/* The book reader: familiar books in Telugu, chapter by chapter or line by line.
 *
 * Deliberately small. Three word states and nothing else:
 *   0 new   — never looked at (the default; not stored)
 *   1 seen  — looked up at least once. Opening a new word's panel moves it here on its own,
 *             because looking a word up IS having seen it.
 *   2 known — reads as plain text from then on.
 * Status is keyed by the Telugu surface form, and shared across every book, so a word marked
 * known in chapter 1 stays known in chapter 9 and in the next book.
 *
 * Names and English loans (lexicon kind "name" / "loan") are never coloured or counted.
 *
 * Data: books/data/books.js, baked by tools/build_books.py. Routes:
 *   #/                 library
 *   #/<book>           chapter list
 *   #/<book>/<ch>      the chapter as a page
 *   #/<book>/<ch>/<n>  line view, sentence n
 */
(() => {
  const D = window.BOOKS_DATA;
  const LEX = D.lex, GRAM = D.grammar;
  const $ = (s, el = document) => el.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /* ---------- storage: wrapped, because private mode and cleared storage both throw ---------- */
  const store = {
    get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  const SK = 'rtt.books.status', PK = 'rtt.books.prefs', LK = 'rtt.books.last';
  let status = store.get(SK, {});
  const prefs = Object.assign({ script: 'te', en: true, ro: false, mode: 'page' }, store.get(PK, {}));
  const savePrefs = () => store.set(PK, prefs);

  const tracked = w => { const e = LEX[w]; return !e || e.k === 'word'; };
  const stOf = w => status[w] || 0;
  function setStatus(w, s) {
    if (s) status[w] = s; else delete status[w];
    store.set(SK, status);
    document.querySelectorAll('.w').forEach(el => { if (el.dataset.w === w) paintWord(el); });
    refreshCounts();
  }

  /* ---------- lookups ---------- */
  const bookById = id => D.books.find(b => b.id === id);
  const chapOf = (b, n) => b && b.chapters.find(c => c.n === n);
  const words = sents => sents.flatMap(s => s.t.filter(t => t[1]).map(t => t[0]));
  function counts(sents) {
    const u = [...new Set(words(sents))].filter(tracked);
    const c = [0, 0, 0];
    u.forEach(w => c[stOf(w)]++);
    return { n: u.length, c };
  }
  const romOf = w => (LEX[w] && LEX[w].r) || (window.Colloquial ? Colloquial.romanize(w) : w);

  /* every place a word occurs, for "also in" */
  const OCC = {};
  D.books.forEach(b => b.chapters.forEach(c => c.s.forEach(s => s.t.forEach(t => {
    if (!t[1]) return;
    const list = (OCC[t[0]] ||= []);
    if (!list.some(o => o.b === b.id && o.c === c.n && o.s === s.n)) list.push({ b: b.id, c: c.n, s: s.n });
  }))));

  /* ---------- rendering pieces ---------- */
  function wordHTML(w) {
    const e = LEX[w];
    const cls = !e ? 'w miss' : e.k === 'word' ? 'w' : 'w lo';
    const shown = prefs.script === 'rom' ? romOf(w) : w;
    return `<span class="${cls}" data-w="${esc(w)}">${esc(shown)}</span>`;
  }
  function paintWord(el) {
    const w = el.dataset.w;
    if (!tracked(w) || !LEX[w]) return;
    el.classList.remove('s-new', 's-seen', 's-known');
    el.classList.add(['s-new', 's-seen', 's-known'][stOf(w)]);
  }
  function lineHTML(s) {
    const rom = prefs.script === 'rom';
    const body = s.t.map(([t, w]) => w ? wordHTML(t) : esc(t)).join('');
    return `<div class="tline ${rom ? 'rom' : 'te'}">${body}</div>` +
      (prefs.ro && s.ro ? `<div class="roline">${esc(s.ro)}</div>` : '') +
      (prefs.en && s.en ? `<div class="enline">${esc(s.en)}</div>` : '');
  }
  function barHTML({ n, c }) {
    const pct = x => n ? (x / n * 100).toFixed(1) + '%' : '0';
    return `<div class="bar"><i class="b-known" style="width:${pct(c[2])}"></i><i class="b-seen" style="width:${pct(c[1])}"></i><i class="b-new" style="width:${pct(c[0])}"></i></div>`;
  }
  function keyHTML({ n, c }) {
    return `<div class="key" data-counts>
      <span><i style="background:var(--blue);opacity:.7"></i>${c[0]} new</span>
      <span><i style="background:var(--amber)"></i>${c[1]} seen</span>
      <span><i style="background:var(--green)"></i>${c[2]} known</span>
      <span>· ${n} words</span></div>`;
  }

  /* ---------- views ---------- */
  const pane = $('#pane'), crumb = $('#crumb');
  let view = null;  // { book, chap, line }

  function renderLibrary() {
    crumb.textContent = 'Books'; crumb.href = '#/';
    pane.innerHTML = `<span class="eyebrow">Books in Telugu</span>
      <h1 style="font-size:34px;margin:6px 0 4px">Read what you already know</h1>
      <p class="muted">Stories you know well, in Telugu, so the plot carries you and the words land on something familiar.</p>
      ${D.books.map(b => {
        const all = b.chapters.flatMap(c => c.s), k = counts(all);
        const n = b.chapters.length;
        return `<a class="book" href="#/${b.id}">
          <span class="eyebrow">${n} chapter${n === 1 ? '' : 's'} so far</span>
          <h2>${esc(b.title)}</h2><div class="te">${esc(b.te || '')}</div>
          ${barHTML(k)}${keyHTML(k)}</a>`;
      }).join('')}`;
  }

  function renderBook(b) {
    crumb.textContent = b.short || b.title; crumb.href = `#/${b.id}`;
    pane.innerHTML = `<span class="eyebrow">Book</span>
      <h1 style="font-size:32px;margin:6px 0 4px">${esc(b.title)}</h1>
      <div class="te muted">${esc(b.te || '')}</div>
      <div class="chapters">${b.chapters.map(c => {
        const k = counts(c.s);
        return `<a class="chap" href="#/${b.id}/${c.n}">
          <span class="num">${String(c.n).padStart(2, '0')}</span>
          <span class="title">${esc(c.en)} ${c.status === 'draft' ? '<span class="draft">draft</span>' : ''}</span>
          <span class="meta">${c.s.length} lines · ${k.c[0]} new · ${k.c[1]} seen · ${k.c[2]} known</span>
        </a>`;
      }).join('')}</div>`;
  }

  function chapterHead(b, c) {
    const k = counts(c.s);
    return `<div class="chead">
      <span class="eyebrow">Chapter ${c.n}</span> ${c.status === 'draft' ? '<span class="draft" title="Unverified AI translation — check with a tutor">draft</span>' : ''}
      <h1>${esc(c.en)}</h1>
      <div data-bar>${barHTML(k)}</div>${keyHTML(k)}
      <div class="modebar"><span class="seg" id="modeseg">
        <button data-mode="page" class="${prefs.mode === 'page' ? 'on' : ''}">Page</button>
        <button data-mode="line" class="${prefs.mode === 'line' ? 'on' : ''}">Line by line</button>
      </span></div></div>`;
  }

  function renderPage(b, c, focus) {
    pane.innerHTML = chapterHead(b, c) +
      c.s.map(s => `<div class="sent" id="s${s.n}"><span class="n"><a href="#/${b.id}/${c.n}/${s.n}" title="Open in line view">${s.n}</a></span><div>${lineHTML(s)}</div></div>`).join('') +
      vocabHTML(c) + chapterNav(b, c);
    pane.querySelectorAll('.w').forEach(paintWord);
    if (focus) {
      const el = $('#s' + focus);
      if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('flash'); }
    } else window.scrollTo(0, 0);
  }

  function renderLine(b, c, n) {
    const i = Math.max(0, c.s.findIndex(s => s.n === n));
    const s = c.s[i];
    pane.innerHTML = chapterHead(b, c) + `
      <div class="lineview">${lineHTML(s)}</div>
      <div class="lnav">
        <button class="btn" id="prev" ${i === 0 ? 'disabled' : ''}>← Prev</button>
        <span class="count">${s.n} / ${c.s[c.s.length - 1].n}</span>
        <button class="btn primary" id="next" ${i === c.s.length - 1 ? 'disabled' : ''}>Next →</button>
      </div>
      <div class="dots">${c.s.map((x, j) => `<button data-n="${x.n}" class="${j === i ? 'on' : j < i ? 'done' : ''}" aria-label="Line ${x.n}"></button>`).join('')}</div>
      ${i === c.s.length - 1 ? vocabHTML(c) + chapterNav(b, c) : ''}`;
    pane.querySelectorAll('.w').forEach(paintWord);
    $('#prev').onclick = () => stepLine(-1);
    $('#next').onclick = () => stepLine(1);
    pane.querySelectorAll('.dots button').forEach(d => d.onclick = () => go(`#/${b.id}/${c.n}/${d.dataset.n}`));
    window.scrollTo(0, 0);
  }

  function vocabHTML(c) {
    if (!c.vocab.length) return '';
    return `<section class="vocab"><h3>Mined vocab</h3>
      ${c.vocab.map(v => `<div class="vrow"><span class="te">${esc(v.te)}</span><span>${esc(v.en)}<div class="r">${esc(v.rom)}${v.ref ? ' · ' + esc(v.ref) : ''}</div></span></div>`).join('')}
      </section>`;
  }
  function chapterNav(b, c) {
    const nx = b.chapters.find(x => x.n > c.n);
    return `<div class="lnav" style="margin-top:30px"><a href="#/${b.id}">← All chapters</a>
      ${nx ? `<a href="#/${b.id}/${nx.n}">Chapter ${nx.n}: ${esc(nx.en)} →</a>` : '<span class="muted">More chapters as they are translated</span>'}</div>`;
  }

  function refreshCounts() {
    if (!view || !view.chap) return;
    const k = counts(view.chap.s);
    const bar = $('[data-bar]'); if (bar) bar.innerHTML = barHTML(k);
    const key = $('[data-counts]'); if (key) key.outerHTML = keyHTML(k);
  }

  function stepLine(d) {
    if (!view || view.line == null) return;
    const c = view.chap, i = c.s.findIndex(s => s.n === view.line) + d;
    if (i >= 0 && i < c.s.length) go(`#/${view.book.id}/${c.n}/${c.s[i].n}`);
  }

  /* ---------- word panel ---------- */
  const panel = $('#panel'), pbody = $('#panelbody');
  let openWord = null, openCtx = null;

  function openPanel(w, ctx) {
    if (tracked(w) && LEX[w] && stOf(w) === 0) setStatus(w, 1);
    openWord = w; openCtx = ctx;
    document.querySelectorAll('.w.sel').forEach(el => el.classList.remove('sel'));
    if (ctx && ctx.el) ctx.el.classList.add('sel');
    renderPanel();
    panel.hidden = false;
    document.body.classList.add('panel-open');
    panel.scrollTop = 0;
    /* on a phone the panel is a bottom sheet: lift the tapped word's line above it */
    if (ctx && ctx.el && matchMedia('(max-width: 860px)').matches) {
      const r = ctx.el.getBoundingClientRect();
      if (r.bottom > panel.getBoundingClientRect().top - 12) {
        const line = ctx.el.closest('.sent, .lineview') || ctx.el;
        line.scrollIntoView({ block: 'start', behavior: 'smooth' });
      }
    }
  }
  function closePanel() {
    panel.hidden = true; openWord = null;
    document.body.classList.remove('panel-open');
    document.querySelectorAll('.w.sel').forEach(el => el.classList.remove('sel'));
  }

  function renderPanel() {
    const w = openWord, e = LEX[w];
    if (!e) {
      pbody.innerHTML = `<div class="pw te">${esc(w)}</div><div class="pr">${esc(romOf(w))}</div>
        <p class="muted" style="margin-top:16px">No gloss yet. Add a row for this word to <span class="mono">books/source/lexicon.tsv</span> and rebuild.</p>`;
      return;
    }
    const st = stOf(w);
    const kind = e.k === 'name' ? 'Name / title' : e.k === 'loan' ? 'English loanword' : '';
    const sent = openCtx && openCtx.sent;
    const occ = (OCC[w] || []).filter(o => !(sent && view && o.b === view.book.id && o.c === view.chap.n && o.s === sent.n));
    pbody.innerHTML = `
      <div class="pw te">${esc(w)}</div>
      <div class="pr">${esc(e.r)}</div>
      ${kind ? `<div class="pk"><span>${kind}</span></div>` : ''}
      <div class="pg">${esc(e.en)}</div>
      ${e.k === 'word' ? `<div class="status">
        ${['New', 'Seen', 'Known'].map((l, i) => `<button data-st="${i}" class="${st === i ? 'on' : ''}">${l}<kbd>${i + 1}</kbd></button>`).join('')}
      </div>` : ''}
      ${e.p ? `<div class="psec"><h4>Breakdown</h4><div class="parts">${e.p.map(([m, g]) =>
        `<span class="part"><span class="te">${esc(m)}</span><small>${esc(g)}</small></span>`).join('<span class="plus">+</span>')}</div></div>` : ''}
      ${e.g ? `<div class="psec"><h4>Grammar</h4>${e.g.filter(id => GRAM[id]).map(id => {
        const r = GRAM[id];
        return `<div class="rule"><b>${esc(r.t)}</b><div class="f te">${esc(r.f)}</div><p>${esc(r.x)}</p></div>`;
      }).join('')}</div>` : ''}
      ${e.x ? `<div class="psec"><h4>Note</h4><div class="note">${esc(e.x)}</div></div>` : ''}
      ${sent && sent.en ? `<div class="psec"><h4>In this line · ${sent.n}</h4><div class="ctx">${esc(sent.en)}</div></div>` : ''}
      ${occ.length ? `<div class="psec"><h4>Also in</h4><div class="refs">${occ.slice(0, 30).map(o =>
        `<a href="#/${o.b}/${o.c}/${o.s}">${o.b === (view && view.book.id) ? '' : o.b + ' '}${o.c}.${o.s}</a>`).join('')}</div></div>` : ''}
      <div class="pfoot">Draft gloss — not yet checked by a native speaker.</div>`;
    pbody.querySelectorAll('.status button').forEach(btn => btn.onclick = () => { setStatus(w, +btn.dataset.st); renderPanel(); });
  }

  /* ---------- events ---------- */
  pane.addEventListener('click', ev => {
    const wEl = ev.target.closest('.w');
    if (wEl) {
      const sid = wEl.closest('.sent');
      const n = sid ? +sid.id.slice(1) : view && view.line;
      const sent = view && view.chap && view.chap.s.find(s => s.n === n);
      openPanel(wEl.dataset.w, { el: wEl, sent });
      return;
    }
    const m = ev.target.closest('[data-mode]');
    if (m && view && view.chap) {
      prefs.mode = m.dataset.mode; savePrefs();
      const first = view.line || (topSentence() ?? view.chap.s[0].n);
      if (prefs.mode === 'page') pageFocus = view.line;
      go(prefs.mode === 'line' ? `#/${view.book.id}/${view.chap.n}/${first}` : `#/${view.book.id}/${view.chap.n}`);
    }
  });
  function topSentence() {
    for (const el of pane.querySelectorAll('.sent')) {
      if (el.getBoundingClientRect().bottom > 80) return +el.id.slice(1);
    }
    return null;
  }
  $('#panel-x').onclick = closePanel;

  function syncToggles() {
    document.querySelectorAll('#scriptseg button').forEach(b => b.classList.toggle('on', b.dataset.script === prefs.script));
    $('#tog-en').classList.toggle('on', prefs.en);
    $('#tog-ro').classList.toggle('on', prefs.ro);
  }
  document.querySelectorAll('#scriptseg button').forEach(b => b.onclick = () => { prefs.script = b.dataset.script; savePrefs(); rerender(); });
  $('#tog-en').onclick = () => { prefs.en = !prefs.en; savePrefs(); rerender(); };
  $('#tog-ro').onclick = () => { prefs.ro = !prefs.ro; savePrefs(); rerender(); };

  document.addEventListener('keydown', ev => {
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.key === 'Escape') return closePanel();
    if (view && view.line != null) {
      if (ev.key === 'ArrowRight') return stepLine(1);
      if (ev.key === 'ArrowLeft') return stepLine(-1);
    }
    if (openWord && LEX[openWord] && LEX[openWord].k === 'word' && '123'.includes(ev.key)) {
      setStatus(openWord, +ev.key - 1); renderPanel();
    }
  });

  /* ---------- router ---------- */
  const go = h => { if (location.hash === h) route(); else location.hash = h; };
  function rerender() {
    syncToggles();
    const keepScroll = window.scrollY;
    route(true);
    if (view && view.chap && view.line == null) window.scrollTo(0, keepScroll);
    if (openWord) renderPanel();
  }
  function route(keep) {
    const [, bid, ch, ln] = (location.hash.replace(/^#\/?/, '#/').split('/'));
    if (!keep) closePanel();
    const b = bid && bookById(bid);
    if (!b) { view = null; return renderLibrary(); }
    const c = ch && chapOf(b, +ch);
    if (!c) { view = { book: b }; return renderBook(b); }
    crumb.textContent = `${b.short || b.title} · ${c.n}`; crumb.href = `#/${b.id}`;
    const last = store.get(LK, {}), key = `${b.id}/${c.n}`;
    if (ln) {
      last[key] = +ln; store.set(LK, last);
      view = { book: b, chap: c, line: +ln }; renderLine(b, c, +ln);
    } else if (prefs.mode === 'line' && !keep) {
      /* the chapter opens in whichever mode you last used, at the line you left off on */
      return go(`#/${b.id}/${c.n}/${last[key] || c.s[0].n}`);
    } else {
      view = { book: b, chap: c, line: null };
      renderPage(b, c, keep ? null : pageFocus);
      pageFocus = null;
    }
  }
  let pageFocus = null;
  window.addEventListener('hashchange', () => route());
  syncToggles();
  route();
})();
