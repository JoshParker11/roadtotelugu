/* The reader — text you can mark up, LingQ-style.
 *
 * The mechanic that makes this worth building: a word's first exposure is never a flashcard.
 * You meet it in something you wanted to read, decide what it is, and only then does it become
 * a card. That ordering is the whole reason for the page.
 *
 * FOUR STATES, and the default is the interesting one.
 *   new       untouched. Highlighted, because unmarked is a to-do, not a neutral.
 *   learning  actively working on it. This is the bucket that exports to Anki.
 *   known     no highlight. Reading is finished when the page stops glowing.
 *   ignore    names, numbers, English. Permanently silent.
 *
 * KNOWN IS SHARED, ON PURPOSE.
 * A word that exists in the master is keyed by guid and its known-state lives in Progress —
 * the same `rtt.known` the vocabulary queue writes. So marking a word known here also unlocks
 * sentences in the drill. Words with no master entry have nowhere to put a guid, so they get
 * their own store keyed by the folded form; they are also exactly the words worth mining.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const nf = n => n.toLocaleString('en-US');

  const K = { st: 'rtt.readStatus', pos: 'rtt.readPos' };
  const read = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };

  const TEXTS = window.READER_TEXTS || {};
  const SLUGS = Object.keys(TEXTS);
  if (!SLUGS.length) {
    $('#reader').innerHTML = '<p class="empty">No texts are baked yet. Run <span class="mono">python3 tools/build_reader.py --all</span>.</p>';
    return;
  }

  /* Reader-local status for every token, keyed by the fold. Master words additionally mirror
     their `known` into Progress so the rest of the site sees it. */
  let status = read(K.st, {});
  const saveStatus = () => write(K.st, status);

  let slug = read(K.pos, {}).slug || SLUGS[0];
  if (!TEXTS[slug]) slug = SLUGS[0];
  let section = 0, showEn = true, focus = null;

  const text = () => TEXTS[slug];
  const lexOf = i => text().lex[i];

  /* ---------- state of one token ---------- */
  function stateOf(tok) {
    const [, kind, li] = tok;
    if (kind === 'p') return 'p';
    const lx = li >= 0 ? lexOf(li) : null;
    const key = lx ? lx.k : null;

    if (key && status[key]) return status[key];          // an explicit decision always wins
    if (kind === 'e' || kind === 'n') return 'english';
    if (lx && lx.g && Progress.isKnown(lx.g)) return 'known';
    /* Not a decision, but worth seeing: this word has already come up in Anki. Distinguishing
       "card I've had" from "never seen" is most of what tells you why a line is hard. */
    if (lx && lx.o && Progress.isConfigured() && lx.o <= Progress.introducedCount()) return 'seen';
    return lx && lx.g ? 'new' : 'unseen';               // unseen = not in the deck at all
  }

  function setState(key, guid, st) {
    if (st === 'clear') delete status[key]; else status[key] = st;
    saveStatus();
    /* Mirror into the shared store so the drill and the vocabulary queue agree. Only `known`
       crosses over — "learning" is a reader concept and would muddy the deck's meaning. */
    if (guid) Progress.setKnown(guid, st === 'known');
    repaint();
  }

  /* ---------- rendering ---------- */
  function renderPicker() {
    $('#texts').innerHTML = SLUGS.map(s =>
      `<button class="chip${s === slug ? ' on' : ''}" data-slug="${esc(s)}">${esc(TEXTS[s].title)}${TEXTS[s].private ? ' <b>private</b>' : ''}</button>`).join('');
    const t = text();
    $('#blurb').textContent = t.blurb || '';
    $('#sections').innerHTML = t.sections.map((s, i) =>
      `<button class="chip${i === section ? ' on' : ''}" data-section="${i}">${esc(s.title)}</button>`).join('');
  }

  function renderText() {
    const sec = text().sections[section];
    if (!sec) { $('#reader').innerHTML = ''; return; }
    $('#reader').innerHTML = sec.lines.map((ln, li) => {
      const body = ln.t.map((tok, ti) => {
        const [surface, kind, lx] = tok;
        if (kind === 'p') return esc(surface);
        const st = stateOf(tok);
        const key = lx >= 0 ? lexOf(lx).k : '';
        return `<span class="tk ${st}${kind === '~' ? ' approx' : ''}" data-l="${li}" data-t="${ti}" data-k="${esc(key)}">${esc(surface)}</span>`;
      }).join('');
      return `<p class="rline"><span class="rte">${body}</span>` +
             (showEn && ln.en ? `<span class="ren">${esc(ln.en)}</span>` : '') + '</p>';
    }).join('');
  }

  function renderStats() {
    const sec = text().sections[section];
    if (!sec) return;
    const c = { known: 0, seen: 0, learning: 0, new: 0, unseen: 0, english: 0, ignore: 0 };
    let tot = 0;
    sec.lines.forEach(ln => ln.t.forEach(tok => {
      const st = stateOf(tok);
      if (st === 'p') return;
      tot++; c[st] = (c[st] || 0) + 1;
    }));
    const comfortable = c.known + c.english + c.ignore + c.seen;
    $('#coverage').innerHTML =
      ['known', 'seen', 'learning', 'new', 'unseen', 'english', 'ignore']
        .filter(k => c[k]).map(k =>
          `<span class="seg-${k}" style="flex:${c[k]}" title="${k}: ${c[k]}"></span>`).join('');
    $('#covnum').innerHTML =
      `<b>${tot ? Math.round(comfortable / tot * 100) : 0}%</b> comfortable · ` +
      `${nf(c.learning || 0)} learning · <b class="warn">${nf((c.new || 0) + (c.unseen || 0))}</b> to deal with`;
    $('#legend').innerHTML = [
      ['known', 'known'], ['seen', 'seen in Anki'], ['learning', 'learning'],
      ['new', 'new (in the deck)'], ['unseen', 'new (not in the deck)'],
      ['english', 'English'], ['ignore', 'ignored'],
    ].map(([k, label]) => `<span><i class="sw ${k}"></i>${label} ${c[k] ? nf(c[k]) : 0}</span>`).join('');
  }

  const repaint = () => { renderText(); renderStats(); renderMine(); };

  /* ---------- the word panel ---------- */
  function openPanel(li, ti) {
    const sec = text().sections[section];
    const ln = sec.lines[li];
    const tok = ln.t[ti];
    const [surface, kind, lxi] = tok;
    if (kind === 'p') return;
    focus = { li, ti };
    const lx = lxi >= 0 ? lexOf(lxi) : null;
    const st = stateOf(tok);

    let head = `<h3>${esc(surface)}</h3>`;
    let body = '';
    if (lx && lx.en) {
      body += `<p class="pgloss">${esc(lx.en)}</p>`;
      body += `<p class="pforms"><span class="mono amber">${esc(lx.r)}</span>` +
              (lx.te ? ` <span class="telugu">${esc(lx.te)}</span>` : '') + '</p>';
      if (kind === '~') {
        body += `<p class="pwarn">Matched approximately — the text spells it <span class="mono">${esc(surface.toLowerCase())}</span>,
          the deck spells it <span class="mono">${esc(lx.r)}</span>. Usually the same word, occasionally not.</p>`;
      }
      if (lx.o) body += `<p class="pmeta">Deck position ${nf(lx.o)}${
        Progress.isConfigured() && lx.o <= Progress.introducedCount() ? ' · already introduced' : ' · not yet introduced'}</p>`;
    } else if (kind === 'e' || kind === 'n') {
      body += `<p class="pgloss">${kind === 'n' ? 'Looks like a name.' : 'English.'}</p>
        <p class="pmeta">Dimmed automatically. If that is wrong, mark it <b>learning</b> and it
        joins the list to look up.</p>`;
    } else {
      body += `<p class="pgloss">Not in the deck.</p>
        <p class="pmeta">Nothing here knows this word. Mark it <b>learning</b> and it joins the
        export list with the line it came from, ready to be given a definition and imported.</p>`;
    }
    body += `<p class="pctx">${esc(ln.en || '')}</p>`;

    $('#panel-body').innerHTML = head + body;
    $('#panel').hidden = false;
    $('#panel').dataset.key = lx ? lx.k : '';
    $('#panel').dataset.guid = lx && lx.g ? lx.g : '';
    $('#panel').querySelectorAll('[data-set]').forEach(b =>
      b.classList.toggle('on', b.dataset.set === st));
  }

  const closePanel = () => { $('#panel').hidden = true; focus = null; };

  /* ---------- mined words ---------- */
  function minedRows() {
    const out = [];
    Object.keys(status).forEach(k => { if (status[k] === 'learning') out.push(k); });
    const byKey = new Map();
    SLUGS.forEach(s => TEXTS[s].lex.forEach(l => { if (!byKey.has(l.k)) byKey.set(l.k, l); }));
    // first line each word appears in, so the export carries its context
    const ctx = new Map();
    SLUGS.forEach(s => TEXTS[s].sections.forEach(sec => sec.lines.forEach(ln => {
      ln.t.forEach(tok => {
        if (tok[2] < 0) return;
        const key = TEXTS[s].lex[tok[2]].k;
        if (!ctx.has(key)) ctx.set(key, ln.t.map(x => x[0]).join(''));
      });
    })));
    return out.map(k => {
      const l = byKey.get(k) || { k, r: k, te: '', en: '', g: '' };
      return { key: k, roman: l.r, telugu: l.te, en: l.en, guid: l.g, ctx: ctx.get(k) || '' };
    }).sort((a, b) => a.roman.localeCompare(b.roman));
  }

  function renderMine() {
    const rows = minedRows();
    $('#minecount').textContent = rows.length ? `${rows.length} word${rows.length === 1 ? '' : 's'}` : 'nothing yet';
    if (!rows.length) {
      $('#minelist').innerHTML = `<p class="empty">Mark words <b>learning</b> as you read and they collect here.</p>`;
      return;
    }
    $('#minelist').innerHTML = rows.map(r =>
      `<div class="minerow"><b class="mono amber">${esc(r.roman)}</b>` +
      (r.telugu ? `<span class="telugu">${esc(r.telugu)}</span>` : '<span class="need">needs script</span>') +
      (r.en ? `<span class="mg">${esc(r.en)}</span>` : '<span class="need">needs a definition</span>') +
      (r.guid ? '<span class="tag">in deck</span>' : '<span class="tag new">to add</span>') +
      '</div>').join('');
  }

  function mineTSV() {
    const rows = minedRows();
    return ['roman\ttelugu\tenglish\tin_deck\tcontext',
      ...rows.map(r => [r.roman, r.telugu, r.en, r.guid ? 'yes' : 'no',
                        (r.ctx || '').replace(/\s+/g, ' ').slice(0, 120)].join('\t'))].join('\n');
  }

  /* ---------- events ---------- */
  $('#reader').addEventListener('click', e => {
    const t = e.target.closest('.tk');
    if (!t) return;
    openPanel(+t.dataset.l, +t.dataset.t);
  });

  $('#panel').addEventListener('click', e => {
    const b = e.target.closest('[data-set]');
    if (!b) return;
    const key = $('#panel').dataset.key, guid = $('#panel').dataset.guid;
    if (!key) return closePanel();
    setState(key, guid, b.dataset.set);
    closePanel();
  });
  $('#panel-close').addEventListener('click', closePanel);

  $('#texts').addEventListener('click', e => {
    const b = e.target.closest('[data-slug]');
    if (!b) return;
    slug = b.dataset.slug; section = 0;
    write(K.pos, { slug });
    renderPicker(); repaint(); closePanel();
  });

  $('#sections').addEventListener('click', e => {
    const b = e.target.closest('[data-section]');
    if (!b) return;
    section = +b.dataset.section;
    renderPicker(); repaint(); closePanel();
    $('#reader').scrollIntoView({ block: 'start' });
  });

  $('#toggle-en').addEventListener('click', () => {
    showEn = !showEn;
    $('#toggle-en').classList.toggle('on', showEn);
    $('#toggle-en').textContent = showEn ? 'Translation shown' : 'Translation hidden';
    renderText();
  });

  $('#btn-known-all').addEventListener('click', () => {
    /* Everything still untouched in this section is probably known — the honest default after
       a first pass, and it is what stops the page glowing forever. */
    const sec = text().sections[section];
    let n = 0;
    sec.lines.forEach(ln => ln.t.forEach(tok => {
      const st = stateOf(tok);
      if (st !== 'new' && st !== 'seen' && st !== 'unseen') return;
      const lx = tok[2] >= 0 ? lexOf(tok[2]) : null;
      if (!lx) return;
      status[lx.k] = 'known';
      if (lx.g) Progress.setKnown(lx.g, true);
      n++;
    }));
    saveStatus(); repaint();
    say(`${n} words marked known in this section.`);
  });

  const say = m => { $('#say').textContent = m; };

  $('#btn-copy').addEventListener('click', async () => {
    const tsv = mineTSV();
    try { await navigator.clipboard.writeText(tsv); say('Copied — paste into a sheet, fill the blanks, import.'); }
    catch { $('#io').value = tsv; $('#io').hidden = false; $('#io').select(); say('Select and copy.'); }
  });

  $('#btn-download').addEventListener('click', () => {
    const b = new Blob([mineTSV()], { type: 'text/tab-separated-values' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(b);
    a.download = `telugu-mined-${Progress.todayISO()}.tsv`;
    a.click(); URL.revokeObjectURL(a.href);
    say('Downloaded.');
  });

  document.addEventListener('keydown', e => {
    const t = e.target;
    if (t instanceof Element && t.matches('input, textarea')) return;
    if ($('#panel').hidden) return;
    const map = { '1': 'known', '2': 'learning', '3': 'ignore', '0': 'clear' };
    if (e.key === 'Escape') return closePanel();
    if (map[e.key]) {
      e.preventDefault();
      const key = $('#panel').dataset.key;
      if (key) setState(key, $('#panel').dataset.guid, map[e.key]);
      closePanel();
    }
  });

  /* ---------- boot ---------- */
  $('#generated').textContent = text().generated;
  renderPicker(); repaint();
})();
