/* The six-level word scale, LingQ's model on this project's identity scheme.
 *
 *   (unmarked)   "new" — blue. Not a stored state; absence is the state.
 *   1 New        just LingQ'd — darkest yellow
 *   2 Recognized
 *   3 Familiar
 *   4 Learned    lightest yellow
 *   k Known      no highlight
 *   x Ignored    no highlight, permanently silent (names, numbers)
 *
 * This deliberately does NOT reuse progress.js's four states (known/hard/seen/queued) as the
 * scale — they are a different model (see READER_BRIEF §4). What IS shared is the identity and
 * one state: every word is keyed by the same guid scheme (hash of Telugu script, tools/ids.py),
 * and `k` mirrors into Progress's rtt.known both ways. Mark a word known here and the old
 * reader, the vocabulary queue and the drill all see it; mark it known there and, absent an
 * explicit level here, it reads as known here. Levels 1–4 and `x` stay reader-local, the same
 * boundary the old reader drew for "learning" — they would muddy the deck's meaning.
 *
 * Same persistence pattern as progress.js on purpose: localStorage, read-through cache,
 * cross-tab sync via the storage event.
 *
 * HISTORY IS NEW. progress.js keeps only current state; a growth chart needs time. One
 * snapshot per day the tool is opened (rtt.msSnap), written on boot and after every change,
 * keyed by date — so the chart is real observed history, not a reconstruction.
 */
const WordLevels = (() => {
  const K = { lvl: 'rtt.msLevel', snap: 'rtt.msSnap', act: 'rtt.msAct',
              meaning: 'rtt.msMeaning', read: 'rtt.msRead', goal: 'rtt.msGoal' };
  const LEVELS = ['1', '2', '3', '4', 'k', 'x'];
  const LABEL = { 1: 'New', 2: 'Recognized', 3: 'Familiar', 4: 'Learned',
                  k: 'Known', x: 'Ignored', new: 'New word' };
  /* Due intervals per level, in days — LingQ's own SRS ladder. */
  const SRS = { 1: 1, 2: 3, 3: 7, 4: 15 };

  const cache = {};
  const read = k => {
    if (k in cache) return cache[k];
    try { cache[k] = JSON.parse(localStorage.getItem(k)) ?? {}; } catch { cache[k] = {}; }
    if (typeof cache[k] !== 'object' || cache[k] === null || Array.isArray(cache[k])) cache[k] = {};
    return cache[k];
  };
  const write = (k, v) => { cache[k] = v; try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const invalidate = () => Object.keys(cache).forEach(k => delete cache[k]);

  const listeners = [];
  const onChange = fn => listeners.push(fn);
  const fire = () => listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });

  const today = () => Progress.todayISO();

  /* ---- levels ---- */
  const valid = l => LEVELS.includes(String(l));
  /* Entries are [level, dateISO]. Anything malformed reads as unmarked rather than crashing
     the page — store corruption should cost a mark, not the reader. */
  const entry = g => {
    const e = read(K.lvl)[g];
    return Array.isArray(e) && valid(e[0]) ? e : null;
  };
  const level = g => { const e = entry(g); return e ? String(e[0]) : null; };

  /* Explicit decision wins; otherwise the shared known store decides; otherwise blue. */
  function effective(g) {
    const l = level(g);
    if (l) return l;
    return Progress.isKnown(g) ? 'k' : null;
  }

  function set(g, l) {
    if (l !== null && !valid(l)) return;
    const m = read(K.lvl);
    if (l === null) delete m[g]; else m[g] = [String(l), today()];
    write(K.lvl, m);
    /* Only `known` crosses into the shared store — same rule the old reader applies. */
    Progress.setKnown(g, l === 'k');
    bumpActivity(1);
    snapshot();
    fire();
  }

  function setMany(guids, l) {
    if (l !== null && !valid(l)) return;
    const m = read(K.lvl), d = today();
    guids.forEach(g => { if (l === null) delete m[g]; else m[g] = [String(l), d]; });
    write(K.lvl, m);
    Progress.markMany(guids, 'known', l === 'k');
    bumpActivity(guids.length);
    snapshot();
    fire();
  }

  /* ---- SRS ---- */
  function isDue(g) {
    const e = entry(g);
    if (!e || !SRS[e[0]]) return false;                 // only 1–4 come due
    const marked = Progress.parseISO(e[1]);
    if (!marked) return true;                           // dateless mark: treat as due, not never
    return (new Date() - marked) / 86400000 >= SRS[e[0]];
  }

  /* ---- meanings (the user's own saved gloss, LingQ's "saved meaning") ---- */
  const meaning = g => read(K.meaning)[g] || '';
  function setMeaning(g, text) {
    const m = read(K.meaning);
    if (text && text.trim()) m[g] = text.trim(); else delete m[g];
    write(K.meaning, m);
  }

  /* ---- lessons read ---- */
  const isRead = num => !!read(K.read)[num];
  function setRead(num, on) {
    const m = read(K.read);
    if (on) m[num] = today(); else delete m[num];
    write(K.read, m); fire();
  }

  /* ---- daily activity, goal ring, streak ---- */
  function bumpActivity(n) {
    const a = read(K.act), d = today();
    a[d] = (typeof a[d] === 'number' ? a[d] : 0) + n;
    write(K.act, a);
  }
  const activityToday = () => { const v = read(K.act)[today()]; return typeof v === 'number' ? v : 0; };
  const goal = () => { const v = read(K.goal).target; return Number.isInteger(v) && v > 0 ? v : 50; };
  const setGoal = t => { write(K.goal, { target: Math.max(1, parseInt(t, 10) || 50) }); fire(); };

  function streak() {
    const a = read(K.act);
    let n = 0;
    const d = new Date();
    if (!a[Progress.toISO(d)]) d.setDate(d.getDate() - 1);   // today not started yet ≠ broken
    while (a[Progress.toISO(d)] > 0) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }

  /* ---- counts and history ---- */
  const knownTotal = () => Object.keys(Progress.getKnown()).length;

  function counts() {
    const c = { 1: 0, 2: 0, 3: 0, 4: 0, k: 0, x: 0 };
    const m = read(K.lvl);
    Object.keys(m).forEach(g => { const e = entry(g); if (e) c[e[0]]++; });
    /* Words known only via the shared store (marked elsewhere, never touched here). */
    Object.keys(Progress.getKnown()).forEach(g => { if (!level(g)) c.k++; });
    return c;
  }

  function snapshot() {
    const s = read(K.snap), c = counts();
    s[today()] = { k: c.k, l: c[1] + c[2] + c[3] + c[4] };   // latest write of the day wins
    write(K.snap, s);
  }
  const snapshots = () =>
    Object.entries(read(K.snap))
      .filter(([d, v]) => Progress.parseISO(d) && v && typeof v.k === 'number')
      .sort((a, b) => a[0] < b[0] ? -1 : 1);

  window.addEventListener('storage', e => {
    if (e.key && e.key.startsWith('rtt.')) { invalidate(); fire(); }
  });

  return { LEVELS, LABEL, SRS, level, effective, set, setMany, isDue,
           meaning, setMeaning, isRead, setRead,
           activityToday, goal, setGoal, streak,
           knownTotal, counts, snapshot, snapshots, onChange };
})();
