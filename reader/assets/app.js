/* The Mini Stories reader. LingQ's reading loop — blue word, click, decide, yellow fades as
 * you learn — on this project's data and identity scheme.
 *
 * Canonical text is Telugu script, always. What is on screen is a render-time transform:
 * Colloquial.romanize (chat spelling), Te2Rom.romanize (the literary scheme), or the script
 * itself. Both romanizers are loaded from their existing homes, not copied — there is exactly
 * one implementation of each rule in this repo and this page is one more caller.
 *
 * Word state lives in WordLevels (levels.js), keyed by the same content-hash guids as the
 * word master and the old reader, which is what makes "known" portable across every text.
 */
(() => {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const nf = n => n.toLocaleString('en-US');
  const read = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const ZW = /[​-‍﻿]/g;
  const bareTe = s => (s || '').replace(ZW, '');
  const clock = s => `${Math.floor((s || 0) / 60)}:${String(Math.floor((s || 0) % 60)).padStart(2, '0')}`;

  /* Two baked datasets now — the mini stories and the Intensive Course lessons — merged into
     one reading list. Each ships its own `lex`, and a line's tokens hold INDEXES into that
     dataset's lex, so the second one's indexes have to be shifted by the length of the first.
     Merging without the shift silently points every Intensive Course word at whatever mini
     story word happens to sit at the same index, which reads as plausible nonsense rather
     than as an error. `src` is carried per story so a story can say where it came from. */
  const SETS = [window.MS_DATA, window.IC_DATA].filter(Boolean);
  const LEX = [];
  const STORIES = [];
  for (const d of SETS) {
    const off = LEX.length;
    LEX.push(...(d.lex || []));
    for (const st of (d.stories || [])) {
      /* Unique across datasets. Both number their stories from 1, and the router matched
         on the number alone — so #/story/1 found mini story 1 and every Intensive Course
         lesson was unreachable behind its mini-story twin. The prefix comes from the source
         rather than from array position, so adding a third dataset cannot silently reshuffle
         which id means what. */
      const pfx = /Intensive/.test(d.source || '') ? 'ic' : 'ms';
      STORIES.push(Object.assign({}, st, {
        id: pfx + st.num,
        src: d.source,
        lines: (st.lines || []).map(l => Object.assign({}, l, {
          t: (l.t || []).map(([w, k, i]) => [w, k, i < 0 ? i : i + off]),
        })),
      }));
    }
  }
  const BY_G = new Map(LEX.map((l, i) => [l.g, i]));
  const FORMLABEL = { future: 'habitual / future', present: 'present continuous', past: 'past',
    negFuture: 'negative future', negPast: 'negative past', negPresent: 'negative present',
    immFuture: 'immediate future', impFam: 'imperative', impPol: 'polite imperative',
    prohibFam: 'prohibitive', prohibPol: 'polite prohibitive', hort: "let's", must: 'must',
    mustNot: 'must not', can: 'can', cannot: 'cannot', wantTo: 'want to',
    dontWant: "don't want to", purpose: 'purposive', cond: 'conditional' };
  const PARTLABEL = { story: 'Story', 'retell-intro': 'Retold', questions: 'Questions' };
  const SECBREAK = { story: 1, 'retell-intro': 1, questions: 1 };

  if (!STORIES.length) {
    $('#pane').innerHTML = '<p class="pempty">No stories are baked yet. Run <code>python3 tools/build_ms_reader.py</code>.</p>';
    return;
  }

  /* Distinct words per story, once. */
  STORIES.forEach(s => {
    s.words = [...new Set(s.lines.flatMap(ln => ln.t.filter(t => t[2] >= 0).map(t => t[2])))];
  });

  /* ---------- display transform ---------- */
  let rom = read('rtt.msRom', 'iso');
  if (!['coll', 'iso', 'te'].includes(rom)) rom = 'iso';
  const romCache = new Map();
  function disp(te) {
    if (rom === 'te') return te;
    const key = rom + ':' + te;
    if (!romCache.has(key)) {
      const b = bareTe(te);
      romCache.set(key, rom === 'coll' ? Colloquial.romanize(b) : Te2Rom.romanize(b));
    }
    return romCache.get(key);
  }
  /* The secondary form shown under a headword: script when romanizing, ISO when in script. */
  const dispAlt = te => rom === 'te' ? Te2Rom.romanize(bareTe(te)) : te;

  /* ---------- state ---------- */
  let view = 'library';                 // library | story | vocab | stats
  let cur = null;                       // current story object
  let showEn = read('rtt.msEn', true);
  let sview = false, svIdx = 0;         // sentence view
  let curLine = -1, loopOn = false;
  const RATES = [0.7, 0.85, 1, 1.15, 1.3];
  let rateIdx = 2;
  let panel = { mode: 'lists', tab: 'lingqs', g: null, line: null, wtab: 'dict', aitab: 'explain',
                scope: 'lesson' };
  let vocab = { tab: 'all', sort: 'freq', q: '' };
  let reviewState = null;

  const effOf = g => WordLevels.effective(g);
  const clsOf = eff => eff === null ? 'new' : eff === 'k' ? '' : eff === 'x' ? 'lvlx' : 'lvl' + eff;
  const badgeOf = eff => {
    const cls = eff === null ? 'new' : 'b' + eff;
    const txt = eff === null ? '•' : eff === 'k' ? '✓' : eff === 'x' ? '✗' : eff;
    return `<span class="badge ${cls}">${txt}</span>`;
  };
  /* For a Verb Lab conjugation, the actual English equivalent of the cell — "he will drink",
     not just "a form of tāgu". The Lab's own cue() wrote these; we look the cell up by its
     script, so nothing is re-derived. */
  const equivCache = new Map();
  function verbEquiv(l) {
    if (!l.form || !l.lemma) return '';
    if (equivCache.has(l.g)) return equivCache.get(l.g);
    let out = '';
    if (typeof VERBS !== 'undefined' && typeof cells === 'function') {
      const v = VERBS.find(x => x.id === l.lemma);
      if (v) {
        const c = cells(v, [l.form]).find(c => c.tel === bareTe(l.te));
        if (c) out = c.cue;
      }
    }
    equivCache.set(l.g, out);
    return out;
  }
  /* Every place a meaning is shown, in one order — your own saved note, the baked gloss, the
     registry card, the stem-and-suffix breakdown, then the verb's dictionary form.

     THE LISTS AND THE CARD USED TO DISAGREE. This knew about `en` and verb forms but not about
     `sn` (a registry definition) or `p` (a decomposition), while the word card rendered both in
     sections of their own. So 230 of the mini stories' 444 words showed a full definition when
     clicked and nothing at all in the sentence list, the lesson list and the vocabulary table —
     the words most worth reviewing, since a registry card is written for exactly the words
     nothing else could gloss. Mirrors build_ms_reader.best_gloss so the reader and the Anki
     export cannot disagree either. */
  const glossOf = l => WordLevels.meaning(l.g) || l.en ||
    (l.sn && l.sn.length ? l.sn.map(x => x.g).filter(Boolean).join('; ') : '') ||
    (l.p && l.p.length ? l.p.map(x => `${x[0]} (${x[1]})`).join(' + ') : '') ||
    (l.head ? (verbEquiv(l) ? `“${verbEquiv(l)}” — ${FORMLABEL[l.form] || l.form} of ${l.head[0]}`
                            : `${FORMLABEL[l.form] || l.form || 'form'} of ${l.head[0]} — ${l.head[1]}`) : '');

  /* ---------- toast ---------- */
  let toastT = null;
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2600);
  }

  /* ---------- top bar ---------- */
  function renderTop() {
    const st = WordLevels.streak();
    $('#streak').innerHTML = st ? `🔥 ${st}` : '';
    const act = WordLevels.activityToday(), goal = WordLevels.goal();
    const frac = Math.min(1, act / goal), r = 9, c = 2 * Math.PI * r;
    $('#goalring').innerHTML =
      `<svg width="24" height="24" viewBox="0 0 24 24">
         <circle cx="12" cy="12" r="${r}" fill="none" stroke="#2c2c25" stroke-width="3.5"/>
         <circle cx="12" cy="12" r="${r}" fill="none" stroke="#8fa37e" stroke-width="3.5"
           stroke-linecap="round" stroke-dasharray="${(frac * c).toFixed(1)} ${c.toFixed(1)}"
           transform="rotate(-90 12 12)"/>
       </svg><span>${act}/${goal}</span>`;
    $('#knowntotal').textContent = nf(WordLevels.knownTotal());
    $$('#romseg button').forEach(b => b.classList.toggle('on', b.dataset.rom === rom));
    $$('#topnav a').forEach(a => a.classList.toggle('on',
      a.dataset.nav === (view === 'story' ? 'read' : view === 'library' ? 'read' : view)));
  }

  /* ---------- router ---------- */
  function router() {
    const h = location.hash;
    const m = /^#\/story\/([a-z]*\d+)/.exec(h);
    closeReview();
    document.querySelector('main').classList.toggle('withpanel', !h.startsWith('#/stats'));
    $('#panel').hidden = h.startsWith('#/stats');
    if (m && STORIES.some(s => s.id === m[1])) {
      view = 'story';
      openStory(STORIES.find(s => s.id === m[1]));
    } else if (h.startsWith('#/vocab')) {
      view = 'vocab'; cur = null; stopAudio(); renderVocab(); renderPanel();
    } else if (h.startsWith('#/stats')) {
      view = 'stats'; cur = null; stopAudio(); renderStats(); renderPanel();
    } else {
      view = 'library'; cur = null; stopAudio(); renderLibrary(); renderPanel();
    }
    renderTop();
  }

  /* ---------- library ---------- */
  function storyStats(s) {
    let known = 0, yellow = 0, blue = 0;
    s.words.forEach(i => {
      const e = effOf(LEX[i].g);
      if (e === 'k' || e === 'x') known++;
      else if (e === null) blue++;
      else yellow++;
    });
    return { known, yellow, blue, total: s.words.length };
  }

  function renderLibrary() {
    $('#playbar').hidden = true;
    const cards = STORIES.map(s => {
      const st = storyStats(s);
      const pct = st.total ? Math.round(st.known / st.total * 100) : 0;
      return `<button class="storycard" data-open="${s.id}">
        <span class="snum">${s.num}</span>
        <span class="meta"><b>${esc(disp(s.title.te) || s.title.en)}</b>
          <span>${esc(s.src || '')} · ${s.lines.length} ${s.src && s.src.indexOf('Intensive') >= 0 ? 'turns' : 'sentences'}${s.dur ? ' · ' + clock(s.dur) : ''}</span></span>
        <span class="wordbar"><span class="track">
            <i style="flex:${st.known};background:var(--green)"></i>
            <i style="flex:${st.yellow};background:var(--l1)"></i>
            <i style="flex:${st.blue};background:var(--new-b)"></i>
          </span><small>${pct}% known · ${st.blue} new</small></span>
        ${WordLevels.isRead(s.num) ? '<span class="done">✓</span>' : ''}
      </button>`;
    }).join('');
    /* The counts are derived, not written down. "11 of 60 stories" was a literal in the
       markup and would have quietly gone stale the moment a second source appeared. */
    const ms = STORIES.filter(s => s.id[0] === 'm').length;
    const ic = STORIES.length - ms;
    const bits = [];
    /* "voiced" is derived, not asserted. It was a literal, and it went stale the moment the
       native translations arrived and their audio stopped matching the text. */
    const voiced = STORIES.filter(s => s.id[0] === 'm' && s.audio).length;
    if (ms) bits.push(`${ms} of 60 Mini Stories${voiced ? `, ${voiced} voiced` : ' — audio pending re-recording'}`);
    if (ic) bits.push(`${ic} Intensive Course lesson${ic === 1 ? '' : 's'}`);
    $('#pane').innerHTML = `
      <div class="libhead"><h1>Reading</h1>
        <p>${bits.join(' · ')}. More appear here as they are prepared.</p></div>${cards}`;
    $$('#pane [data-open]').forEach(b =>
      b.addEventListener('click', () => { location.hash = '#/story/' + b.dataset.open; }));
  }

  /* ---------- reading view ---------- */
  function openStory(s) {
    const changed = cur !== s;
    cur = s; curLine = -1; sview = false; svIdx = 0;
    panel = { mode: 'lists', tab: 'lingqs', g: null, line: null, wtab: 'dict', aitab: 'explain',
              scope: 'lesson' };
    renderStory();
    renderPanel();
    if (changed) setupAudio();
  }

  function tokenHTML(tok, li, ti) {
    const [surface, kind, lx] = tok;
    if (kind === 'p' || lx < 0) {
      /* Romanized view: script punctuation-adjacent spacing survives; digits pass through. */
      return esc(surface);
    }
    /* OCR debris is on the page but it is not a word. Rendering it as a clickable blue token
       invites a lookup for a string that was never written, and counts it against the lesson's
       known-word progress. It stays visible — it is what the page says — but inert. */
    if (LEX[lx].junk) return `<span class="junk" title="unreadable — OCR debris">${esc(disp(surface))}</span>`;
    const eff = effOf(LEX[lx].g);
    return `<span class="w ${clsOf(eff)}" data-l="${li}" data-t="${ti}">${esc(disp(surface))}</span>`;
  }

  function lineHTML(ln, li) {
    const cue = ln.s != null
      ? `<button class="cue" data-seek="${li}" title="Play from here">▶</button>` : '';
    const en = showEn && ln.en && ln.p !== 'title'
      ? `<span class="ren">${esc(ln.en)}</span>` : '';
    return `<p class="rline${ln.p === 'title' || ln.p === 'retell-intro' ? ' meta' : ''}" data-li="${li}">
      ${cue}<span class="rte">${ln.t.map((t, ti) => tokenHTML(t, li, ti)).join('')}</span>${en}</p>`;
  }

  function renderStory() {
    const s = cur;
    const st = storyStats(s);
    const worked = st.total ? Math.round((st.total - st.blue) / st.total * 100) : 0;
    let body = '';
    let prevPart = null;
    s.lines.forEach((ln, li) => {
      if (li > 0 && ln.p !== prevPart && SECBREAK[ln.p]) {
        const label = PARTLABEL[ln.p];
        if (label && ln.p !== 'retell-intro') body += `<span class="seclabel">${label}</span>`;
        if (ln.p === 'retell-intro') body += `<span class="seclabel">${PARTLABEL['retell-intro']}</span>`;
      }
      if (ln.p === 'retell') prevPart = 'retell-intro';   // intro + retell are one section
      else prevPart = ln.p;
      body += lineHTML(ln, li);
    });

    $('#pane').innerHTML = `
      <div class="lessonbar">
        <a href="#/" title="All stories">‹ Stories</a>
        <span class="progress"><i style="width:${worked}%"></i></span>
        <span style="color:var(--ink2);font-size:12.5px">${worked}% worked</span>
      </div>
      <div class="lessonhead">
        <span class="snum">${s.num}</span>
        <span class="meta"><b>${esc(disp(s.title.te) || s.title.en)}</b>
          <span>${esc(s.src || '')} — Telugu</span></span>
        <span class="tools">
          <button class="iconbtn${showEn ? ' on' : ''}" id="t-en" title="Show / hide English (Shift+T)">EN</button>
          <button class="iconbtn" id="t-sv" title="Sentence view">☰</button>
          <button class="iconbtn mobonly" id="t-words" title="Word lists">📖</button>
        </span>
      </div>
      ${sview ? sentenceViewHTML() : `<div class="readtext" id="readtext">${body}</div>
      <div class="finishrow">
        <button class="finishbtn${WordLevels.isRead(s.num) ? ' done' : ''}" id="t-finish">
          ✓ ${WordLevels.isRead(s.num) ? 'Lesson finished' : 'Finish lesson'}</button>
      </div>`}`;

    $('#t-en') && $('#t-en').addEventListener('click', () => {
      showEn = !showEn; write('rtt.msEn', showEn); renderStory();
    });
    $('#t-sv').addEventListener('click', () => {
      sview = !sview;
      if (sview && curLine >= 0) svIdx = curLine;
      renderStory();
      // The panel owns the sentence/lesson switch, and entering sentence view is exactly when
      // that switch starts existing. Without this it only appeared once something else
      // happened to redraw the panel.
      renderPanel();
    });
    $('#t-finish') && $('#t-finish').addEventListener('click', finishLesson);
    $('#t-words').addEventListener('click', () => {
      panel.mode = 'lists'; panel.g = null; renderPanel(); sheetOpen();
    });
    wireSentenceView();
    paintPlaying();
  }

  function sentenceViewHTML() {
    const ln = cur.lines[svIdx];
    const n = wordsOfLine(ln).filter(stillLearning).length;
    return `<div class="sview">
      <p class="big">${ln.t.map((t, ti) => tokenHTML(t, svIdx, ti)).join('')}</p>
      ${showEn && ln.en ? `<p class="ren">${esc(ln.en)}</p>` : ''}
      <div class="navrow">
        <button id="sv-prev" ${svIdx === 0 ? 'disabled' : ''}>‹ Previous</button>
        <button id="sv-play" ${ln.s == null ? 'disabled' : ''}>▶ Play</button>
        <button id="sv-next" ${svIdx === cur.lines.length - 1 ? 'disabled' : ''}>Next ›</button>
      </div>
      <div class="navrow">
        <button id="sv-review" class="prim" ${n ? '' : 'disabled'}>
          ⚡ Review this sentence${n ? ` <span class="n">${n}</span>` : ''}</button>
      </div>
      <p class="count">${svIdx + 1} / ${cur.lines.length}${
        n ? '' : ' · nothing left to review in this one'}</p>
    </div>`;
  }
  function wireSentenceView() {
    if (!sview) return;
    /* The panel has to follow. When it is scoped to the sentence, moving to the next one and
       leaving the previous sentence's word list on screen is worse than not having the feature. */
    const go = i => { svIdx = i; renderStory(); renderPanel(); };
    $('#sv-prev').addEventListener('click', () => go(Math.max(0, svIdx - 1)));
    $('#sv-next').addEventListener('click', () => go(Math.min(cur.lines.length - 1, svIdx + 1)));
    $('#sv-play').addEventListener('click', () => playLine(svIdx));
    /* Cards for exactly the words in the sentence on screen, then the same words as a list.
       Scoped to the sentence rather than the lesson on purpose: the value is that you have
       just read them in context and still have that context in mind. */
    $('#sv-review').addEventListener('click', () => {
      const ln = cur.lines[svIdx];
      startReview(wordsOfLine(ln).filter(stillLearning),
                  { scope: `sentence ${svIdx + 1} of ${cur.lines.length}` });
    });
  }

  /* Status changed: recolour tokens in place instead of rebuilding the DOM under the cursor. */
  function repaintTokens() {
    if (!cur) return;
    $$('#pane .w').forEach(el => {
      const tok = cur.lines[+el.dataset.l].t[+el.dataset.t];
      el.className = 'w ' + clsOf(effOf(LEX[tok[2]].g)) +
        (el.classList.contains('focus') ? ' focus' : '');
    });
  }

  function finishLesson() {
    const s = cur;
    const blues = s.words.filter(i => effOf(LEX[i].g) === null).map(i => LEX[i].g);
    if (blues.length &&
        !confirm(`Mark the ${blues.length} remaining new (blue) word${blues.length === 1 ? '' : 's'} in this lesson as known?\n\nThis is LingQ's page-complete behaviour: anything you didn't stop on, you knew.`)) {
      return;
    }
    if (blues.length) WordLevels.setMany(blues, 'k');
    WordLevels.setRead(s.num, true);
    toast(blues.length ? `${blues.length} words marked known — lesson finished.` : 'Lesson finished.');
    renderStory(); renderPanel(); renderTop();
  }

  /* ---------- audio ---------- */
  const audio = new Audio();
  audio.preload = 'metadata';
  let pendingSeek = null;
  audio.addEventListener('loadedmetadata', () => {
    if (pendingSeek != null) { audio.currentTime = pendingSeek; pendingSeek = null; }
  });
  audio.addEventListener('error', () => {
    if (cur && cur.audio) toast('Audio not found — it is generated locally, not committed.');
  });
  const syncPlayBtn = () => { $('#pb-play').textContent = audio.paused ? '▶' : '❚❚'; };
  audio.addEventListener('play', syncPlayBtn);
  audio.addEventListener('pause', syncPlayBtn);

  function setupAudio() {
    audio.pause();
    $('#playbar').hidden = !cur || !cur.audio;
    if (!cur || !cur.audio) return;
    audio.src = cur.audio; pendingSeek = null; audio.load();
    audio.playbackRate = RATES[rateIdx];
    $('#pb-total').textContent = clock(cur.dur);
    $('#pb-scrub').max = cur.dur || 100;
    $('#pb-scrub').value = 0;
    $('#pb-elapsed').textContent = '0:00';
    syncPlayBtn();
  }
  function stopAudio() { audio.pause(); $('#playbar').hidden = true; }

  function seekTo(t) {
    if (audio.readyState >= 1) audio.currentTime = t; else pendingSeek = t;
  }
  function playLine(li) {
    const ln = cur.lines[li];
    if (ln.s == null) return;
    curLine = li;
    seekTo(ln.s);
    audio.play().catch(() => toast('The browser blocked playback — press play once.'));
    paintPlaying();
  }

  function lineAt(t) {
    if (!cur) return -1;
    for (let i = 0; i < cur.lines.length; i++) {
      const ln = cur.lines[i];
      if (ln.s != null && t >= ln.s - 0.01 && t < ln.e) return i;
    }
    return -1;
  }

  function paintPlaying() {
    $$('.rline.playing').forEach(e => e.classList.remove('playing'));
    const el = document.querySelector(`.rline[data-li="${curLine}"]`);
    if (!el) return;
    el.classList.add('playing');
    const r = el.getBoundingClientRect();
    if (r.top < 70 || r.bottom > innerHeight - 90) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }

  audio.addEventListener('timeupdate', () => {
    if (!cur || pendingSeek != null) return;
    const t = audio.currentTime;
    $('#pb-elapsed').textContent = clock(t);
    $('#pb-scrub').value = t;
    if (curLine >= 0 && loopOn && t >= cur.lines[curLine].e - 0.05) {
      audio.currentTime = cur.lines[curLine].s;
      return;
    }
    if (sview && curLine === svIdx && t >= cur.lines[svIdx].e - 0.05) {
      audio.pause();
      return;
    }
    const i = lineAt(t);
    if (i !== curLine && i >= 0) {
      curLine = i;
      if (sview) { svIdx = i; renderStory(); } else paintPlaying();
    }
  });

  $('#pb-play').addEventListener('click', () => {
    if (audio.paused) {
      if (curLine < 0) { const i = cur.lines.findIndex(l => l.s != null); if (i >= 0) return playLine(i); }
      audio.play().catch(() => {});
    } else audio.pause();
  });
  $('#pb-back').addEventListener('click', () => { audio.currentTime = Math.max(0, audio.currentTime - 5); });
  $('#pb-fwd').addEventListener('click', () => { audio.currentTime = Math.min(cur ? cur.dur : 0, audio.currentTime + 5); });
  $('#pb-loop').addEventListener('click', () => {
    loopOn = !loopOn;
    $('#pb-loop').classList.toggle('on', loopOn);
  });
  $('#pb-rate').addEventListener('click', () => {
    rateIdx = (rateIdx + 1) % RATES.length;
    audio.playbackRate = RATES[rateIdx];
    $('#pb-rate').textContent = RATES[rateIdx] + '×';
  });
  $('#pb-scrub').addEventListener('input', e => { seekTo(+e.target.value); });

  function step(d) {
    if (!cur) return;
    let i = (curLine < 0 ? (d > 0 ? -1 : cur.lines.length) : curLine) + d;
    while (i >= 0 && i < cur.lines.length && cur.lines[i].s == null) i += d;
    if (i >= 0 && i < cur.lines.length) playLine(i);
  }

  /* ---------- right panel ---------- */
  /* True when the panel is showing one sentence rather than the whole lesson. Only possible
     in sentence view — there is no "current sentence" to scope to while reading the page. */
  const sentenceScope = () => sview && cur && panel.scope === 'sentence';

  function panelWords() {
    /* In a story: that story's words, or just the sentence on screen when scoped to it.
       Elsewhere: the whole corpus.
       Sorted alphabetically, not by first occurrence — these lists are used to review and to
       find a word again, and hunting for one in reading order means re-reading the story. Sorts
       on the DISPLAYED form so the order matches what is on screen in whichever script is
       selected; localeCompare keeps Telugu in its own collation rather than by code point. */
    if (sentenceScope()) {
      const seen = new Set();
      const idx = [];
      for (const [, , i] of (cur.lines[svIdx].t || [])) {
        if (i >= 0 && !seen.has(i) && !LEX[i].junk) { seen.add(i); idx.push(i); }
      }
      return idx
        .map(i => ({ i, l: LEX[i], eff: effOf(LEX[i].g) }))
        .sort((a, b) => disp(a.l.te).localeCompare(disp(b.l.te), undefined, { sensitivity: 'base' }));
    }
    const idxs = cur ? cur.words : LEX.map((_, i) => i);
    return idxs
      .filter(i => !LEX[i].junk)            // not words; see tokenHTML
      .map(i => ({ i, l: LEX[i], eff: effOf(LEX[i].g) }))
      .sort((a, b) => disp(a.l.te).localeCompare(disp(b.l.te), undefined, { sensitivity: 'base' }));
  }

  function renderPanel() {
    if (view === 'stats') { $('#panelbody').innerHTML = ''; return; }
    if (panel.mode === 'word' && panel.g) return renderWordCard();
    if (view === 'vocab') { renderPanelForVocab(); return; }

    const words = panelWords();
    const groups = {
      lingqs: words.filter(w => ['1', '2', '3', '4'].includes(w.eff)),
      new: words.filter(w => w.eff === null),
      all: words,
    };
    const rows = groups[panel.tab] || [];
    const dueAll = LEX.filter(l => WordLevels.isDue(l.g));
    const lessonLingqs = groups.lingqs;
    const lessonPool = words.filter(w => stillLearning(w.l));

    const scoper = (sview && cur) ? `
      <div class="pscope">
        <button data-pscope="sentence" class="${panel.scope === 'sentence' ? 'on' : ''}"
          >Sentence ${svIdx + 1}</button>
        <button data-pscope="lesson" class="${panel.scope === 'lesson' ? 'on' : ''}"
          >Whole lesson</button>
      </div>` : '';
    $('#panelbody').innerHTML = scoper + `
      <div class="ptabs">
        <button data-ptab="lingqs" class="${panel.tab === 'lingqs' ? 'on' : ''}">LingQs (${groups.lingqs.length})</button>
        <button data-ptab="new" class="${panel.tab === 'new' ? 'on' : ''}">New Words (${groups.new.length})</button>
        <button data-ptab="all" class="${panel.tab === 'all' ? 'on' : ''}">All Words (${groups.all.length})</button>
      </div>
      <div class="plist">${rows.length ? rows.map(w => `
        <button class="row" data-word="${esc(w.l.g)}">
          ${badgeOf(w.eff)}<b>${esc(disp(w.l.te))}</b>
          <span class="g">${esc(glossOf(w.l))}</span>
        </button>`).join('')
        : `<p class="pempty">${panel.tab === 'lingqs'
            ? 'Nothing yet — click a blue word and give it a status (1–4).'
            : 'Nothing here.'}</p>`}
      </div>
      <div class="pmenu">
        <button id="pm-lesson">▤ Review ${
          sentenceScope() ? 'This Sentence' : cur ? 'This Lesson' : 'LingQs'} <span class="n">${
          cur ? lessonPool.length : lessonLingqs.length}</span></button>
        <button id="pm-due">◷ Review Due <span class="n">${dueAll.length}</span></button>
        <button id="pm-vocab">☰ Vocabulary List</button>
      </div>`;

    $$('#panel [data-ptab]').forEach(b => b.addEventListener('click', () => {
      panel.tab = b.dataset.ptab; renderPanel();
    }));
    $$('#panel [data-pscope]').forEach(b => b.addEventListener('click', () => {
      panel.scope = b.dataset.pscope; renderPanel();
    }));
    $$('#panel [data-word]').forEach(b => b.addEventListener('click', () => openWord(b.dataset.word)));
    /* In a lesson this covers everything in the lesson still being learned, not only the
       words already LingQ'd — "scoped to this lesson" is the point, and a lesson's new words
       are exactly the ones worth a second pass. Outside a lesson there is no scope, so it
       falls back to the LingQs it always was. */
    $('#pm-lesson').addEventListener('click', () => startReview(
      (cur ? lessonPool : lessonLingqs).map(w => w.l),
      { scope: sentenceScope() ? `sentence ${svIdx + 1} of ${cur.lines.length}`
               : cur ? (cur.title.en || `lesson ${cur.num}`) : 'your LingQs' }));
    $('#pm-due').addEventListener('click', () => startReview(dueAll, { scope: 'due today' }));
    $('#pm-vocab').addEventListener('click', () => { location.hash = '#/vocab'; });
  }

  /* Find the sentence a word occurs in, preferring the current story. */
  function contextFor(g) {
    const i = BY_G.get(g);
    const pool = cur ? [cur, ...STORIES.filter(s => s !== cur)] : STORIES;
    for (const s of pool) {
      for (const ln of s.lines) {
        if (ln.t.some(t => t[2] === i)) return ln;
      }
    }
    return null;
  }

  function openWord(g, line) {
    panel.mode = 'word'; panel.g = g; panel.line = line || contextFor(g);
    panel.chipSel = 0;
    renderWordCard();
    sheetOpen();
    /* Hearing the word is the point of clicking it, so do not make that a second tap. Silent on
       failure: openWord fires on every word click, and a word with no clip yet would otherwise
       toast on each one. The 🔊 button stays noisy, because there the user asked specifically. */
    sayWord(g, true);
  }
  function closeWord() {
    panel.mode = 'lists'; panel.g = null; panel.line = null;
    renderPanel();
  }

  function statusButtonsHTML(eff) {
    const items = [['1', 'New', '1'], ['2', 'Recognized', '2'], ['3', 'Familiar', '3'],
                   ['4', 'Learned', '4'], ['k', 'Known', 'K'], ['x', 'Ignore', 'X']];
    return items.map(([v, label, key]) =>
      `<button data-set="${v}" class="${eff === v ? 'on' : ''}" title="${label} (${key})">${
        v === 'k' ? '✓' : v === 'x' ? '✗' : v} ${label}</button>`).join('');
  }

  function renderWordCard() {
    const g = panel.g;
    const l = LEX[BY_G.get(g)];
    if (!l) return closeWord();
    const eff = effOf(g);
    const ln = panel.line;
    const meaning = WordLevels.meaning(g);

    /* Candidate meanings, LingQ's "popular meanings" slot filled from this repo's own data. */
    const chips = [];
    /* Registry glosses first: they are hand-written for this word in this corpus, where l.en is
       the master's general gloss and l.p is an automatic split. Most-specific first. */
    (l.sn || []).forEach(sn => { if (sn.g) chips.push(sn.g); });
    if (l.en) chips.push(l.en);
    if (l.head) chips.push(verbEquiv(l) || `${FORMLABEL[l.form] || l.form}: ${l.head[1]}`);
    if (l.p) chips.push(l.p.map(([a, b]) => `${a} (${b})`).join(' + '));
    panel.chips = chips;

    let body = '';
    if (panel.wtab === 'dict') {
      const senses = l.sn || [];
      /* The word registry (ministories/vocab.tsv), rendered above everything else because it is
         the only source written for this word in this sentence. A word can carry several senses;
         sense 1 is the first one met in the corpus and leads. Nothing checks these explanations
         for correctness, so a draft says so rather than implying review it has not had. */
      const senseHTML = senses.length ? `
        <div class="wc-senses">
          ${senses.map((sn, i) => `
            <div class="sense">
              <p style="font-size:15px;margin:6px 0">
                ${senses.length > 1 ? `<span style="color:var(--ink2)">${i + 1}.</span> ` : ''}
                <b>${esc(sn.g)}</b>
                ${sn.p ? ` <small style="color:var(--ink2)">· ${esc(sn.p)}</small>` : ''}
              </p>
              ${sn.x ? `<p style="font-size:14px;line-height:1.55">${esc(sn.x)}</p>` : ''}
              ${sn.s === 'draft' ? `<p style="font-size:12px;color:var(--ink2)">
                Draft — written for this project, not yet checked by a native speaker.</p>` : ''}
            </div>`).join('')}
        </div>` : '';

      body = `
        ${senseHTML}
        ${l.en ? `<p style="font-size:15px;margin:6px 0"><b>${esc(l.en)}</b></p>` : ''}
        ${l.p ? `<p style="font-size:14px">${l.p.map(([a, b]) =>
            `<b class="end">${esc(a)}</b> ${esc(b)}`).join(' &nbsp;+&nbsp; ')}
            <br><small style="color:var(--ink2)">Split automatically — check it reads sensibly.</small></p>` : ''}
        ${l.head ? `${verbEquiv(l)
              ? `<p style="font-size:16px;margin:6px 0">= <b>“${esc(verbEquiv(l))}”</b></p>` : ''}
            <p style="font-size:14px">${esc(FORMLABEL[l.form] || l.form)} of
            <b>${esc(l.head[0])}</b> — ${esc(l.head[1])}</p>` : ''}
        ${l.o ? `<p style="font-size:13px;color:var(--ink2)">Deck position ${nf(l.o)}</p>` : ''}
        ${!l.en && !l.p && !l.head && !senses.length ? `<p style="font-size:14px;color:var(--ink2)">Not in the
            word master — a real find. Save your own meaning above, or ask the dictionaries.</p>` : ''}
        <label style="font:700 11px/1 Inter;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);display:block;margin-top:14px">Web dictionaries</label>
        <div class="dictlinks">
          <a href="https://en.wiktionary.org/wiki/${encodeURIComponent(bareTe(l.te))}" target="_blank" rel="noopener">Wiktionary ↗</a>
          <a href="https://glosbe.com/te/en/${encodeURIComponent(bareTe(l.te))}" target="_blank" rel="noopener">Glosbe Telugu–English ↗</a>
          <a href="https://translate.google.com/?sl=te&tl=en&text=${encodeURIComponent(bareTe(l.te))}" target="_blank" rel="noopener">Google Translate ↗</a>
        </div>`;
    } else if (panel.wtab === 'ai') {
      body = aiTabHTML(l, ln);
    } else {
      body = formsTabHTML(l);
    }

    $('#panelbody').innerHTML = `
      <button class="wc-back" id="wc-back">‹ ${cur ? 'Lesson words' : 'Words'}</button>
      <div class="wc-head">
        <h2 class="${rom === 'te' ? 'te' : ''}">${esc(disp(l.te))}</h2>
        <button class="say" id="wc-say" title="Pronounce">🔊</button>
        ${badgeOf(eff)}
      </div>
      <p class="wc-sub ${rom === 'te' ? '' : 'te'}">${esc(dispAlt(l.te))}${l.r && rom !== 'iso' ? ` · ${esc(l.r)}` : ''}</p>
      <div class="wc-status">${statusButtonsHTML(eff)}</div>
      <div class="wc-meaning">
        <label>Saved meaning</label>
        <textarea id="wc-meaning" placeholder="Type a meaning here">${esc(meaning)}</textarea>
        ${chips.length ? `<div class="chips">${chips.map((c, i) =>
          `<button data-chip="${i}" class="${i === (panel.chipSel || 0) ? 'sel' : ''}">${esc(c)}</button>`).join('')}</div>` : ''}
      </div>
      ${ln ? `<div class="wc-ctx"><div class="te-line">${esc(disp(bareTe(ln.t.map(t => t[0]).join(''))))}</div>${esc(ln.en)}</div>` : ''}
      <div class="subtabs">
        <button data-wtab="dict" class="${panel.wtab === 'dict' ? 'on' : ''}">Dictionary</button>
        <button data-wtab="ai" class="${panel.wtab === 'ai' ? 'on' : ''}">AI</button>
        <button data-wtab="forms" class="${panel.wtab === 'forms' ? 'on' : ''}">Forms</button>
      </div>
      <div id="wc-body">${body}</div>`;

    $('#wc-back').addEventListener('click', closeWord);
    $('#wc-say').addEventListener('click', () => sayWord(g));
    $$('#panel [data-set]').forEach(b => b.addEventListener('click', () => {
      const v = b.dataset.set;
      const clearing = effOf(g) === v;                // clicking the active status clears it
      WordLevels.set(g, clearing ? null : v);
      renderWordCard(); repaintTokens(); renderTop();
      /* On a phone the sheet covers the text, so deciding a word should hand the page back
         rather than needing a second tap to dismiss. Only for Recognized..Known — 'New' and
         'Ignore' leave you looking at the card, and clearing a status means you are still
         choosing. Matches the 900px CSS breakpoint where the panel becomes a bottom sheet. */
      if (!clearing && ['2', '3', '4', 'k'].includes(v) && isPhone()) {
        closeWord(); sheetClose();
      }
    }));
    const ta = $('#wc-meaning');
    let deb = null;
    ta.addEventListener('input', () => {
      clearTimeout(deb);
      deb = setTimeout(() => WordLevels.setMeaning(g, ta.value), 400);
    });
    $$('#panel [data-chip]').forEach(b => b.addEventListener('click', () => {
      WordLevels.setMeaning(g, chips[+b.dataset.chip]);
      renderWordCard();
    }));
    $$('#panel [data-wtab]').forEach(b => b.addEventListener('click', () => {
      panel.wtab = b.dataset.wtab; renderWordCard();
    }));
    wireAiTab(l, ln);
  }

  let wordAudio = null;
  function sayWord(g, silent) {
    if (wordAudio) wordAudio.pause();
    /* Each corpus keeps its own word clips, and the path was hardcoded to the mini stories —
       so every speaker button in the Intensive Course asked ministories for a file it does not
       have. A word guid is a hash of its Telugu, so the SAME word is the same id in both
       corpora: whichever directory holds it, the clip is the right one. Try the corpus in
       front of you first, then the other, before deciding there is no clip. */
    const dirs = (cur && cur.id && cur.id[0] === 'i')
      ? ['../intensive/audio/words', '../ministories/audio/words']
      : ['../ministories/audio/words', '../intensive/audio/words'];
    /* Autoplay policy: this only ever runs inside a click handler, which counts as the user
       gesture browsers require, so playback is allowed. The catch still matters for a missing
       clip or a decode error. */
    const tryDir = i => {
      if (i >= dirs.length) {
        if (!silent) toast('No clip for this word yet.');
        return;
      }
      wordAudio = new Audio(`${dirs[i]}/${g}.mp3`);
      wordAudio.play().catch(() => tryDir(i + 1));
    };
    tryDir(0);
  }

  /* ---------- AI tab ---------- */
  function aiTabHTML(l, ln) {
    if (!AiDict.hasKey()) {
      return `<div class="aikey">
        <p style="font-size:13.5px">On-demand explanations from <b>${esc(AiDict.MODEL)}</b>,
          per word, per sentence, only when you ask. This needs <b>your own API key</b>: it is
          stored only in this browser's localStorage, sent only to api.anthropic.com, and never
          committed anywhere. Reasonable for a single-user tool; do not do this on a shared machine.</p>
        <input type="password" id="ai-key" placeholder="sk-ant-…" autocomplete="off">
        <p style="margin-top:8px"><button class="btn primary" id="ai-savekey">Save key</button></p>
      </div>`;
    }
    const lineG = ln ? ln.g : 'nocx';
    const tabs = ['explain', 'examples', 'grammar'];
    const cached = AiDict.cached(panel.aitab, l.g, lineG);
    return `
      <div class="subtabs">${tabs.map(t =>
        `<button data-aitab="${t}" class="${panel.aitab === t ? 'on' : ''}">${t[0].toUpperCase() + t.slice(1)}</button>`).join('')}</div>
      <div id="ai-out">${cached
        ? `<div class="aiout">${esc(cached)}</div>`
        : `<p><button class="btn primary" id="ai-go">Generate ${panel.aitab}</button></p>`}</div>
      <p class="ainote">Model output, not checked translation — nothing here has been through
        check_ms.py. Cached in this browser after the first ask.
        <button id="ai-forgetkey" style="color:var(--accent)">Remove key</button></p>`;
  }

  function wireAiTab(l, ln) {
    const saveBtn = $('#ai-savekey');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => {
        const v = $('#ai-key').value.trim();
        if (!v) return toast('Paste a key first.');
        AiDict.setKey(v); renderWordCard();
      });
    }
    $$('#panel [data-aitab]').forEach(b => b.addEventListener('click', () => {
      panel.aitab = b.dataset.aitab; renderWordCard();
    }));
    const forget = $('#ai-forgetkey');
    if (forget) forget.addEventListener('click', () => {
      if (confirm('Remove the stored API key from this browser?')) { AiDict.setKey(''); renderWordCard(); }
    });
    const go = $('#ai-go');
    if (go) {
      go.addEventListener('click', async () => {
        const lineG = ln ? ln.g : 'nocx';
        const ctxTe = ln ? bareTe(ln.t.map(t => t[0]).join('')) : bareTe(l.te);
        const out = $('#ai-out');
        out.innerHTML = '<p style="color:var(--ink2);font-size:14px">Asking…</p>';
        try {
          const text = await AiDict.ask(panel.aitab, l.g, lineG, bareTe(l.te), ctxTe, ln ? ln.en : '');
          out.innerHTML = `<div class="aiout">${esc(text)}</div>`;
        } catch (e) {
          out.innerHTML = `<p class="err">${
            e.message === 'no-key' ? 'No key saved.' : esc(e.message)}</p>
            <p><button class="btn" id="ai-go2">Try again</button></p>`;
          const again = $('#ai-go2');
          if (again) again.addEventListener('click', () => { panel.aitab = panel.aitab; renderWordCard(); });
        }
      });
    }
  }

  /* ---------- Forms tab: the Verb Lab's actual paradigm, not a re-derivation ---------- */
  function formsTabHTML(l) {
    /* VERBS/cells are top-level consts in classic scripts — lexical globals, NOT window
       properties. typeof is the only safe existence test. */
    const haveLab = typeof VERBS !== 'undefined' && typeof cells === 'function';
    const v = l.lemma && haveLab ? VERBS.find(x => x.id === l.lemma) : null;
    if (!v) {
      return `<p style="font-size:14px;color:var(--ink2)">${l.form
        ? 'This form\'s verb is not in the Verb Lab\'s 54 roots yet.'
        : 'Not recognized as a Verb Lab conjugation. Forms are shown for words the '
          + 'conjugation engine already generates — nothing is re-derived here.'}</p>
        <div class="dictlinks"><a href="../GRAMMAR_LAB/paradigms.html">Open the paradigm tables ↗</a></div>`;
    }
    const all = cells(v);
    const byForm = new Map();
    all.forEach(c => {
      if (!byForm.has(c.form)) byForm.set(c.form, []);
      byForm.get(c.form).push(c);
    });
    const target = bareTe(l.te);
    const order = [...byForm.keys()].sort((a, b) =>
      (byForm.get(a).some(c => c.tel === target) ? -1 : 0) - (byForm.get(b).some(c => c.tel === target) ? -1 : 0));
    const rows = order.map(f => {
      const cs = byForm.get(f);
      const hit = cs.some(c => c.tel === target);
      return `<tr${hit ? ' style="background:var(--l4)"' : ''}>
        <td>${esc(FORMLABEL[f] || f)}</td>
        <td class="cell">${cs.map(c =>
          `<span style="margin-right:10px;white-space:nowrap${c.tel === target ? ';font-weight:800' : ''}">${
            esc(rom === 'te' ? c.tel : rom === 'coll' ? Colloquial.romanize(c.tel) : c.rom)}</span>`).join('')}</td>
      </tr>`;
    }).join('');
    return `<p style="font-size:14px">Paradigm of <b>${esc(rom === 'te' ? '' : v.id)}</b>
        <span class="te">${esc(v.root[1])}</span> — ${esc(v.gloss)}, from the
        <a href="../GRAMMAR_LAB/paradigms.html">Verb Lab</a>.</p>
      <div style="overflow-x:auto"><table class="formtable">${rows}</table></div>`;
  }

  /* ---------- vocabulary view ---------- */
  function renderVocab() {
    $('#playbar').hidden = true;
    const words = LEX.map((l, i) => ({ i, l, eff: effOf(l.g) }));
    const groups = {
      lingqs: words.filter(w => ['1', '2', '3', '4'].includes(w.eff)),
      new: words.filter(w => w.eff === null),
      known: words.filter(w => w.eff === 'k'),
      all: words,
    };
    let rows = groups[vocab.tab] || words;
    if (vocab.q) {
      const q = vocab.q.toLowerCase();
      rows = rows.filter(w => disp(w.l.te).toLowerCase().includes(q) ||
        (w.l.en || '').toLowerCase().includes(q) || w.l.te.includes(vocab.q));
    }
    rows = [...rows];
    if (vocab.sort === 'alpha') rows.sort((a, b) => disp(a.l.te).localeCompare(disp(b.l.te)));
    else if (vocab.sort === 'freq') rows.sort((a, b) => b.l.n - a.l.n);
    else rows.sort((a, b) => (a.l.f - b.l.f) || (b.l.n - a.l.n));

    $('#pane').innerHTML = `
      <div class="viewhead">
        <h1>Vocabulary</h1><span class="sub">${nf(LEX.length)} distinct words across ${STORIES.length} stories</span>
        <span class="tools">
          <input type="search" id="v-q" placeholder="Search…" value="${esc(vocab.q)}"
            style="border:1px solid var(--line);border-radius:8px;padding:6px 10px;font:inherit;font-size:13.5px">
          <span class="seg">
            <button data-sort="freq" class="${vocab.sort === 'freq' ? 'on' : ''}">Frequency</button>
            <button data-sort="alpha" class="${vocab.sort === 'alpha' ? 'on' : ''}">A–Z</button>
            <button data-sort="first" class="${vocab.sort === 'first' ? 'on' : ''}">First met</button>
          </span>
        </span>
      </div>
      <div class="ptabs">
        <button data-vtab="lingqs" class="${vocab.tab === 'lingqs' ? 'on' : ''}">LingQs (${groups.lingqs.length})</button>
        <button data-vtab="new" class="${vocab.tab === 'new' ? 'on' : ''}">New Words (${groups.new.length})</button>
        <button data-vtab="known" class="${vocab.tab === 'known' ? 'on' : ''}">Known (${groups.known.length})</button>
        <button data-vtab="all" class="${vocab.tab === 'all' ? 'on' : ''}">All Words (${groups.all.length})</button>
      </div>
      <table class="vtable"><tbody>${rows.map(w => `
        <tr data-word="${esc(w.l.g)}">
          <td style="width:24px">${badgeOf(w.eff)}</td>
          <td class="te-col ${rom === 'te' ? 'te' : ''}">${esc(disp(w.l.te))}</td>
          <td class="g-col">${esc(glossOf(w.l))}</td>
          <td class="n-col">×${w.l.n} · story ${w.l.f}</td>
        </tr>`).join('')}</tbody></table>`;

    $$('#pane [data-vtab]').forEach(b => b.addEventListener('click', () => { vocab.tab = b.dataset.vtab; renderVocab(); }));
    $$('#pane [data-sort]').forEach(b => b.addEventListener('click', () => { vocab.sort = b.dataset.sort; renderVocab(); }));
    $('#v-q').addEventListener('input', e => { vocab.q = e.target.value; renderVocab(); $('#v-q').focus(); const v = $('#v-q'); v.setSelectionRange(v.value.length, v.value.length); });
    $$('#pane [data-word]').forEach(tr => tr.addEventListener('click', () => openWord(tr.dataset.word)));
    renderPanelForVocab();
  }
  function renderPanelForVocab() {
    if (panel.mode === 'word' && panel.g) renderWordCard();
    else $('#panelbody').innerHTML = '<p class="pempty">Tap a word to open its card.</p>';
  }

  /* ---------- stats view ---------- */
  function renderStats() {
    $('#playbar').hidden = true;
    document.querySelector('main').classList.remove('withpanel');
    const c = WordLevels.counts();
    const lingqs = c[1] + c[2] + c[3] + c[4];
    const snaps = WordLevels.snapshots();

    $('#pane').innerHTML = `
      <div class="viewhead"><h1>Stats</h1></div>
      <div class="statcards">
        <div class="statcard"><b>${nf(WordLevels.knownTotal())}</b><span>known words, all texts</span></div>
        <div class="statcard"><b>${nf(lingqs)}</b><span>LingQs being learned</span></div>
        <div class="statcard"><b>${WordLevels.activityToday()}/${WordLevels.goal()}</b>
          <span>today · <button id="st-goal" style="color:var(--accent)">change goal</button></span></div>
        <div class="statcard"><b>${WordLevels.streak() || '—'}</b><span>day streak</span></div>
      </div>
      <div class="statcards">
        ${['1', '2', '3', '4', 'k', 'x'].map(l => `<div class="statcard">
          <b>${nf(c[l])}</b><span>${badgeOf(l)} ${WordLevels.LABEL[l]}</span></div>`).join('')}
      </div>
      <div class="chartbox"><h3>Known words over time</h3>${chartHTML(snaps)}</div>`;

    $('#st-goal').addEventListener('click', () => {
      const v = prompt('Daily goal — words acted on per day:', WordLevels.goal());
      if (v) { WordLevels.setGoal(v); renderStats(); renderTop(); }
    });
  }

  function chartHTML(snaps) {
    if (snaps.length < 2) {
      return `<p class="empty">One snapshot per day this page is opened. Come back tomorrow and
        a line starts here — history recording began today, there is nothing to reconstruct
        backwards from.</p>`;
    }
    const W = 640, H = 200, P = 30;
    const vals = snaps.map(([, v]) => v.k);
    const max = Math.max(...vals, 1), min = Math.min(...vals, 0);
    const x = i => P + i * (W - 2 * P) / (snaps.length - 1);
    const y = v => H - P - (v - min) * (H - 2 * P) / Math.max(1, max - min);
    const pts = vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px">
      <polyline points="${pts}" fill="none" stroke="#8fa37e" stroke-width="2.5"/>
      ${vals.map((v, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3" fill="#8fa37e"/>`).join('')}
      <text x="${P}" y="${H - 8}" font-size="11" fill="#b9b3a4">${snaps[0][0]}</text>
      <text x="${W - P}" y="${H - 8}" font-size="11" fill="#b9b3a4" text-anchor="end">${snaps[snaps.length - 1][0]}</text>
      <text x="${P - 4}" y="${y(max) + 4}" font-size="11" fill="#b9b3a4" text-anchor="end">${nf(max)}</text>
      <text x="${P - 4}" y="${y(min) + 4}" font-size="11" fill="#b9b3a4" text-anchor="end">${nf(min)}</text>
    </svg>`;
  }

  /* ---------- review ---------- */

  /* The words of one line, deduplicated and in the order the panel lists them.

     Alphabetical, not reading order, and on the DISPLAYED form — the same rule panelWords()
     already follows, and for the same reason: this list is for finding a word again, and
     reading order means re-reading the sentence to find it. */
  function wordsOfLine(ln) {
    const seen = new Set();
    const out = [];
    for (const [, , i] of (ln.t || [])) {
      if (i < 0 || seen.has(i)) continue;
      seen.add(i);
      out.push(LEX[i]);
    }
    return out.sort((a, b) => disp(a.te).localeCompare(disp(b.te), undefined, { sensitivity: 'base' }));
  }

  /* Known and Ignored are dropped. Reviewing a word you have already retired is the fastest
     way to make a review feel like busywork, and both states exist precisely to say "stop
     showing me this". Everything else — unmarked and levels 1-4 — is still being learned. */
  const stillLearning = l => !['k', 'x'].includes(effOf(l.g));

  function startReview(lexEntries, opts) {
    const list = lexEntries.filter(Boolean);
    if (!list.length) return toast('Nothing to review.');
    reviewState = {
      queue: list.map(w => w.g || (w.l && w.l.g)).filter(Boolean),
      i: 0, revealed: false, scope: (opts && opts.scope) || '',
    };
    renderReview();
  }
  function closeReview() { reviewState = null; $('#overlay-root').innerHTML = ''; }

  function renderReview() {
    const rs = reviewState;
    if (!rs) return;
    if (rs.i >= rs.queue.length) {
      /* The list comes straight after the cards, on the same screen, rather than sending you
         back to the panel to find it. That is the whole point of it: the words are still in
         mind from the sentence you just read, and an alphabetical list of exactly those is
         where the second pass is cheapest. Statuses are live here — rating a word in the list
         is the same action as rating it on a card. */
      const rows = rs.queue.map(g => LEX[BY_G.get(g)]).filter(Boolean)
        .sort((a, b) => disp(a.te).localeCompare(disp(b.te), undefined, { sensitivity: 'base' }));
      $('#overlay-root').innerHTML = `<div class="overlay"><div class="rvcard wide">
        <button class="close" id="rv-close">×</button>
        <p class="rvdone">${rs.queue.length} word${rs.queue.length === 1 ? '' : 's'} reviewed${
          rs.scope ? ' — ' + esc(rs.scope) : ''}</p>
        <div class="rvlist">${rows.map(l => `
          <div class="rvrow" data-g="${esc(l.g)}">
            ${badgeOf(effOf(l.g))}
            <b class="${rom === 'te' ? 'te' : ''}">${esc(disp(l.te))}</b>
            <span class="alt">${esc(dispAlt(l.te))}</span>
            <span class="g">${esc(glossOf(l) || '—')}</span>
          </div>`).join('')}</div>
        <p class="count">Click a word to open it · <kbd>Esc</kbd> to close</p>
      </div></div>`;
      $('#rv-close').addEventListener('click', () => { closeReview(); renderPanel(); renderTop(); });
      $$('#overlay-root .rvrow').forEach(r => r.addEventListener('click', () => {
        closeReview(); openWord(r.dataset.g); renderTop();
      }));
      return;
    }
    const g = rs.queue[rs.i];
    const l = LEX[BY_G.get(g)];
    const eff = effOf(g);
    $('#overlay-root').innerHTML = `<div class="overlay"><div class="rvcard">
      <button class="close" id="rv-close">×</button>
      <p class="count">${rs.i + 1} / ${rs.queue.length}</p>
      <p class="term ${rom === 'te' ? 'te' : ''}">${esc(disp(l.te))}</p>
      <p class="sub ${rom === 'te' ? '' : 'te'}">${esc(dispAlt(l.te))}</p>
      <div class="answer">${rs.revealed
        ? esc(glossOf(l) || '(no meaning saved yet)')
        : '<span class="hint">space / enter to reveal</span>'}</div>
      <div class="wc-status">${statusButtonsHTML(eff)}</div>
      <p class="count"><kbd>1</kbd>–<kbd>4</kbd> rate · <kbd>K</kbd> known · <kbd>X</kbd> ignore · <kbd>Esc</kbd> quit</p>
    </div></div>`;
    $('#rv-close').addEventListener('click', () => { closeReview(); renderPanel(); renderTop(); });
    $$('#overlay-root [data-set]').forEach(b => b.addEventListener('click', () => rateReview(b.dataset.set)));
  }
  function rateReview(v) {
    const rs = reviewState;
    WordLevels.set(rs.queue[rs.i], v);
    rs.i++; rs.revealed = false;
    renderReview(); repaintTokens();
  }

  /* ---------- events ---------- */
  $('#pane').addEventListener('click', e => {
    const cue = e.target.closest('.cue');
    if (cue) { playLine(+cue.dataset.seek); return; }
    const w = e.target.closest('.w');
    if (!w || !cur) return;
    $$('#pane .w.focus').forEach(el => el.classList.remove('focus'));
    w.classList.add('focus');
    const tok = cur.lines[+w.dataset.l].t[+w.dataset.t];
    const g = LEX[tok[2]].g;
    /* LingQ's core move: clicking a blue word creates the LingQ at status 1. Arrow/Tab
       navigation deliberately does not — only the deliberate click/tap commits. */
    if (effOf(g) === null) {
      WordLevels.set(g, '1');
      repaintTokens(); renderTop();
    }
    openWord(g, cur.lines[+w.dataset.l]);
  });

  $$('#romseg button').forEach(b => b.addEventListener('click', () => {
    rom = b.dataset.rom;
    write('rtt.msRom', rom);
    renderTop();
    if (view === 'story') { renderStory(); }
    else if (view === 'vocab') renderVocab();
    else if (view === 'library') renderLibrary();
    renderPanel();
  }));

  /* Tab: jump to the next word not yet decided on — LingQ's core reading shortcut. */
  /* Move to the next word still waiting on a decision, and open it.

     THE CONTAINER IS NOT ALWAYS #readtext. Sentence view renders into .sview, so this used to
     find no spans there and return without moving — rating a word by keyboard in sentence view
     left the focus where it was, which is exactly where you want it to advance.

     In sentence view it walks the sentence in front of you and then steps to the next sentence
     that still has one, so a whole lesson can be cleared without touching the mouse. It does
     not wrap: reaching the end should say so rather than quietly starting again and looking
     like nothing happened. */
  function focusWord(el) {
    $$('#pane .w.focus').forEach(s => s.classList.remove('focus'));
    el.classList.add('focus');
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    const ln = cur.lines[+el.dataset.l];
    openWord(LEX[ln.t[+el.dataset.t][2]].g, ln);
  }

  /* One word to the right, and on to the next sentence at the end of this one.

     RATING IS A CURSOR, NOT A SEARCH. Rating used to call nextBlue, which looks for the next
     word still needing a decision — so re-rating the first word of a sentence whose words were
     all already rated found nothing nearby and leapt several sentences ahead. Correct by its
     own rule and useless in practice: you were revising this sentence, not looking for work.

     Skipping ahead is still available and still wanted — it is Tab / B, which is where a
     search belongs. Two gestures, one each. */
  function nextWord() {
    if (!sview) return nextBlue();
    const spans = $$('.sview .w');
    const at = spans.findIndex(s => s.classList.contains('focus'));
    if (at >= 0 && at + 1 < spans.length) return focusWord(spans[at + 1]);
    if (svIdx + 1 >= cur.lines.length) return toast('End of the lesson.');
    svIdx += 1;
    renderStory(); renderPanel();
    const first = $$('.sview .w')[0];
    if (first) focusWord(first);
  }

  function nextBlue() {
    const spans = $$((sview ? '.sview' : '#readtext') + ' .w');
    const at = spans.findIndex(s => s.classList.contains('focus'));
    for (let i = at + 1; i < spans.length; i++) {
      if (spans[i].classList.contains('new')) return focusWord(spans[i]);
    }
    if (!sview) {
      // The reading view shows the whole lesson, so wrapping is how you catch what you skipped.
      for (let i = 0; i <= at && i < spans.length; i++) {
        if (spans[i].classList.contains('new')) return focusWord(spans[i]);
      }
      return toast('No blue words left in this lesson.');
    }
    for (let j = svIdx + 1; j < cur.lines.length; j++) {
      if (cur.lines[j].t.some(t => t[2] >= 0 && effOf(LEX[t[2]].g) === null)) {
        svIdx = j;
        renderStory(); renderPanel();
        const next = $$('.sview .w').find(el => el.classList.contains('new'));
        if (next) focusWord(next);
        return;
      }
    }
    toast('No blue words left in this lesson.');
  }

  /* Arrows walk the shaded words — anything still carrying a highlight, blue or yellow. */
  function moveShaded(d) {
    const spans = $$('#readtext .w').filter(s =>
      s.classList.contains('new') || /(^| )lvl[1-4]( |$)/.test(s.className));
    if (!spans.length) return;
    const at = spans.findIndex(s => s.classList.contains('focus'));
    const el = spans[(at + d + spans.length) % spans.length];
    $$('#pane .w.focus').forEach(s => s.classList.remove('focus'));
    el.classList.add('focus');
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    const tok = cur.lines[+el.dataset.l].t[+el.dataset.t];
    openWord(LEX[tok[2]].g, cur.lines[+el.dataset.l]);
  }

  function openDict(g) {
    const l = LEX[BY_G.get(g)];
    if (l) window.open('https://en.wiktionary.org/wiki/' + encodeURIComponent(bareTe(l.te)),
                       '_blank', 'noopener');
  }

  /* ---------- text size ---------- */
  let fontPx = read('rtt.msFont', 21);
  const applyFont = () => document.documentElement.style.setProperty('--readsize', fontPx + 'px');
  function bumpFont(d) {
    fontPx = Math.max(15, Math.min(30, fontPx + d));
    write('rtt.msFont', fontPx); applyFont();
  }

  /* ---------- the panel as a bottom sheet on small screens ---------- */
  /* Single source of truth for "is this the bottom-sheet layout", kept in step with the
     max-width: 900px block in reader.css. */
  const isPhone = () => window.matchMedia('(max-width: 900px)').matches;
  const sheetOpen = () => $('#panel').classList.add('open');
  const sheetClose = () => $('#panel').classList.remove('open');
  $('#panel-x').addEventListener('click', () => {
    if (panel.mode === 'word') closeWord();
    sheetClose();
  });

  /* ---------- keyboard help ---------- */
  let helpOpen = false;
  const KEYHELP = [
    ['Reading', [
      ['click / tap', 'blue word → LingQ at status 1, card opens'],
      ['Tab or B', 'next blue word'],
      ['← →', 'previous / next highlighted word'],
      ['Shift + ← →', 'previous / next sentence'],
      ['Space', 'play / pause'], ['A', 'replay this sentence'], ['L', 'loop sentence'],
      ['Shift + T', 'show / hide English'], ['+ −', 'text size'],
    ]],
    ['Word card', [
      ['1 – 4', 'New · Recognized · Familiar · Learned'],
      ['K', 'known'], ['X', 'ignore'], ['0', 'clear'],
      ['S', 'pronounce'], ['A', 'play its sentence'], ['D', 'open dictionary'],
      ['H', 'edit the meaning'], ['↑ ↓ then E', 'pick a suggested meaning'],
      ['Esc', 'close'],
    ]],
    ['Review', [['Space / Enter', 'reveal'], ['1–4 · K · X', 'rate and advance'], ['Esc', 'quit']]],
  ];
  function toggleHelp() {
    helpOpen = !helpOpen;
    if (!helpOpen) { $('#overlay-root').innerHTML = ''; return; }
    $('#overlay-root').innerHTML = `<div class="overlay" id="help-ov"><div class="rvcard help">
      <button class="close" id="help-close">×</button>
      <h3>Keyboard</h3>
      ${KEYHELP.map(([title, rows]) => `<div class="helpgroup"><h4>${title}</h4>
        ${rows.map(([k, what]) => `<div class="helprow"><span class="keys">${
          k.split(' ').map(p => /^(or|then|\/|·|\+|−|-)$/.test(p) ? ` ${p} ` : `<kbd>${p}</kbd>`).join('')
        }</span><span>${what}</span></div>`).join('')}</div>`).join('')}
    </div></div>`;
    $('#help-close').addEventListener('click', toggleHelp);
    $('#help-ov').addEventListener('click', e => { if (e.target.id === 'help-ov') toggleHelp(); });
  }
  $('#kbd-help').addEventListener('click', toggleHelp);

  /* Some environments deliver the space key with an empty e.key; e.code is the reliable one. */
  const isSpace = e => e.key === ' ' || e.code === 'Space';

  document.addEventListener('keydown', e => {
    const t = e.target;
    if (t instanceof Element && t.matches('input, textarea')) {
      if (e.key === 'Escape') t.blur();
      return;
    }
    /* Review overlay swallows everything first. */
    if (reviewState) {
      if (e.key === 'Escape') { closeReview(); renderPanel(); renderTop(); return; }
      if (reviewState.i >= reviewState.queue.length) {
        if (isSpace(e) || e.key === 'Enter') { closeReview(); renderPanel(); renderTop(); e.preventDefault(); }
        return;
      }
      if (isSpace(e) || e.key === 'Enter') { reviewState.revealed = true; renderReview(); e.preventDefault(); return; }
      const map = { 1: '1', 2: '2', 3: '3', 4: '4', k: 'k', x: 'x' };
      const v = map[e.key.toLowerCase()];
      if (v) { rateReview(v); e.preventDefault(); }
      return;
    }

    if (helpOpen) {
      if (e.key === 'Escape' || e.key === '?') { e.preventDefault(); toggleHelp(); }
      return;
    }
    if (e.key === '?') { e.preventDefault(); toggleHelp(); return; }
    if (e.key === '+' || e.key === '=') { e.preventDefault(); bumpFont(1); return; }
    if (e.key === '-') { e.preventDefault(); bumpFont(-1); return; }

    // sview is no longer excluded: nextBlue walks the sentence and rolls to the next one, so
    // Tab is the same "go to the next word that needs a decision" gesture in both views.
    if ((e.key === 'Tab' || e.key.toLowerCase() === 'b') && view === 'story') {
      e.preventDefault(); nextBlue(); return;
    }

    /* A word card is open: the six-level keys and LingQ's card shortcuts act on it. */
    if (panel.mode === 'word' && panel.g) {
      const map = { 1: '1', 2: '2', 3: '3', 4: '4', k: 'k', x: 'x' };
      const v = map[e.key.toLowerCase()];
      if (v) {
        e.preventDefault();
        WordLevels.set(panel.g, v);
        repaintTokens(); renderTop();
        if (view === 'story') nextWord(); else renderWordCard();
        return;
      }
      if (e.key === '0') { e.preventDefault(); WordLevels.set(panel.g, null); repaintTokens(); renderWordCard(); renderTop(); return; }
      if (e.key === 'Escape') { e.preventDefault(); closeWord(); sheetClose(); return; }
      const k = e.key.toLowerCase();
      if (k === 's') { e.preventDefault(); sayWord(panel.g); return; }
      if (k === 'd') { e.preventDefault(); openDict(panel.g); return; }
      if (k === 'h') {
        e.preventDefault();
        if (effOf(panel.g) === null) { WordLevels.set(panel.g, '1'); repaintTokens(); renderTop(); renderWordCard(); }
        const ta = $('#wc-meaning'); if (ta) ta.focus();
        return;
      }
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        if (panel.chips && panel.chips.length) {
          e.preventDefault();
          const n = panel.chips.length;
          panel.chipSel = ((panel.chipSel || 0) + (e.key === 'ArrowDown' ? 1 : -1) + n) % n;
          $$('#panelbody [data-chip]').forEach((b, i) => b.classList.toggle('sel', i === panel.chipSel));
          return;
        }
      }
      if (k === 'e') {
        if (panel.chips && panel.chips.length) {
          e.preventDefault();
          WordLevels.setMeaning(panel.g, panel.chips[panel.chipSel || 0]);
          if (effOf(panel.g) === null) { WordLevels.set(panel.g, '1'); repaintTokens(); renderTop(); }
          renderWordCard();
          openDict(panel.g);
          return;
        }
      }
    }

    if (view === 'story') {
      if (e.key === 'T' && e.shiftKey) {
        e.preventDefault();
        showEn = !showEn; write('rtt.msEn', showEn); renderStory();
        return;
      }
      /* Plain arrows walk shaded words (LingQ); Shift+arrows move through the sentences. */
      if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && !e.shiftKey && !sview) {
        e.preventDefault(); moveShaded(e.key === 'ArrowRight' ? 1 : -1); return;
      }
      if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && sview) {
        e.preventDefault();
        svIdx = Math.max(0, Math.min(cur.lines.length - 1, svIdx + (e.key === 'ArrowRight' ? 1 : -1)));
        renderStory(); return;
      }
      if (e.key.toLowerCase() === 'a' && cur && cur.audio) {
        e.preventDefault();
        const li = panel.line ? cur.lines.indexOf(panel.line) : curLine;
        if (li >= 0 && cur.lines[li].s != null) playLine(li);
        return;
      }
      if (cur && cur.audio) {
        if (isSpace(e)) { e.preventDefault(); $('#pb-play').click(); }
        else if (e.key === 'ArrowLeft' && e.shiftKey) { e.preventDefault(); step(-1); }
        else if (e.key === 'ArrowRight' && e.shiftKey) { e.preventDefault(); step(1); }
        else if (e.key.toLowerCase() === 'l') { e.preventDefault(); $('#pb-loop').click(); }
      }
    }
  });

  /* Cross-tab / cross-page changes: recount, recolour. */
  WordLevels.onChange(() => { renderTop(); repaintTokens(); });
  Progress.onChange(() => { renderTop(); });

  /* ---------- boot ---------- */
  WordLevels.snapshot();          // today's history point, written on every open
  applyFont();
  window.addEventListener('hashchange', router);
  router();
})();
