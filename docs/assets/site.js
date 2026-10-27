(function(){
var root=document.documentElement;
var saved;try{saved=localStorage.getItem("kb-site-theme");}catch(_){}if(saved){root.dataset.theme=saved;}
var theme=document.getElementById("site-theme");
function syncTheme(){if(theme){theme.textContent=root.dataset.theme==="dark"?"浅色":"深色";}}
if(theme){theme.addEventListener("click",function(){root.dataset.theme=root.dataset.theme==="dark"?"light":"dark";try{localStorage.setItem("kb-site-theme",root.dataset.theme);}catch(_){}syncTheme();});}
syncTheme();
var search=document.getElementById("section-search");
if(search){
var cards=Array.from(document.querySelectorAll(".kb-note-card"));
var buttons=Array.from(document.querySelectorAll(".category-button"));
var active="";
var localStatus=document.createElement("p");localStatus.className="search-status";localStatus.setAttribute("role","status");search.parentNode.appendChild(localStatus);
function apply(){var terms=search.value.normalize("NFKC").trim().toLocaleLowerCase("zh-CN").split(/\s+/).filter(Boolean);var visible=0;cards.forEach(function(card){var text=(card.dataset.search||"").normalize("NFKC");var ok=terms.every(function(term){return text.indexOf(term)>=0;})&&(!active||card.dataset.category===active);card.hidden=!ok;if(ok)visible++;});document.getElementById("empty-state").style.display=visible?"none":"block";localStatus.textContent="显示 "+visible+" / "+cards.length+" 篇笔记";}
search.addEventListener("input",apply);
buttons.forEach(function(button){button.setAttribute("aria-pressed","false");button.addEventListener("click",function(){var next=button.dataset.category;active=active===next?"":next;buttons.forEach(function(item){item.classList.toggle("active",item.dataset.category===active);item.setAttribute("aria-pressed",String(item.dataset.category===active));});apply();});});apply();
}
})();
;(function initSearch(engine) {
  var payload = document.getElementById('kb-search-data');
  var input = document.getElementById('global-search');
  if (!payload || !input) return;
  var notes;
  try { notes = engine.prepare(JSON.parse(payload.textContent)); }
  catch (_) { document.getElementById('search-status').textContent = '搜索索引加载失败，请刷新页面。'; return; }
  var section = document.getElementById('search-section');
  var sort = document.getElementById('search-sort');
  var results = document.getElementById('search-results');
  var status = document.getElementById('search-status');
  var more = document.getElementById('search-more');
  var clear = document.getElementById('search-clear');
  var limit = 40, timer, composing = false;
  function node(tag, className, text) { var el = document.createElement(tag); if (className) el.className = className; if (text !== undefined) el.textContent = text; return el; }
  function highlight(el, text, query) {
    var terms = engine.tokens(query);
    if (!terms.length) { el.textContent = text; return; }
    var lower = text.toLocaleLowerCase('zh-CN'), ranges = [];
    terms.forEach(function (term) { var at = lower.indexOf(term); while (at >= 0) { ranges.push([at, at + term.length]); at = lower.indexOf(term, at + term.length); } });
    ranges.sort(function(a, b) { return a[0] - b[0]; });
    var end = 0;
    ranges.forEach(function(range) { if (range[0] < end) return; el.appendChild(document.createTextNode(text.slice(end, range[0]))); el.appendChild(node('mark', '', text.slice(range[0], range[1]))); end = range[1]; });
    el.appendChild(document.createTextNode(text.slice(end)));
  }
  function stateFromURL() {
    var params = new URL(location.href).searchParams;
    input.value = (params.get('q') || '').slice(0, 300);
    section.value = params.get('section') || ''; if (!section.value) section.value = '';
    sort.value = params.get('sort') === 'updated' ? 'updated' : 'relevance';
  }
  function render(updateURL) {
    var query = input.value.trim(), matches = engine.search(notes, query, section.value, sort.value);
    results.replaceChildren();
    matches.slice(0, limit).forEach(function(match) {
      var item = match.note, article = node('article', 'search-result');
      var metadata = node('div', 'recent-meta', item.sectionTitle + ' / ' + item.category + ' · ' + item.updated.slice(0, 10));
      var identifier = node('span', 'kb-id-badge', item.kbId); identifier.setAttribute('aria-label', '站内唯一编号 ' + item.kbId); metadata.appendChild(identifier); article.appendChild(metadata);
      var heading = node('h2'), link = node('a'); link.href = item.url; highlight(link, item.title, query); heading.appendChild(link); article.appendChild(heading);
      var excerpt = node('p', 'search-excerpt'); highlight(excerpt, engine.snippet(item, query), query); article.appendChild(excerpt);
      var tags = node('div', 'tag-row'); (item.tags || []).slice(0, 6).forEach(function(tag) { tags.appendChild(node('span', 'tag-pill', tag)); }); article.appendChild(tags);
      results.appendChild(article);
    });
    status.textContent = matches.length ? '找到 ' + matches.length + ' 篇笔记' + (matches.length > limit ? '，已显示 ' + limit + ' 篇' : '') : '没有匹配的笔记。试试减少关键词或选择全部板块。';
    more.hidden = matches.length <= limit;
    clear.disabled = !query && !section.value;
    if (updateURL) {
      var url = new URL(location.href);
      query ? url.searchParams.set('q', query) : url.searchParams.delete('q');
      section.value ? url.searchParams.set('section', section.value) : url.searchParams.delete('section');
      sort.value === 'updated' ? url.searchParams.set('sort', 'updated') : url.searchParams.delete('sort');
      try { history.replaceState(null, '', url); } catch (_) { /* Search also works without history access. */ }
    }
  }
  function schedule() { clearTimeout(timer); if (composing) return; timer = setTimeout(function() { limit = 40; render(true); }, 120); }
  input.addEventListener('compositionstart', function() { composing = true; });
  input.addEventListener('compositionend', function() { composing = false; schedule(); });
  input.addEventListener('input', schedule);
  section.addEventListener('change', function() { limit = 40; render(true); });
  sort.addEventListener('change', function() { limit = 40; render(true); });
  more.addEventListener('click', function() { limit += 40; render(false); });
  clear.addEventListener('click', function() { input.value = ''; section.value = ''; limit = 40; render(true); input.focus(); });
  input.addEventListener('keydown', function(event) { if (event.key === 'Escape') { clearTimeout(timer); input.value = ''; render(true); } });
  window.addEventListener('popstate', function() { stateFromURL(); limit = 40; render(false); });
  document.addEventListener('keydown', function(event) { if (event.key === '/' && !/input|textarea|select/i.test(document.activeElement.tagName) && !document.activeElement.isContentEditable) { event.preventDefault(); input.focus(); } });
  stateFromURL(); render(false);
})((function createSearchEngine() {
  function normalise(value) { return String(value || '').normalize('NFKC').toLocaleLowerCase('zh-CN').replace(/\s+/g, ' ').trim(); }
  function tokens(query) { return [...new Set(normalise(query).slice(0, 300).split(' ').filter(Boolean))]; }
  function prepare(notes) {
    return notes.map(note => ({ ...note, fields: { id: normalise(note.kbId), title: normalise(note.title + ' ' + (note.subtitle || '')), tags: normalise((note.tags || []).join(' ')), summary: normalise(note.summary), body: normalise(note.body), category: normalise(note.sectionTitle + ' ' + note.category) } }));
  }
  function search(notes, query, section = '', sort = 'relevance') {
    const terms = tokens(query), phrase = normalise(query);
    return notes.filter(note => !section || note.section === section).map(note => {
      const fields = note.fields, all = Object.values(fields).join(' ');
      if (!terms.every(term => all.includes(term))) return null;
      let score = 0;
      for (const term of terms) for (const [field, weight] of Object.entries({ id: 40, title: 30, tags: 20, summary: 8, category: 4, body: 2 })) if (fields[field].includes(term)) score += weight;
      if (phrase && fields.title.includes(phrase)) score += 15;
      return { note, score };
    }).filter(Boolean).sort((a, b) => (sort === 'updated' ? 0 : b.score - a.score) || String(b.note.updated).localeCompare(String(a.note.updated)) || a.note.url.localeCompare(b.note.url));
  }
  function snippet(note, query) {
    const body = String(note.body || note.summary || ''), lower = body.toLocaleLowerCase('zh-CN');
    const positions = tokens(query).map(term => lower.indexOf(term)).filter(n => n >= 0);
    const start = positions.length ? Math.max(0, Math.min(...positions) - 60) : 0;
    return (start ? '…' : '') + body.slice(start, start + 220) + (body.length > start + 220 ? '…' : '');
  }
  return { normalise, tokens, prepare, search, snippet };
})());
