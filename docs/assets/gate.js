(function () {
  'use strict';

  var payload = document.getElementById('kb-payload');
  var form = document.getElementById('kb-unlock-form');
  var input = document.getElementById('kb-password');
  var status = document.getElementById('kb-status');
  if (!payload || !form || !input || !status) return;

  var iterations = Number(payload.dataset.iterations || 310000);
  var salt = base64ToBytes(payload.dataset.salt || '');
  var encrypted = base64ToBytes((payload.textContent || '').replace(/\s+/g, ''));

  function base64ToBytes(value) {
    var raw = atob(value);
    var bytes = new Uint8Array(raw.length);
    for (var index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index);
    return bytes;
  }

  function bytesToBase64(bytes) {
    var chunks = [];
    for (var index = 0; index < bytes.length; index += 0x8000) {
      chunks.push(String.fromCharCode.apply(null, bytes.subarray(index, index + 0x8000)));
    }
    return btoa(chunks.join(''));
  }

  async function deriveKey(password) {
    var material = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(password),
      'PBKDF2',
      false,
      ['deriveKey']
    );
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: salt, iterations: iterations, hash: 'SHA-256' },
      material,
      { name: 'AES-GCM', length: 256 },
      true,
      ['decrypt']
    );
  }

  async function importStoredKey(value) {
    return crypto.subtle.importKey('raw', base64ToBytes(value), 'AES-GCM', true, ['decrypt']);
  }

  async function openContent(key) {
    var plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: encrypted.slice(0, 12) },
      key,
      encrypted.slice(12)
    );
    var html = new TextDecoder().decode(plain);
    var parsed = new DOMParser().parseFromString(html, 'text/html');
    var scripts = Array.from(parsed.querySelectorAll('script'));
    scripts.forEach(function (script) { script.remove(); });

    Array.from(document.documentElement.attributes).forEach(function (attribute) {
      document.documentElement.removeAttribute(attribute.name);
    });
    Array.from(parsed.documentElement.attributes).forEach(function (attribute) {
      document.documentElement.setAttribute(attribute.name, attribute.value);
    });
    document.head.innerHTML = parsed.head.innerHTML;
    document.body.innerHTML = parsed.body.innerHTML;
    Array.from(parsed.body.attributes).forEach(function (attribute) {
      document.body.setAttribute(attribute.name, attribute.value);
    });

    for (var index = 0; index < scripts.length; index += 1) {
      var original = scripts[index];
      var replacement = document.createElement('script');
      Array.from(original.attributes).forEach(function (attribute) {
        replacement.setAttribute(attribute.name, attribute.value);
      });
      var scriptSource = original.getAttribute('src');
      if (!scriptSource) replacement.textContent = original.textContent;
      if (scriptSource) {
        replacement.src = new URL(scriptSource, window.location.href).href;
        await new Promise(function (resolve) {
          replacement.addEventListener('load', resolve, { once: true });
          replacement.addEventListener('error', resolve, { once: true });
          document.body.appendChild(replacement);
        });
      } else {
        document.body.appendChild(replacement);
      }
    }
  }

  function setStatus(message, isError) {
    status.textContent = message;
    status.dataset.state = isError ? 'error' : 'busy';
  }

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    var password = input.value;
    if (!password) {
      setStatus('请输入共享密码。', true);
      input.focus();
      return;
    }
    input.disabled = true;
    form.querySelector('button').disabled = true;
    setStatus('正在验证…', false);
    try {
      var key = await deriveKey(password);
      sessionStorage.setItem('kb-unlock-key', bytesToBase64(new Uint8Array(await crypto.subtle.exportKey('raw', key))));
      await openContent(key);
    } catch (error) {
      input.disabled = false;
      form.querySelector('button').disabled = false;
      input.select();
      setStatus('密码不正确，请重试。', true);
    }
  });

  (async function tryStoredKey() {
    if (!window.crypto || !crypto.subtle) {
      setStatus('当前浏览器不支持安全解密，请使用较新的浏览器。', true);
      return;
    }
    var stored = sessionStorage.getItem('kb-unlock-key');
    if (!stored) {
      input.focus();
      return;
    }
    try {
      var key = await importStoredKey(stored);
      await openContent(key);
    } catch (error) {
      sessionStorage.removeItem('kb-unlock-key');
      input.focus();
    }
  })();
})();
