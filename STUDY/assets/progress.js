/* Where "how far along am I" lives.
 *
 * Two kinds of state, and the distinction is the whole design:
 *
 *   DERIVED — which words you have been *introduced to*. Not stored per word. It is a start
 *   date and a rate, and everything else follows, because the word master is already an
 *   ordered curriculum: word 312 is day 21 whether or not anybody records that. Storing 2,103
 *   booleans to represent one date would be a database that can disagree with itself.
 *
 *   MARKED — which words you actually *know*, and which ones fight back. This cannot be
 *   derived from anything; it is a judgement, so it is stored, one entry per marked word.
 *
 * Keyed by guid, which is a hash of the Telugu script (tools/ids.py) rather than a row
 * number. That is what lets this state survive a rebuild: re-run the pipeline, re-export,
 * re-import, and every mark still points at the word it was made about.
 *
 * localStorage is per-browser, so phone and laptop keep separate marks — the same caveat the
 * Verb Lab carries. exportState/importState is the bridge, and the backup.
 *
 * Loaded by any page that needs progress; it has no dependencies and touches no DOM.
 */

const Progress = (() => {
  const K = { setup: 'rtt.setup', known: 'rtt.known', hard: 'rtt.hard' };
  const DEFAULTS = { start: '', rate: 15, skip: 0 };

  /* Read through a cache. Without it every isKnown() is a JSON.parse of the whole marks
     object, and painting 2,200 rows turns into thousands of parses of a growing blob — the
     page gets slower the more progress you make, which is precisely backwards. */
  const cache = {};
  const read = (k, d) => {
    if (k in cache) return cache[k];
    try { cache[k] = JSON.parse(localStorage.getItem(k)) ?? d; } catch { cache[k] = d; }
    return cache[k];
  };
  const write = (k, v) => {
    cache[k] = v;
    try { localStorage.setItem(k, JSON.stringify(v)); } catch {}
  };
  const invalidate = () => Object.keys(cache).forEach(k => delete cache[k]);

  const listeners = [];
  const onChange = fn => listeners.push(fn);
  const fire = () => listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });

  /* ---- dates ----
   * new Date('2026-08-11') parses as UTC midnight, which reads as the 10th anywhere west of
   * Greenwich and quietly shifts every day number by one. Parse the parts by hand. */
  function parseISO(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((s || '').trim());
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }
  const midnight = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const toISO = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const todayISO = () => toISO(new Date());

  /* ---- setup ---- */
  const getSetup = () => Object.assign({}, DEFAULTS, read(K.setup, {}));
  function setSetup(patch) {
    const s = Object.assign(getSetup(), patch);
    s.rate = Math.max(1, parseInt(s.rate, 10) || DEFAULTS.rate);
    s.skip = Math.max(0, parseInt(s.skip, 10) || 0);
    write(K.setup, s); fire(); return s;
  }
  const isConfigured = () => !!parseISO(getSetup().start);

  /* Day 1 is the start date itself. `skip` subtracts days you did not do any new cards on —
   * the calendar keeps moving whether or not you opened Anki, and without this the page would
   * confidently claim you had met words you have never seen. */
  function dayNumber() {
    const s = getSetup(), start = parseISO(s.start);
    if (!start) return 0;
    const elapsed = Math.floor((midnight(new Date()) - start) / 86400000);
    return Math.max(0, elapsed + 1 - s.skip);
  }

  /* How many words the schedule says you have met. Capped nowhere on purpose: past the end of
   * the list it simply exceeds the word count, and callers clamp. */
  const introducedCount = () => dayNumber() * getSetup().rate;
  const dayOfOrder = order => order ? Math.ceil(order / getSetup().rate) : 0;
  const dateOfDay = d => {
    const start = parseISO(getSetup().start);
    if (!start || !d) return null;
    return new Date(start.getTime() + (d - 1 + getSetup().skip) * 86400000);
  };

  /* ---- marks ---- */
  const getKnown = () => read(K.known, {});
  const getHard = () => read(K.hard, {});
  const isKnown = g => !!getKnown()[g];
  const isHard = g => !!getHard()[g];

  function mark(bucket, guid, on) {
    const k = bucket === 'known' ? K.known : K.hard;
    const m = read(k, {});
    if (on) m[guid] = todayISO(); else delete m[guid];
    write(k, m);
    /* known and hard are mutually exclusive: a word you have decided you know is not also on
       the trouble list, and leaving both set makes every downstream count ambiguous. */
    if (on) {
      const other = bucket === 'known' ? K.hard : K.known;
      const o = read(other, {});
      if (o[guid]) { delete o[guid]; write(other, o); }
    }
    fire();
  }
  const setKnown = (g, on) => mark('known', g, on);
  const setHard = (g, on) => mark('hard', g, on);
  const toggleKnown = g => setKnown(g, !isKnown(g));
  const toggleHard = g => setHard(g, !isHard(g));

  /* Bulk marking, one write and one repaint instead of fifteen of each. */
  function markMany(guids, bucket, on) {
    const k = bucket === 'known' ? K.known : K.hard;
    const other = bucket === 'known' ? K.hard : K.known;
    const m = read(k, {}), o = read(other, {}), stamp = todayISO();
    guids.forEach(g => { if (on) { m[g] = stamp; delete o[g]; } else delete m[g]; });
    write(k, m); if (on) write(other, o);
    fire();
  }

  /* ---- state of one word ----
   * `held` are the rows sequence.py excludes from the deck — bound suffixes, words with no
   * script yet. They have no order and no day, and calling them "upcoming" would be a lie. */
  function stateOf(w) {
    if (isKnown(w.guid)) return 'known';
    if (!w.order) return 'held';
    if (isHard(w.guid)) return 'hard';
    return w.order <= introducedCount() ? 'seen' : 'queued';
  }

  function summary(words) {
    const n = introducedCount(), known = getKnown(), hard = getHard();
    let seen = 0, k = 0, kAhead = 0, h = 0;
    words.forEach(w => {
      const met = w.order && w.order <= n;
      if (met) seen++;
      if (known[w.guid]) { k++; if (!met) kAhead++; }
      else if (hard[w.guid]) h++;
    });
    return { day: dayNumber(), introduced: seen, known: k, knownAhead: kAhead, hard: h,
             total: words.length };
  }

  /* ---- portability ----
   * The export is also what a future tool reads: guid -> date marked is exactly the shape
   * sequence.py or the drill would want, so nothing has to be reshaped later. */
  function exportState() {
    return JSON.stringify({ kind: 'roadtotelugu.progress', version: 1,
                            exported: todayISO(), setup: getSetup(),
                            known: getKnown(), hard: getHard() }, null, 2);
  }

  function importState(text, { merge = true } = {}) {
    const d = JSON.parse(text);
    if (d.kind !== 'roadtotelugu.progress') throw new Error('Not a progress export.');
    if (d.setup) write(K.setup, Object.assign({}, DEFAULTS, d.setup));
    write(K.known, merge ? Object.assign(getKnown(), d.known || {}) : (d.known || {}));
    write(K.hard, merge ? Object.assign(getHard(), d.hard || {}) : (d.hard || {}));
    fire();
    return { known: Object.keys(d.known || {}).length, hard: Object.keys(d.hard || {}).length };
  }

  function reset() {
    Object.values(K).forEach(k => localStorage.removeItem(k));
    invalidate(); fire();
  }

  /* Another tab moved something. The cache is now stale by definition, so drop it before
     telling anyone to repaint. */
  window.addEventListener('storage', e => {
    if (e.key && e.key.startsWith('rtt.')) { invalidate(); fire(); }
  });

  return { getSetup, setSetup, isConfigured, dayNumber, introducedCount, dayOfOrder, dateOfDay,
           getKnown, getHard, isKnown, isHard, setKnown, setHard, toggleKnown, toggleHard,
           markMany, stateOf, summary, exportState, importState, reset, onChange,
           todayISO, toISO, parseISO };
})();
