/* Text analyzer — paste Telugu, find out which words are worth learning first.
 *
 * On the fly, not baked. This runs *before* a text is worth ingesting: the question it answers
 * is "is this worth my time, and which twenty words would make it readable" — and you need
 * that answer while deciding, not after committing to a build step.
 *
 * MATCHING
 * Telugu script matches the master's script directly, romanization matches the folded
 * romanization, and anything unmatched still gets romanized by the te2rom port so the table is
 * readable. Every path is exact — nothing here guesses the way the reader's loose fold does,
 * because a frequency table full of wrong matches is worse than one with honest gaps.
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

  /* Tokenizing and matching live in Lex, shared with the reader's transcript loader. Two
     copies of that logic would drift, and a frequency table built by a different matcher than
     the reader uses would quietly disagree with it about what counts as known. */
  const { fold, isTelugu, lookup, keyOf, tokens } = Lex;

  /* ---------- analysis ---------- */
  function analyse(text) {
    const counts = new Map();
    let total = 0;
    for (const tok of tokens(text)) {
      const key = keyOf(tok);
      if (!key) continue;
      total++;
      const e = counts.get(key) || { key, surface: tok, n: 0, telugu: isTelugu(tok) };
      e.n++; counts.set(key, e);
    }
    const rows = [...counts.values()].map(e => {
      const w = lookup(e.surface);
      return Object.assign(e, {
        order: w ? w.order : 0, gloss: w ? w.english : '', guid: w ? w.guid : '',
        /* Unmatched script still gets a romanization — the whole point of the port. */
        roman: w ? w.roman : (e.telugu ? Te2Rom.romanize(e.surface) : e.surface),
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
    renderChunkTotals(saved);
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

  /* ---------- repeated chunks ---------- */
  /* Kept off `current` deliberately: mining is re-run whenever the thresholds move, and caching
     a result that the controls can invalidate is how the chip counts and the list came to
     disagree on the vocabulary queue. One source of truth, recomputed. */
  let mineText = '';

  const badge = w => w.fresh === 0
    ? '<span class="kind learn">learnable now</span>'
    : `<span class="kind fresh">${w.fresh} new word${w.fresh === 1 ? '' : 's'}</span>`;

  const slotHtml = (toks, slot) => toks
    .map((t, i) => i === slot || t === Chunks.SLOT ? '<span class="slot">&nbsp;</span>' : esc(t))
    .join(' ');

  function renderMine() {
    const el = $('#chunks');
    if (!mineText) { el.hidden = true; return; }
    el.hidden = false;
    const minCount = +$('#m-count').value, minFillers = +$('#m-fillers').value;
    $('#m-count-v').textContent = minCount + '\u00d7';
    $('#m-fillers-v').textContent = minFillers + ' fillers';

    const res = Chunks.mine(mineText, { minCount, minFillers });

    $('#m-fixed').innerHTML = res.fixed.length
      ? res.fixed.slice(0, 60).map(c =>
          `<div class="chunk${c.words.learnable ? ' learn' : ''}">
             <div class="chunk-te">${esc(c.toks.join(' '))}</div>
             <div class="chunk-rom">${esc(c.roman)}</div>
             <div class="chunk-meta"><span><b>${c.n}</b>\u00d7</span>
               <span>${c.lines} line${c.lines === 1 ? '' : 's'}</span>
               <span>${c.toks.length} words</span>${badge(c.words)}</div>
           </div>`).join('')
      : `<p class="mine-empty">Nothing repeats ${minCount} times or more. Either the text is short,
           or it genuinely does not repeat itself — lower the threshold to see.</p>`;

    $('#m-frames').innerHTML = res.frames.length
      ? res.frames.slice(0, 40).map(f =>
          `<div class="chunk${f.words.learnable ? ' learn' : ''}">
             <div class="chunk-te">${slotHtml(f.toks, f.slot)}</div>
             <div class="chunk-rom">${esc(f.roman)}</div>
             <div class="chunk-meta">
               <span class="kind ${f.kind}">${f.kind === 'inflection' ? 'verb form \u00b7 ' + esc(f.root) : 'lexical'}</span>
               <span><b>${f.fillers.length}</b> fillers</span>
               <span>${f.n}\u00d7 over ${f.lines} lines</span>${badge(f.words)}</div>
             <div class="fillers">${f.fillers.slice(0, 12).map(([w, n]) =>
               `<span class="filler">${esc(w)}<i>${n}</i></span>`).join('')}</div>
           </div>`).join('')
      : `<p class="mine-empty">No frame reaches ${minFillers} different fillers. Frames need a
           text that says the same shape about several different things — drop the requirement to
           2 and see what appears.</p>`;

    /* Stashed for the CSV button and for saving with the source. */
    $('#chunks').dataset.mined = JSON.stringify({
      fixed: res.fixed.slice(0, 200).map(c => [c.toks.join(' '), c.roman, c.n, c.lines, c.words.fresh]),
      frames: res.frames.slice(0, 100).map(f => [f.toks.join(' '), f.roman, f.kind, f.root,
        f.fillers.length, f.n, f.fillers.slice(0, 12).map(x => x[0]).join(' / ')]),
    });
  }

  ['#m-count', '#m-fillers'].forEach(sel =>
    $(sel).addEventListener('input', renderMine));

  $('#btn-csv-chunks').addEventListener('click', () => {
    const m = JSON.parse($('#chunks').dataset.mined || 'null');
    if (!m) return;
    const name = (current ? current.name : 'text').replace(/\W+/g, '-');
    download(`${name}-chunks.csv`, csv([
      ['kind', 'chunk', 'romanization', 'slot_kind', 'root', 'fillers', 'count', 'lines', 'new_words'],
      ...m.fixed.map(c => ['fixed', c[0], c[1], '', '', '', c[2], c[3], c[4]]),
      ...m.frames.map(f => ['frame', f[0], f[1], f[2], f[3], f[6], f[5], '', '']),
    ]));
  });

  /* ---------- chunks across sources ---------- */
  function renderChunkTotals(saved) {
    const withChunks = saved.filter(s => s.chunks && s.chunks.length);
    if (withChunks.length < 2) {
      $('#chunk-totals').innerHTML = `<p class="mine-empty">Needs at least two saved sources that
        were mined. ${withChunks.length === 1 ? 'One so far.' : 'None yet.'} Analyse a text, press
        Save, and repeat with another.</p>`;
      return;
    }
    const agg = new Map();
    withChunks.forEach(s => s.chunks.forEach(([te, rom, n]) => {
      const e = agg.get(te) || { te, rom, n: 0, sources: 0 };
      e.n += n; e.sources++; agg.set(te, e);
    }));
    const rows = [...agg.values()].filter(e => e.sources > 1)
      .sort((a, b) => b.sources - a.sources || b.n - a.n);
    $('#chunk-totals').innerHTML = rows.length
      ? rows.slice(0, 60).map(e =>
          `<div class="chunk"><div class="chunk-te">${esc(e.te)}</div>
             <div class="chunk-rom">${esc(e.rom)}</div>
             <div class="chunk-meta"><span><b>${e.sources}</b> sources</span>
               <span>${e.n}\u00d7 in total</span></div></div>`).join('')
      : `<p class="mine-empty">No chunk appears in more than one of your ${withChunks.length}
           mined sources yet.</p>`;
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
    mineText = raw;
    renderMine();
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
    /* The mined chunks ride along, so the cross-source view has something to compare. Only
       the top fixed phrases — enough to spot an overlap, small enough for localStorage. */
    const m = JSON.parse($('#chunks').dataset.mined || 'null');
    if (m) rec.chunks = m.fixed.slice(0, 120).map(c => [c[0], c[1], c[2]]);
    if (i >= 0) saved[i] = rec; else saved.push(rec);
    write(saved); renderSaved();
  });

  $('#saved').addEventListener('click', e => {
    const o = e.target.closest('[data-open]'), d = e.target.closest('[data-del]');
    const saved = read();
    if (o) {
      const s = saved[+o.dataset.open];
      current = { name: s.name, total: s.total, distinct: s.rows.length, rows: s.rows };
      /* The text itself was never stored, so chunks cannot be recomputed for a reopened
         source. Hide the panel rather than show the previous text's findings under this
         source's name. */
      mineText = ''; renderMine();
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
