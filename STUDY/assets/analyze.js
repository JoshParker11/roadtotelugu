/* Text analyzer — paste Telugu, find out which words are worth learning first.
 *
 * On the fly, not baked. This runs *before* a text is worth ingesting: the question it answers
 * is "is this worth my time, and which twenty words would make it readable" — and you need
 * that answer while deciding, not after committing to a build step.
 *
 * WHY IT CAN MATCH WITHOUT A ROMANIZER
 * te2rom is Python and there is no JS port. But the master carries the Telugu script for every
 * word, so script input matches directly on script and never needs romanizing. Romanized input
 * falls back to the folded romanization. Each path is exact within itself; nothing here guesses
 * the way the reader's loose fold does, because a frequency table full of wrong matches is
 * worse than one with honest gaps.
 *
 * SAVED SOURCES AND THE CUMULATIVE VIEW
 * One text tells you what that text needs. Several tell you what *your* Telugu needs, which is
 * the actually useful question — a word in four of five sources earns a card in a way a word
 * appearing nine times in one does not. So sources persist and the totals view ranks by how
 * many sources a word appears in first, occurrences second.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const nf = n => n.toLocaleString('en-US');

  const K = 'rtt.analyze';
  const read = () => { try { return JSON.parse(localStorage.getItem(K)) ?? []; } catch { return []; } };
  const write = v => { try { localStorage.setItem(K, JSON.stringify(v)); } catch (e) { alert('Could not save — storage may be full.'); } };

  const FOLD = { 'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ḷ': 'l', 'ṁ': 'm', 'ṣ': 's', 'ś': 's', 'ṛ': 'r' };
  const fold = s => (s || '').toLowerCase().replace(/[āīūēōṭḍṇḷṁṣśṛ]/g, c => FOLD[c]).replace(/[^a-z]/g, '');

  /* Same two-branch tokenizer the ingest uses: Telugu as a run, because its vowel signs are
     combining marks that \w does not match. */
  const TOKEN = /[ఀ-౿]+|[^\W\d_]+(?:['’][^\W\d_]+)*/gu;
  const isTelugu = s => /[ఀ-౿]/.test(s);

  /* ---------- master index ---------- */
  const F = WORD_DATA.fields;
  const WORDS = WORD_DATA.words.map(r => { const o = {}; F.forEach((k, i) => o[k] = r[i]); return o; });
  const byScript = new Map(), byRoman = new Map();
  WORDS.forEach(w => {
    if (w.telugu) byScript.set(w.telugu.trim(), w);
    const f = fold((w.roman || '').split(' ')[0]);
    if (f && !byRoman.has(f)) byRoman.set(f, w);
  });

  function lookup(tok) {
    if (isTelugu(tok)) return byScript.get(tok) || null;
    return byRoman.get(fold(tok)) || null;
  }

  /* ---------- analysis ---------- */
  function analyse(text) {
    const counts = new Map();
    let total = 0;
    for (const m of text.matchAll(TOKEN)) {
      const tok = m[0];
      if (isTelugu(tok)) {
        if (!tok.trim()) continue;
      } else if (!fold(tok)) continue;
      total++;
      const key = isTelugu(tok) ? tok : fold(tok);
      const e = counts.get(key) || { key, surface: tok, n: 0, telugu: isTelugu(tok) };
      e.n++; counts.set(key, e);
    }
    const rows = [...counts.values()].map(e => {
      const w = lookup(e.surface);
      return Object.assign(e, {
        order: w ? w.order : 0, gloss: w ? w.english : '', guid: w ? w.guid : '',
        roman: w ? w.roman : (e.telugu ? '' : e.surface),
      });
    });
    rows.sort((a, b) => b.n - a.n || a.key.localeCompare(b.key));
    return { total, distinct: rows.length, rows };
  }

  /* Coverage is computed against what you actually know, not against the deck. Known marks
     come from the shared store, so this agrees with the reader and the vocabulary queue. */
  function coverage(rows) {
    const n = Progress.isConfigured() ? Progress.introducedCount() : 0;
    const known = Progress.getKnown();
    let kt = 0, it = 0, ut = 0, kd = 0;
    rows.forEach(r => {
      if (r.guid && known[r.guid]) { kt += r.n; kd++; }
      else if (r.order && r.order <= n) it += r.n;
      else ut += r.n;
    });
    return { knownTokens: kt, introducedTokens: it, unknownTokens: ut, knownDistinct: kd };
  }

  /* The only genuinely actionable number on the page: learn the top N unknown words from this
     text and coverage moves from here to there. */
  function curve(rows, cov, total) {
    const unknown = rows.filter(r => {
      const known = Progress.getKnown();
      if (r.guid && known[r.guid]) return false;
      return !(r.order && Progress.isConfigured() && r.order <= Progress.introducedCount());
    });
    const base = cov.knownTokens + cov.introducedTokens;
    const out = [];
    let run = 0;
    unknown.forEach((r, i) => {
      run += r.n;
      if ([9, 19, 49, 99, 199].includes(i)) out.push({ n: i + 1, pct: (base + run) / total * 100 });
    });
    return { base: base / total * 100, points: out, unknown };
  }

  /* ---------- render one source ---------- */
  let current = null;

  function renderCurrent() {
    if (!current) { $('#result').hidden = true; return; }
    $('#result').hidden = false;
    const { name, total, distinct, rows } = current;
    const cov = coverage(rows);
    const cur = curve(rows, cov, total);

    $('#r-title').textContent = name;
    $('#r-stats').innerHTML = [
      ['Tokens', nf(total)], ['Distinct', nf(distinct)],
      ['Known', Math.round(cov.knownTokens / total * 100) + '%'],
      ['Coverage now', Math.round(cur.base) + '%'],
      ['Unknown words', nf(cur.unknown.length)],
    ].map(([k, v]) => `<div class="stat"><span>${k}</span><strong>${v}</strong></div>`).join('');

    $('#r-curve').innerHTML = cur.points.length
      ? `<p class="sub">Learn the most frequent unknown words from this text and coverage goes:</p>` +
        '<div class="curve">' + `<span class="cpt"><b>${Math.round(cur.base)}%</b><i>now</i></span>` +
        cur.points.map(p => `<span class="cpt"><b>${Math.round(p.pct)}%</b><i>+${p.n} words</i></span>`).join('') +
        '</div>'
      : '';

    /* Two piles, because they need opposite actions: a word already in the deck arrives on its
       own and only needs waiting for; a word that is not in the deck at all will never arrive
       unless it is added. Lumping them hides the only decision this page exists to support. */
    const inDeck = cur.unknown.filter(r => r.order);
    const notInDeck = cur.unknown.filter(r => !r.order);
    $('#r-split').innerHTML =
      `<div class="split"><b>${nf(inDeck.length)}</b> already in the deck, arriving later —
         nothing to do but get there${inDeck.length ? `, soonest at position ${nf(Math.min(...inDeck.map(r => r.order)))}` : ''}.</div>
       <div class="split warn"><b>${nf(notInDeck.length)}</b> not in the deck at all —
         these will never arrive on their own.</div>`;

    $('#r-rows').innerHTML = tableFor(rows.slice(0, 300));
  }

  function tableFor(rows) {
    const known = Progress.getKnown();
    const n = Progress.isConfigured() ? Progress.introducedCount() : 0;
    return '<table class="freq"><thead><tr><th>#</th><th>word</th><th>romanization</th>' +
      '<th>gloss</th><th>status</th></tr></thead><tbody>' +
      rows.map(r => {
        const st = r.guid && known[r.guid] ? ['known', 'known']
          : r.order && r.order <= n ? ['seen', 'in Anki']
          : r.order ? ['new', 'deck #' + nf(r.order)]
          : ['unseen', 'not in deck'];
        return `<tr><td class="fn">${r.n}</td>` +
          `<td class="${r.telugu ? 'telugu' : 'mono'}">${esc(r.surface)}</td>` +
          `<td class="mono amber">${esc(r.roman || '')}</td>` +
          `<td class="fg">${esc(r.gloss || '')}</td>` +
          `<td><span class="tag ${st[0]}">${st[1]}</span></td></tr>`;
      }).join('') + '</tbody></table>';
  }

  /* ---------- saved sources & totals ---------- */
  function renderSaved() {
    const saved = read();
    $('#saved').innerHTML = saved.length
      ? saved.map((s, i) =>
          `<div class="srow"><b>${esc(s.name)}</b>
            <span>${nf(s.total)} tokens · ${nf(s.rows.length)} distinct</span>
            <button class="btn small" data-open="${i}" type="button">Open</button>
            <button class="btn small danger" data-del="${i}" type="button">Remove</button></div>`).join('')
      : '<p class="empty">Nothing saved yet. Analyse a text and press Save.</p>';
    renderTotals(saved);
  }

  function renderTotals(saved) {
    if (saved.length < 1) { $('#totals').innerHTML = ''; return; }
    const agg = new Map();
    saved.forEach(s => s.rows.forEach(r => {
      const e = agg.get(r.key) || { ...r, n: 0, sources: 0 };
      e.n += r.n; e.sources++; agg.set(r.key, e);
    }));
    const rows = [...agg.values()]
      .sort((a, b) => b.sources - a.sources || b.n - a.n);
    const known = Progress.getKnown();
    const n = Progress.isConfigured() ? Progress.introducedCount() : 0;
    const worth = rows.filter(r => !(r.guid && known[r.guid]) && !(r.order && r.order <= n));

    $('#totals').innerHTML =
      `<p class="sub">Across <b>${saved.length}</b> source${saved.length === 1 ? '' : 's'}:
        ${nf(rows.length)} distinct words, ${nf(worth.length)} of them not yet known.
        Ranked by how many sources a word turns up in — a word in four texts out of five is
        worth more than one that appears nine times in a single text.</p>` +
      '<table class="freq"><thead><tr><th>src</th><th>#</th><th>word</th><th>romanization</th>' +
      '<th>gloss</th><th>status</th></tr></thead><tbody>' +
      worth.slice(0, 300).map(r => {
        const st = r.order ? ['new', 'deck #' + nf(r.order)] : ['unseen', 'not in deck'];
        return `<tr><td class="fn">${r.sources}</td><td class="fn">${r.n}</td>` +
          `<td class="${r.telugu ? 'telugu' : 'mono'}">${esc(r.surface)}</td>` +
          `<td class="mono amber">${esc(r.roman || '')}</td>` +
          `<td class="fg">${esc(r.gloss || '')}</td>` +
          `<td><span class="tag ${st[0]}">${st[1]}</span></td></tr>`;
      }).join('') + '</tbody></table>';
    $('#totals').dataset.rows = JSON.stringify(worth.slice(0, 2000).map(r =>
      [r.sources, r.n, r.surface, r.roman || '', r.gloss || '', r.order || '']));
  }

  const csv = rows => rows.map(r => r.map(c =>
    /[",\n]/.test(String(c)) ? '"' + String(c).replace(/"/g, '""') + '"' : c).join(',')).join('\n');

  function download(name, body) {
    const b = new Blob([body], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = name; a.click();
    URL.revokeObjectURL(a.href);
  }

  /* ---------- events ---------- */
  $('#btn-run').addEventListener('click', () => {
    const raw = $('#input').value.trim();
    if (!raw) return;
    const name = $('#name').value.trim() || 'Untitled';
    const a = analyse(raw);
    current = { name, ...a };
    renderCurrent();
    $('#result').scrollIntoView({ block: 'start' });
  });

  $('#btn-save').addEventListener('click', () => {
    if (!current) return;
    const saved = read();
    const i = saved.findIndex(s => s.name === current.name);
    /* Only the frequency rows are kept, not the text: the pasted source may be copyrighted,
       and the counts are the whole point anyway. */
    const rec = { name: current.name, total: current.total,
                  rows: current.rows.map(r => ({ key: r.key, surface: r.surface, n: r.n,
                                                 telugu: r.telugu, order: r.order,
                                                 guid: r.guid, roman: r.roman, gloss: r.gloss })) };
    if (i >= 0) saved[i] = rec; else saved.push(rec);
    write(saved); renderSaved();
  });

  $('#saved').addEventListener('click', e => {
    const o = e.target.closest('[data-open]'), d = e.target.closest('[data-del]');
    const saved = read();
    if (o) {
      const s = saved[+o.dataset.open];
      current = { name: s.name, total: s.total, distinct: s.rows.length, rows: s.rows };
      renderCurrent(); $('#result').scrollIntoView({ block: 'start' });
    } else if (d) {
      saved.splice(+d.dataset.del, 1); write(saved); renderSaved();
    }
  });

  $('#btn-csv').addEventListener('click', () => {
    if (!current) return;
    download(`${current.name.replace(/\W+/g, '-')}-frequency.csv`,
      csv([['count', 'word', 'romanization', 'gloss', 'deck_position'],
        ...current.rows.map(r => [r.n, r.surface, r.roman || '', r.gloss || '', r.order || ''])]));
  });

  $('#btn-csv-all').addEventListener('click', () => {
    const rows = JSON.parse($('#totals').dataset.rows || '[]');
    if (!rows.length) return;
    download('all-sources-frequency.csv',
      csv([['sources', 'count', 'word', 'romanization', 'gloss', 'deck_position'], ...rows]));
  });

  $('#btn-clear').addEventListener('click', () => {
    if (!confirm('Remove every saved source? Your known-word marks are not affected.')) return;
    write([]); renderSaved();
  });

  renderSaved();
})();
