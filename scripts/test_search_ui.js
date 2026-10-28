const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(id = '') {
    this.id = id;
    this.textContent = '';
    this.className = '';
    this.value = '';
    this.hidden = false;
    this.disabled = false;
    this.dataset = {};
    this.children = [];
    this.listeners = {};
    this.tagName = 'DIV';
    this.isContentEditable = false;
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  replaceChildren(...children) {
    this.children = children;
  }

  addEventListener(type, handler) {
    (this.listeners[type] ||= []).push(handler);
  }

  setAttribute(name, value) {
    this[name] = value;
  }

  focus() {}

  dispatch(type, event = {}) {
    for (const handler of this.listeners[type] || []) handler(event);
  }
}

const root = path.resolve(__dirname, '..');
const ids = {};
for (const id of [
  'kb-search-data',
  'global-search',
  'search-section',
  'search-sort',
  'search-results',
  'search-status',
  'search-more',
  'search-clear',
]) {
  ids[id] = new Element(id);
}
ids['kb-search-data'].dataset.src = 'search-index.json';
ids['search-more'].hidden = true;

const document = {
  documentElement: { dataset: {} },
  activeElement: { tagName: 'BODY', isContentEditable: false },
  getElementById(id) {
    return ids[id] || null;
  },
  createElement(tag) {
    const element = new Element();
    element.tagName = tag.toUpperCase();
    return element;
  },
  createTextNode(text) {
    return { textContent: text };
  },
  addEventListener() {},
};

const notes = JSON.parse(
  fs.readFileSync(path.join(root, 'docs', 'search-index.json'), 'utf8'),
);
const context = {
  document,
  fetch: async () => ({ ok: true, json: async () => notes }),
  console,
  setTimeout,
  clearTimeout,
  Promise,
  URL,
  location: { href: 'http://127.0.0.1:8765/search.html' },
  history: { replaceState() {} },
  localStorage: { getItem() { return null; }, setItem() {} },
  window: { addEventListener() {} },
};

vm.createContext(context);
vm.runInContext(
  fs.readFileSync(path.join(root, 'docs', 'assets', 'site.js'), 'utf8'),
  context,
);

try {
  assert.equal(ids['search-status'].textContent, '\u8f93\u5165\u5173\u952e\u8bcd\u5f00\u59cb\u641c\u7d22\u3002');
  ids['global-search'].value = '\u5355\u7ec6\u80de';
  ids['global-search'].dispatch('input');
  setTimeout(() => {
    try {
      assert.ok(ids['search-results'].children.length > 0);
      assert.match(ids['search-status'].textContent, /\u627e\u5230/);
      ids['search-clear'].dispatch('click');
      assert.equal(ids['search-results'].children.length, 0);
      console.log('Search UI test: OK');
    } catch (error) {
      console.error(error);
      process.exitCode = 1;
    }
  }, 500);
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
