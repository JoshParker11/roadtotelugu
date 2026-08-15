/* The recombination drill.
 *
 * THE ITEM IS THE TRANSFORMATION, NOT THE SENTENCE.
 * A sentence with a verb has roughly eight safe transformations, and enumerating them as
 * separate cards would be the wrong model twice over: it multiplies a 1,400-sentence corpus
 * into an unreviewable pile, and it trains nothing, because what is actually being learned is
 * the *operation* — "make this negative", "move this to she" — not eight memorised strings.
 * So each sentence is one scheduled item, served with one transformation, and the
 * transformation is chosen by which operation is currently weakest.
 *
 * REVISITS ESCALATE INSTEAD OF REPEATING.
 * Meeting the same sentence six times in the same shape is six times the cost for less than
 * twice the benefit. The Leitner box doubles as a difficulty ladder:
 *
 *     box 0  comprehend  what does this mean?          (day it unlocks)
 *     box 1  produce     say it from the English       (+1)
 *     box 2  cloze       fill the missing verb         (+3)
 *     box 3+ transform   change tense, polarity, person (+7, +16, +35)
 *
 * The gaps are the Verb Lab's, deliberately — one spacing scheme across the project.
 *
 * STATE IS DISPOSABLE, WHICH IS THE POINT.
 * Anki owns the permanent core and nothing here may compete with it. The drill's queue is
 * meant to exceed the available time; sliding an item costs nothing. That is precisely why
 * this cannot live in Anki, where every card is a lifetime commitment.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const nf = n => n.toLocaleString('en-US');

  const K = { state: 'rtt.drill', ops: 'rtt.drillOps', opt: 'rtt.drillOpts' };
  const GAPS = [0, 1, 3, 7, 16, 35];
  const MODES = ['comprehend', 'produce', 'cloze', 'transform'];
  const MODE_INFO = {
    comprehend: { label: 'Comprehend', ask: 'What does this mean?' },
    produce:    { label: 'Produce',    ask: 'Say it in Telugu.' },
    cloze:      { label: 'Cloze',      ask: 'Fill the gap.' },
    transform:  { label: 'Transform',  ask: 'Say it again, changed.' },
  };

  const read = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const today = () => Math.floor(Date.now() / 86400000);

  /* ---------- data ---------- */
  const SF = SENTENCE_DATA.fields;
  const SENTS = SENTENCE_DATA.sentences.map(r => {
    const o = {}; SF.forEach((k, i) => o[k] = r[i]); return o;
  });

  /* study_order -> guid, so a sentence's word requirements can be checked against the
     marked-known set from the study desk. Without this the drill could only ask "has enough
     time passed", never "do I actually know every word in this". */
  const GUID_BY_ORDER = new Map();
  WORD_DATA.words.forEach(r => { if (r[1]) GUID_BY_ORDER.set(r[1], r[0]); });

  /* Analysis is lazy: 1,400 sentences × a token scan is fast, but there is no reason to pay
     for sentences the schedule has not reached. */
  const ANALYSED = new Map();
  function info(s) {
    if (ANALYSED.has(s.guid)) return ANALYSED.get(s.guid);
    const a = Recombine.analyse(s);
    const v = { a, opts: Recombine.options(a), cloze: Recombine.cloze(s, a) };
    ANALYSED.set(s.guid, v);
    return v;
  }

  /* ---------- progress ---------- */
  const getState = () => read(K.state, {});
  const getOps = () => read(K.ops, {});
  const getOpts = () => Object.assign({ len: 40, romanFirst: false }, read(K.opt, {}));
  const setOpts = v => write(K.opt, Object.assign(getOpts(), v));

  function grade(s, item, g) {
    const st = getState();
    const r = st[s.guid] || { box: 0, due: 0, seen: 0, wrong: 0 };
    r.seen++;
    /* A miss drops one rung rather than resetting to zero. The boxes here are a difficulty
       ladder as much as a memory-strength one, and failing to *transform* a sentence is not
       evidence that you no longer understand it — sending it back to "what does this mean?"
       would waste the next three reviews re-proving something that was never in doubt. */
    if (g === 2) r.box = Math.min(r.box + 1, GAPS.length - 1);
    else if (g === 0) { r.box = Math.max(0, r.box - 1); r.wrong++; }
    r.due = today() + GAPS[r.box];
    r.last = today();
    st[s.guid] = r; write(K.state, st);

    /* Operation stats drive which transformation gets served next time. Only transform-mode
       answers say anything about an operation. */
    if (item.mode === 'transform' && item.opt) {
      const ops = getOps();
      const o = ops[item.opt.op] || { seen: 0, wrong: 0 };
      o.seen++; if (g === 0) o.wrong++;
      ops[item.opt.op] = o; write(K.ops, ops);
    }
  }

  /* Laplace-smoothed error rate. Unseen operations score 0.5 and so outrank anything you are
     reliably getting right, which is the behaviour wanted: breadth first, then weakness. */
  function opScore(op) {
    const o = getOps()[op];
    return o ? (o.wrong + 1) / (o.seen + 2) : 0.5;
  }

  function pickOption(opts) {
    let best = null, bestScore = -1;
    for (const o of opts) {
      const sc = opScore(o.op) + Math.random() * 0.08;   // jitter so ties do not fossilise
      if (sc > bestScore) { best = o; bestScore = sc; }
    }
    return best;
  }

  /* ---------- availability ---------- */
  function knownOrders() {
    const known = Progress.getKnown(), set = new Set();
    GUID_BY_ORDER.forEach((guid, order) => { if (known[guid]) set.add(order); });
    return set;
  }

  function available() {
    const n = Progress.introducedCount();
    if (!Progress.isConfigured()) return [];
    const extra = knownOrders();
    return SENTS.filter(s => s.need.every(o => o <= n || extra.has(o)));
  }

  /* ---------- session ---------- */
  let session = [], pos = 0, revealed = false, tally = { got: 0, shaky: 0, missed: 0 };

  function modeFor(s, box) {
    const want = MODES[Math.min(box, MODES.length - 1)];
    const v = info(s);
    /* Downgrade rather than skip. A sentence with no verb can never reach transform, and
       there is no reason to withhold it from review because of that. */
    if (want === 'transform' && !v.opts.length) return v.cloze ? 'cloze' : 'produce';
    if (want === 'cloze' && !v.cloze) return 'produce';
    return want;
  }

  function buildItem(s) {
    const st = getState()[s.guid];
    const box = st ? st.box : 0;
    const mode = modeFor(s, box);
    const v = info(s);
    return { s, box, mode, isNew: !st,
             opt: mode === 'transform' ? pickOption(v.opts) : null,
             cloze: mode === 'cloze' ? v.cloze : null };
  }

  function startSession(mode) {
    const pool = available();
    const st = getState(), d = today();
    const due = [], fresh = [], ahead = [];
    pool.forEach(s => {
      const r = st[s.guid];
      if (!r) fresh.push(s);
      else if (r.due <= d) due.push(s);
      else ahead.push(s);
    });
    [due, fresh, ahead].forEach(shuffle);

    /* Due first, then unseen, then — only when asked for — material that is not yet due.
       "Extra" exists because the stated need is to be able to generate a lot of practice
       whenever there is time, and running out mid-session is the failure mode to avoid. It is
       labelled, so early reviews never masquerade as scheduled ones. */
    const ordered = mode === 'extra' ? [...due, ...fresh, ...ahead] : [...due, ...fresh];
    const len = getOpts().len;
    session = (len ? ordered.slice(0, len) : ordered).map(buildItem);
    pos = 0; revealed = false; tally = { got: 0, shaky: 0, missed: 0 };
    render();
  }

  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /* ---------- rendering ---------- */
  function renderOverview() {
    const configured = Progress.isConfigured();
    const pool = available();
    const st = getState(), d = today();
    let due = 0, fresh = 0, ahead = 0;
    pool.forEach(s => {
      const r = st[s.guid];
      if (!r) fresh++; else if (r.due <= d) due++; else ahead++;
    });

    $('#st-day').innerHTML = configured
      ? `<strong class="amber">Day ${nf(Progress.dayNumber())}</strong><i>${nf(pool.length)} sentences open</i>`
      : `<strong class="amber">—</strong><i>no start date set</i>`;
    $('#st-due').innerHTML = `<strong class="${due ? 'amber' : ''}">${nf(due)}</strong><i>due now</i>`;
    $('#st-new').innerHTML = `<strong>${nf(fresh)}</strong><i>not yet seen</i>`;
    $('#st-ahead').innerHTML = `<strong>${nf(ahead)}</strong><i>ahead of schedule</i>`;

    const total = SENTS.length;
    $('#st-corpus').innerHTML = `<strong>${nf(total)}</strong><i>in the corpus</i>`;

    $('#setup-warn').hidden = configured;
    $('#start-row').hidden = !configured;

    $('#btn-start').textContent = due + fresh ? `Start — ${nf(Math.min(due + fresh, getOpts().len || Infinity))} items` : 'Nothing due';
    $('#btn-start').disabled = !(due + fresh);
    $('#btn-extra').disabled = !pool.length;

    renderOps();
  }

  function renderOps() {
    const ops = getOps();
    const rows = Object.entries(ops)
      .filter(([, o]) => o.seen >= 3)
      .sort((a, b) => (b[1].wrong / b[1].seen) - (a[1].wrong / a[1].seen))
      .slice(0, 8);
    if (!rows.length) {
      $('#ops').innerHTML = `<p class="empty">Nothing yet. After a few transform rounds this ranks the operations you miss most, and the drill starts serving them more often.</p>`;
      return;
    }
    $('#ops').innerHTML = rows.map(([op, o]) => {
      const pct = Math.round(o.wrong / o.seen * 100);
      return `<div class="oprow"><b>${esc(opLabel(op))}</b>
        <span class="bar"><i style="width:${pct}%"></i></span>
        <span class="opnum">${pct}% missed · ${o.seen}</span></div>`;
    }).join('');
  }

  function opLabel(op) {
    if (op.startsWith('person:')) {
      const p = PERSONS.find(x => x.id === op.slice(7));
      return p ? 'to ' + p.en : op;
    }
    const f = FORMS.find(x => x.id === op);
    return f ? f.label : op;
  }

  function render() {
    const inSession = pos < session.length;
    $('#overview').hidden = inSession;
    $('#card').hidden = !inSession;
    $('#done').hidden = !(session.length && !inSession);
    if (!inSession) {
      if (session.length) renderDone();
      renderOverview();
      return;
    }

    const it = session[pos];
    const s = it.s;
    const m = MODE_INFO[it.mode];

    $('#progress').innerHTML = `<i style="width:${pos / session.length * 100}%"></i>`;
    $('#counter').textContent = `${pos + 1} / ${session.length}`;
    $('#modetag').textContent = m.label;
    $('#modetag').className = 'modetag ' + it.mode;
    $('#newtag').hidden = !it.isNew;
    $('#daytag').textContent = `day ${s.day}`;

    let prompt = '', instruction = m.ask;

    if (it.mode === 'comprehend') {
      prompt = `<div class="tel-big">${esc(s.telugu)}</div><div class="rom-big">${esc(s.roman)}</div>`;
    } else if (it.mode === 'produce') {
      prompt = `<div class="en-big">${esc(s.english)}</div>`;
    } else if (it.mode === 'cloze') {
      prompt = `<div class="tel-big">${esc(it.cloze.tel)}</div><div class="rom-big">${esc(it.cloze.rom)}</div>
                <div class="en-small">${esc(s.english)}</div>`;
    } else {
      const o = it.opt;
      const tag = o.label ? `<b class="oplabel">${esc(o.label)}</b>` : '';
      instruction = `Change it: ${tag}<span class="opcue">${esc(o.cue)}</span>`;
      prompt = `<div class="tel-big">${esc(s.telugu)}</div><div class="rom-big">${esc(s.roman)}</div>
                <div class="en-small">${esc(s.english)}</div>`;
    }

    $('#instruction').innerHTML = instruction;
    $('#prompt').innerHTML = prompt;
    $('#answer').innerHTML = revealed ? answerHTML(it) : '';
    $('#answer').hidden = !revealed;
    $('#btn-reveal').hidden = revealed;
    $('#grades').hidden = !revealed;
  }

  function answerHTML(it) {
    const s = it.s;
    if (it.mode === 'comprehend') {
      return `<div class="en-big">${esc(s.english)}</div>`;
    }
    if (it.mode === 'produce') {
      return `<div class="tel-big">${esc(s.telugu)}</div><div class="rom-big">${esc(s.roman)}</div>`;
    }
    if (it.mode === 'cloze') {
      /* The missing word large, then the sentence whole again — seeing the gap filled in
         context is most of what makes cloze worth more than a flashcard. */
      return `<div class="tel-big">${esc(it.cloze.answerTel)}</div>
              <div class="rom-big">${esc(it.cloze.answerRom)}</div>
              <p class="whole"><span class="telugu">${esc(s.telugu)}</span><span>${esc(s.roman)}</span></p>`;
    }
    const o = it.opt;
    const v = info(s).a;
    const check = v && v.check
      ? `<p class="gen warn">This verb's stems are unconfirmed — see the Verb Lab's review page.</p>` : '';
    return `<div class="tel-big">${esc(o.tel)}</div><div class="rom-big">${esc(o.rom)}</div>
      <p class="gen">Source sentence with the verb swapped for another cell of the same verb,
      from the Verb Lab's engine. The sentence is from a source; this particular form of it is
      generated.</p>${check}`;
  }

  function renderDone() {
    const n = tally.got + tally.shaky + tally.missed;
    $('#done-body').innerHTML = `
      <h2>${n} item${n === 1 ? '' : 's'} done</h2>
      <div class="tally">
        <span class="t-got">${tally.got} got it</span>
        <span class="t-shaky">${tally.shaky} shaky</span>
        <span class="t-missed">${tally.missed} missed</span>
      </div>
      <p class="sub">Everything you graded is rescheduled. Nothing here is a commitment — an item
      that slides costs nothing, which is why the queue is allowed to be bigger than the time.</p>`;
  }

  /* ---------- events ---------- */
  function reveal() {
    if (pos >= session.length || revealed) return;
    revealed = true; render();
  }

  function doGrade(g) {
    if (!revealed || pos >= session.length) return;
    const it = session[pos];
    grade(it.s, it, g);
    tally[g === 2 ? 'got' : g === 1 ? 'shaky' : 'missed']++;
    pos++; revealed = false;
    render();
  }

  $('#btn-reveal').addEventListener('click', reveal);
  $('#grades').addEventListener('click', e => {
    const b = e.target.closest('button[data-g]');
    if (b) doGrade(+b.dataset.g);
  });
  $('#btn-start').addEventListener('click', () => startSession('normal'));
  $('#btn-extra').addEventListener('click', () => startSession('extra'));
  $('#btn-again').addEventListener('click', () => { session = []; render(); });
  /* Ending a session you graded nothing in should not show a "0 items done" summary. */
  $('#btn-quit').addEventListener('click', () => {
    const any = tally.got + tally.shaky + tally.missed;
    if (any) pos = session.length; else session = [];
    render();
  });

  $('#lens').addEventListener('click', e => {
    const b = e.target.closest('button[data-len]');
    if (!b) return;
    setOpts({ len: +b.dataset.len });
    $('#lens').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
    renderOverview();
  });

  document.addEventListener('keydown', e => {
    /* e.target is not always an Element — a programmatically dispatched event targets
       `document`, which has no .matches, and the throw takes the whole handler with it. */
    const t = e.target;
    if (t instanceof Element && t.matches('input, textarea, select')) return;
    if ($('#card').hidden) return;
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); revealed ? doGrade(2) : reveal(); }
    else if (e.key === '1') doGrade(0);
    else if (e.key === '2') doGrade(1);
    else if (e.key === '3') doGrade(2);
  });

  $('#btn-reset').addEventListener('click', () => {
    if (!confirm('Clear all drill scheduling in this browser? Your word marks and start date are not affected.')) return;
    localStorage.removeItem(K.state); localStorage.removeItem(K.ops);
    session = []; render();
  });

  /* ---------- boot ---------- */
  $('#generated').textContent = SENTENCE_DATA.generated;
  const len = getOpts().len;
  $('#lens').querySelectorAll('button').forEach(b => b.classList.toggle('on', +b.dataset.len === len));
  render();
})();
