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

  const _FOLD = { 'ā':'a','ī':'i','ū':'u','ē':'e','ō':'o','ṭ':'t','ḍ':'d','ṇ':'n','ḷ':'l','ṁ':'m','ṣ':'s','ś':'s','ṛ':'r' };
  const fold = s => (s || '').toLowerCase().replace(/[āīūēōṭḍṇḷṁṣśṛ]/g, c => _FOLD[c]).replace(/[^a-z]/g, '');

  const TEXTS = window.READER_TEXTS || {};

  /* ---------- transcripts loaded in the browser ----------
   * The public site ships the tooling, not other people's content. A transcript you hold is
   * parsed, resolved and stored here on your own machine — nothing is uploaded, and nothing
   * copyrighted has to enter the repository for the page to be fully usable.
   *
   * The offline pipeline is still the better resolver where it can be used: it romanizes
   * script with te2rom, filters English against a real dictionary, and does the loose
   * chat-romanization match. This path is exact-only. For Telugu-script transcripts that is
   * most of the difference anyway, since script matches the master's script directly.
   */
  const LK = 'rtt.readLocal';
  const TSLINE = /^(\d{2}):(\d{2}):(\d{2})[.,](\d+)\s+(.*)$/;

  function parseTranscript(raw, name) {
    let ytid = '';
    const lines = [];
    for (const line of raw.split(/\r?\n/)) {
      if (line.startsWith('#')) {
        const m = line.match(/(?:watch\/|watch\?v=|youtu\.be\/|embed\/)([\w-]{11})/);
        if (m) ytid = m[1];
        continue;
      }
      const m = TSLINE.exec(line.trim());
      if (m) {
        const t = +m[1] * 3600 + +m[2] * 60 + +m[3] + +('0.' + m[4]);
        if (m[5].trim()) lines.push([t, m[5].trim()]);
      } else if (line.trim()) {
        lines.push([null, line.trim()]);
      }
    }
    if (!lines.length) return null;

    // Caption chunks are two or three words each; reading 2,500 fragments is not reading.
    // Merge to a sentence-ish length but keep the first chunk's time, so seeking still lands.
    const merged = [];
    let buf = [], t0 = null;
    for (const [t, txt] of lines) {
      if (t0 === null) t0 = t;
      buf.push(txt);
      if (buf.join(' ').length >= 90) { merged.push([t0, buf.join(' ')]); buf = []; t0 = null; }
    }
    if (buf.length) merged.push([t0, buf.join(' ')]);

    const lex = [], lexidx = new Map(), sections = [];
    let cur = [], start = merged[0][0] ?? 0;
    const flush = () => { if (cur.length) sections.push({ title: fmtStamp(start), lines: cur }); };
    for (const [t, txt] of merged) {
      if (t != null && t - start > 300 && cur.length) { flush(); cur = []; start = t; }
      const ln = { t: Lex.resolveLine(txt, lex, lexidx), en: '' };
      if (t != null) ln.s = Math.round(t * 100) / 100;
      cur.push(ln);
    }
    flush();

    const freq = new Map();
    sections.forEach(sc => sc.lines.forEach(l => l.t.forEach(tk => {
      if (tk[1] !== 'p' && tk[2] >= 0) freq.set(tk[2], (freq.get(tk[2]) || 0) + 1);
    })));
    lex.forEach((l, i) => l.n = freq.get(i) || 0);

    return { slug: 'yours:' + name, title: name, local: true, youtube: ytid, audio: '',
             script: lex.some(l => l.te), generated: new Date().toISOString().slice(0, 10),
             blurb: 'Loaded from your machine. Not stored in the repository.',
             lex, sections };
  }

  const fmtStamp = s => `${Math.floor((s || 0) / 60)}:${String(Math.floor((s || 0) % 60)).padStart(2, '0')}`;

  /* Restore anything loaded previously, before the picker is built. */
  (() => {
    let saved = [];
    try { saved = JSON.parse(localStorage.getItem(LK)) || []; } catch {}
    saved.forEach(t => { TEXTS[t.slug] = t; });
  })();
  const slugs = () => Object.keys(TEXTS);
  const SLUGS = slugs();
  if (!slugs().length) {
    $('#reader').innerHTML = '<p class="empty">No texts are baked yet. Run <span class="mono">python3 tools/build_reader.py --all</span>.</p>';
    return;
  }

  /* Reader-local status for every token, keyed by the fold. Master words additionally mirror
     their `known` into Progress so the rest of the site sees it. */
  let status = read(K.st, {});
  const saveStatus = () => write(K.st, status);

  let slug = read(K.pos, {}).slug || slugs()[0];
  if (!TEXTS[slug]) slug = slugs()[0];
  let section = 0, showEn = true, focus = null;
  /* Script or romanization for the body text. Defaults to romanization: the script is
     unreadable to the learner today, and a page of it is a wall rather than practice.
     Persisted, because it is the setting most likely to change as reading improves. */
  let script = read('rtt.readScript', false);

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
    $('#texts').innerHTML = slugs().map(s =>
      `<button class="chip${s === slug ? ' on' : ''}" data-slug="${esc(s)}">${esc(TEXTS[s].title)}${
        TEXTS[s].local ? ' <b>yours</b>' : TEXTS[s].private ? ' <b>private</b>' : ''}</button>`).join('');
    const t = text();
    $('#blurb').textContent = t.blurb || '';
    $('#toggle-script').hidden = !t.script;
    $('#btn-forget').hidden = !t.local;
    $('#credit').hidden = !t.youtube;
    if (t.youtube) {
      $('#credit').innerHTML = `Audio and transcript belong to the original creator and are used
        here for private study. Watch the source on
        <a href="https://www.youtube.com/watch?v=${esc(t.youtube)}" target="_blank" rel="noopener">YouTube</a>.`;
    }
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
        const shown = (!script && tok[3]) ? tok[3] : surface;
        return `<span class="tk ${st}${kind === '~' ? ' approx' : ''}${script && tok[3] ? ' script' : ''}"`
             + ` data-l="${li}" data-t="${ti}" data-k="${esc(key)}">${esc(shown)}</span>`;
      }).join('');
      const cue = ln.s != null
        ? `<button class="cue" data-seek="${ln.s}" title="Play from here">${clock(ln.s)}</button>` : '';
      return `<p class="rline" data-li="${li}"${ln.s != null ? ` data-s="${ln.s}"` : ''}>` +
             cue + `<span class="rte">${body}</span>` +
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

    const rom = tok[3] || null;
    let head = rom
      ? `<h3>${esc(script ? surface : rom)}</h3>
         <p class="palt ${script ? 'mono' : 'telugu'}">${esc(script ? rom : surface)}</p>`
      : `<h3>${esc(surface)}</h3>`;
    let body = '';
    if (lx && lx.en) {
      body += `<p class="pgloss">${esc(lx.en)}</p>`;
      /* The heading already shows both forms for a script token. Repeat the deck's spelling
         only when it differs from what is on the page — which is the case worth seeing. */
      const sameAsHead = rom && fold(lx.r) === fold(rom);
      if (!sameAsHead) {
        body += `<p class="pforms"><span class="mono amber">${esc(lx.r)}</span>` +
                (lx.te && lx.te !== surface ? ` <span class="telugu">${esc(lx.te)}</span>` : '') + '</p>';
      }
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
    slugs().forEach(s => TEXTS[s].lex.forEach(l => { if (!byKey.has(l.k)) byKey.set(l.k, l); }));
    // first line each word appears in, so the export carries its context
    const ctx = new Map();
    slugs().forEach(s => TEXTS[s].sections.forEach(sec => sec.lines.forEach(ln => {
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
    slug = b.dataset.slug; section = 0; curLine = -1;
    write(K.pos, { slug });
    renderPicker(); repaint(); closePanel(); setupPlayer();
  });

  $('#sections').addEventListener('click', e => {
    const b = e.target.closest('[data-section]');
    if (!b) return;
    section = +b.dataset.section; curLine = -1;
    renderPicker(); repaint(); closePanel();
    $('#reader').scrollIntoView({ block: 'start' });
  });

  $('#toggle-script').addEventListener('click', () => {
    script = !script;
    write('rtt.readScript', script);
    $('#toggle-script').classList.toggle('on', script);
    $('#toggle-script').textContent = script ? 'Telugu script' : 'Romanized';
    renderText();
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

  /* ---------- playback ----------
   * One interface over two backends. A local mp3 is the better experience — instant seeks,
   * works offline — but it cannot be published: the file is 105 MB and the episode is not
   * ours to redistribute. Embedding YouTube moves both problems to Google, at the cost of
   * needing a network and an http(s) origin (an embed will not run from file://).
   *
   * THE IFRAME IS CREATED ONCE AND NEVER REPLACED. That is the whole caching story. Seeking a
   * live player reuses whatever YouTube has already buffered and costs nothing; calling
   * loadVideoById, or re-rendering the container, tears the player down and re-downloads from
   * scratch. So switching sections only seeks, and the player survives every repaint.
   */
  const clock = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  let follow = true, sentence = false, curLine = -1, loopOn = false;

  const audio = new Audio();
  let yt = null, ytReady = false, ytPending = null, mode = 'none', tick = null;

  const P = {
    get paused() {
      if (mode === 'yt') return !yt || !ytReady || yt.getPlayerState() !== 1;
      return audio.paused;
    },
    get time() {
      if (mode === 'yt') return (yt && ytReady) ? yt.getCurrentTime() : 0;
      return audio.currentTime;
    },
    play() {
      if (mode === 'yt') { if (ytReady) yt.playVideo(); }
      else audio.play().catch(() => say('The browser blocked playback — press play once.'));
    },
    pause() { mode === 'yt' ? (ytReady && yt.pauseVideo()) : audio.pause(); },
    seek(sec) {
      if (mode === 'yt') {
        if (ytReady) yt.seekTo(sec, true); else ytPending = sec;
        return ytReady;
      }
      /* Seeking a file whose metadata has not loaded snaps silently back to zero, which is
         exactly what an hour-long mp3 does on the first click. Queue it instead. */
      if (audio.readyState >= 1) { audio.currentTime = sec; return true; }
      pendingSeek = sec;
      return false;
    },
    rate(r) { mode === 'yt' ? (ytReady && yt.setPlaybackRate(r)) : (audio.playbackRate = r); },
  };

  let pendingSeek = null;
  audio.addEventListener('loadedmetadata', () => {
    if (pendingSeek != null) { audio.currentTime = pendingSeek; pendingSeek = null; }
  });
  audio.addEventListener('error', () => {
    if (mode === 'audio') say('Audio not found — it is kept locally, not committed.');
  });

  window.onYouTubeIframeAPIReady = () => {
    const t = text();
    if (!t.youtube) return;
    yt = new YT.Player('ytframe', {
      videoId: t.youtube,
      playerVars: { rel: 0, modestbranding: 1, playsinline: 1 },
      events: {
        onReady: () => {
          ytReady = true;
          if (ytPending != null) { yt.seekTo(ytPending, true); yt.playVideo(); ytPending = null; }
        },
        onStateChange: syncPlay,
      },
    });
  };

  function setupPlayer() {
    const t = text();
    mode = t.youtube ? 'yt' : (t.audio ? 'audio' : 'none');
    $('#player').hidden = mode === 'none';
    $('#ytwrap').hidden = mode !== 'yt';

    if (mode === 'audio') {
      if (!audio.src.endsWith(t.audio)) {
        audio.preload = 'metadata'; audio.src = t.audio; pendingSeek = null; audio.load();
      }
    } else {
      audio.pause();
    }
    if (mode === 'yt' && !yt && window.YT && YT.Player) window.onYouTubeIframeAPIReady();
    if (mode !== 'none' && !tick) tick = setInterval(onTick, 250);
  }

  function lineTimes() {
    const sec = text().sections[section];
    return sec ? sec.lines.map(l => (l.s == null ? null : l.s)) : [];
  }

  function playLine(sec0, li) {
    curLine = li == null ? curLineAt(sec0) : li;
    paintCurrent();
    const ok = P.seek(sec0);
    P.play();
    if (!ok) say('Loading…');
  }

  function curLineAt(t) {
    const ts = lineTimes();
    let best = -1;
    for (let i = 0; i < ts.length; i++) if (ts[i] != null && ts[i] <= t + 0.01) best = i;
    return best;
  }

  function paintCurrent() {
    document.querySelectorAll('.rline.playing').forEach(e => e.classList.remove('playing'));
    const el = document.querySelector(`.rline[data-li="${curLine}"]`);
    if (!el) return;
    el.classList.add('playing');
    if (follow) {
      const r = el.getBoundingClientRect();
      if (r.top < 90 || r.bottom > innerHeight - 80) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }

  /* The transcript gives starts only; a line ends where the next one begins, which is all
     sentence mode and looping need. */
  function endOf(li) {
    const ts = lineTimes();
    for (let i = li + 1; i < ts.length; i++) if (ts[i] != null) return ts[i];
    return Infinity;
  }

  /* Polled rather than event-driven: YouTube has no timeupdate, and one timer for both
     backends keeps the two paths from drifting apart in behaviour. */
  function onTick() {
    if (mode === 'none' || pendingSeek != null || ytPending != null) return;
    const ts = lineTimes();
    if (!ts.length) return;
    const now = P.time;
    $('#elapsed').textContent = clock(now);
    if (curLine >= 0 && (sentence || loopOn) && now >= endOf(curLine) - 0.15) {
      if (loopOn) { P.seek(ts[curLine]); return; }
      P.pause();
      return;
    }
    const i = curLineAt(now);
    if (i !== curLine) { curLine = i; paintCurrent(); }
  }

  const syncPlay = () => { $('#play').textContent = P.paused ? '▶' : '❚❚'; };
  audio.addEventListener('play', syncPlay);
  audio.addEventListener('pause', syncPlay);

  $('#reader').addEventListener('click', e => {
    const c = e.target.closest('.cue');
    if (!c) return;
    e.stopPropagation();
    playLine(+c.dataset.seek, +c.closest('.rline').dataset.li);
  });

  $('#play').addEventListener('click', () => {
    if (P.paused) {
      if (curLine < 0) {
        const ts = lineTimes(); const i = ts.findIndex(x => x != null);
        if (i >= 0) return playLine(ts[i], i);
      }
      P.play();
    } else P.pause();
    setTimeout(syncPlay, 120);
  });

  $('#prev').addEventListener('click', () => step(-1));
  $('#next').addEventListener('click', () => step(1));
  function step(d) {
    const ts = lineTimes();
    let i = curLine + d;
    while (i >= 0 && i < ts.length && ts[i] == null) i += d;
    if (i < 0 || i >= ts.length) return;
    playLine(ts[i], i);
  }

  $('#loop').addEventListener('click', () => {
    loopOn = !loopOn;
    $('#loop').classList.toggle('on', loopOn);
    if (loopOn && P.paused && curLine >= 0) playLine(lineTimes()[curLine], curLine);
  });
  $('#sentence').addEventListener('click', () => {
    sentence = !sentence;
    $('#sentence').classList.toggle('on', sentence);
    $('#sentence').textContent = sentence ? 'Sentence mode' : 'Continuous';
  });
  $('#follow').addEventListener('click', () => {
    follow = !follow;
    $('#follow').classList.toggle('on', follow);
    $('#follow').textContent = follow ? 'Following' : 'Not following';
  });

  /* Fixed steps rather than a slider: YouTube only honours its own set of rates and silently
     ignores anything else, so a free slider would lie about what it was doing. */
  $('#rates').addEventListener('click', e => {
    const b = e.target.closest('[data-rate]');
    if (!b) return;
    $('#rates').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
    P.rate(+b.dataset.rate);
  });

  document.addEventListener('keydown', e => {
    const t = e.target;
    if (t instanceof Element && t.matches('input, textarea')) return;
    if (!$('#panel').hidden || $('#player').hidden) return;
    if (e.key === ' ') { e.preventDefault(); $('#play').click(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    else if (e.key.toLowerCase() === 'l') { e.preventDefault(); $('#loop').click(); }
  });

  /* ---------- loading and forgetting your own transcripts ---------- */
  function persistLocal() {
    const mine = slugs().filter(k => TEXTS[k].local).map(k => TEXTS[k]);
    try { localStorage.setItem(LK, JSON.stringify(mine)); return true; }
    catch { say('Too large to keep between visits — it will work until you reload.'); return false; }
  }

  function addText(t) {
    TEXTS[t.slug] = t;
    slug = t.slug; section = 0; curLine = -1;
    write(K.pos, { slug });
    persistLocal();
    renderPicker(); repaint(); setupPlayer();
    const words = t.lex.reduce((a, l) => a + l.n, 0);
    say(`Loaded ${t.sections.length} section${t.sections.length === 1 ? '' : 's'}, ${nf(words)} words.`);
  }

  function ingest(raw, name) {
    const t = parseTranscript(raw, name);
    if (!t) return say('Could not find any lines in that file.');
    addText(t);
    $('#loadbox').open = false;
  }

  $('#file').addEventListener('change', e => {
    const f = e.target.files[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => ingest(String(r.result), $('#tname').value.trim() || f.name.replace(/\.[^.]+$/, ''));
    r.readAsText(f);
    e.target.value = '';
  });

  $('#btn-paste').addEventListener('click', () => {
    const raw = $('#paste').value.trim();
    if (!raw) return say('Nothing pasted.');
    ingest(raw, $('#tname').value.trim() || 'Pasted transcript');
    $('#paste').value = '';
  });

  $('#btn-forget').addEventListener('click', () => {
    if (!TEXTS[slug] || !TEXTS[slug].local) return say('That one is built into the site.');
    if (!confirm(`Remove "${TEXTS[slug].title}"? Your word marks are kept.`)) return;
    delete TEXTS[slug];
    slug = slugs()[0]; section = 0; curLine = -1;
    persistLocal();
    renderPicker(); repaint(); setupPlayer();
  });

  /* ---------- boot ---------- */
  $('#generated').textContent = text().generated;
  $('#toggle-script').classList.toggle('on', script);
  $('#toggle-script').textContent = script ? 'Telugu script' : 'Romanized';
  renderPicker(); repaint(); setupPlayer(); syncPlay();
})();
