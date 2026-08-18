/* Repeated-chunk mining: the phrases a text says over and over, and the frames it says them in.
 *
 * WHY THIS IS NOT JUST N-GRAM COUNTING
 * Raw n-grams are unreadable. If "నాకు తెలుగు అంటే ఇష్టం" occurs five times then so does every
 * fragment inside it, so a frequency-sorted list buries the one useful entry under a dozen
 * shadows of itself. Two things fix that, and they are the whole of this file:
 *
 *   1. MAXIMALITY. Keep a chunk only if no longer chunk containing it occurs nearly as often.
 *      A fragment that never appears outside its parent is not a phrase, it is a substring.
 *
 *   2. FRAMES. Abstract one position and count what fills it. "నాకు ___ కావాలి" with nine
 *      different fillers is worth more than any one of those nine sentences, because it is a
 *      generator rather than a thing to memorise.
 *
 * THE DISTINCTION THAT NEEDED THE VERB LAB
 * Two frames look identical to a counter and are not remotely the same discovery:
 *
 *      నాకు ___ కావాలి       fillers: నీళ్ళు, కాఫీ, టైం      — lexical. A card.
 *      నేను ___              fillers: వెళ్తాను, వెళ్ళాను       — inflectional. A conjugation,
 *                                                              already drillable in the Lab.
 *
 * Telling them apart needs to know those two fillers are one verb, which is what STEM_DATA is
 * for. Without it the frame list is half noise and the noise is indistinguishable.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO
 * No baseline comparison, no distinctiveness score. The master is 2,103 words — far too small
 * to say whether a chunk is over-represented, and a score computed off it would be noise
 * wearing a number. The master is used only for what it *can* answer honestly: how many words
 * in this chunk are ones you already have.
 */
const Chunks = (() => {
  const MIN_N = 2, MAX_N = 6;
  /* A chunk is absorbed if an extension of it occurs at least this share of the time. Below 1.0
     because near-total absorption is still absorption: a fragment appearing 10 times whose
     parent appears 9 is a substring with one stray hit, not two phrases. */
  const ABSORB = 0.8;
  /* The slot marker. NUL, because tokenizing strips it out of any real text, so no chunk can
     ever contain it by accident and collide with a frame key. */
  const SLOT = '\u0000';

  /* ---------- stems ---------- */
  let stemOf = null;
  function stem(tok) {
    if (!stemOf) {
      stemOf = new Map();
      if (typeof STEM_DATA !== 'undefined') {
        for (const [form, i] of Object.entries(STEM_DATA.forms)) stemOf.set(form, STEM_DATA.roots[i]);
      }
    }
    return stemOf.get(tok) || null;
  }

  /* ---------- segmentation ---------- */
  /* Transcript lines are the unit. A chunk must never span a line, or the miner "discovers"
     phrases made of one speaker's last word and the next speaker's first. Sentence punctuation
     splits further, since a pasted transcript line often holds several utterances. */
  function segment(text) {
    const out = [];
    for (const line of String(text).split(/\r?\n/)) {
      for (const part of line.split(/[.!?।]+/)) {
        const toks = Lex.tokens(part)
          .map(t => t.trim())
          .filter(t => t && !/^[\s\p{P}\p{S}]+$/u.test(t) && !/^\d+$/.test(t));
        if (toks.length >= MIN_N) out.push(toks);
      }
    }
    return out;
  }

  /* ---------- n-gram counting ---------- */
  /* Counts up to MAX_N + 1: the extra order is never reported, it exists only so that
     MAX_N-grams can be tested for absorption like every other length. */
  function count(lines) {
    const grams = new Map();
    lines.forEach((toks, li) => {
      for (let n = MIN_N; n <= MAX_N + 1; n++) {
        for (let i = 0; i + n <= toks.length; i++) {
          const slice = toks.slice(i, i + n);
          const key = slice.join(' ');
          let e = grams.get(key);
          if (!e) { e = { toks: slice, n: 0, lines: new Set() }; grams.set(key, e); }
          e.n++; e.lines.add(li);
        }
      }
    });
    return grams;
  }

  /* For every chunk, the count of the most frequent chunk that contains it. Computed by walking
     each (n+1)-gram once and crediting its two n-token faces, which is O(total) — searching for
     extensions per chunk instead would be quadratic. */
  function extensions(grams) {
    const best = new Map();
    for (const e of grams.values()) {
      if (e.toks.length <= MIN_N) continue;
      const prefix = e.toks.slice(0, -1).join(' ');
      const suffix = e.toks.slice(1).join(' ');
      if ((best.get(prefix) || 0) < e.n) best.set(prefix, e.n);
      if ((best.get(suffix) || 0) < e.n) best.set(suffix, e.n);
    }
    return best;
  }

  /* ---------- frames ---------- */
  /* One slot, abstracted. Built from raw n-grams rather than from surviving chunks: a frame's
     whole point is that its instances differ, so the instances are often individually too rare
     to survive maximality on their own. */
  function frames(grams, minFillers) {
    const pats = new Map();
    for (const e of grams.values()) {
      const n = e.toks.length;
      if (n < 3 || n > MAX_N) continue;          /* a 2-token frame is one word and a hole */
      for (let s = 0; s < n; s++) {
        const pat = e.toks.slice();
        const filler = pat[s];
        pat[s] = SLOT;
        const key = pat.join(' ');
        let p = pats.get(key);
        if (!p) { p = { toks: pat, slot: s, n: 0, fillers: new Map(), lines: new Set() }; pats.set(key, p); }
        p.n += e.n;
        p.fillers.set(filler, (p.fillers.get(filler) || 0) + e.n);
        e.lines.forEach(l => p.lines.add(l));
      }
    }

    /* The same absorption rule, applied to patterns — but an extension only counts if the slot
       survives it. Trimming a frame's first token drops the slot when the slot *is* the first
       token, and what is left is a different pattern rather than a shorter version of this one. */
    const best = new Map();
    for (const p of pats.values()) {
      if (p.toks.length <= 3) continue;
      const pre = p.toks.slice(0, -1), suf = p.toks.slice(1);
      if (pre.indexOf(SLOT) >= 0) { const k = pre.join(' '); if ((best.get(k) || 0) < p.n) best.set(k, p.n); }
      if (suf.indexOf(SLOT) >= 0) { const k = suf.join(' '); if ((best.get(k) || 0) < p.n) best.set(k, p.n); }
    }

    const out = [];
    for (const [key, p] of pats) {
      if (p.fillers.size < minFillers) continue;
      if ((best.get(key) || 0) >= p.n * ABSORB) continue;

      /* Does the slot vary by word, or by verb form? If two or more fillers share a verb root
         this is a conjugation the Verb Lab already drills, not a phrase worth a card. */
      const roots = new Map();
      let stemmed = 0;
      for (const f of p.fillers.keys()) {
        const r = stem(f);
        if (r) { stemmed++; roots.set(r, (roots.get(r) || 0) + 1); }
      }
      const topRoot = [...roots.entries()].sort((a, b) => b[1] - a[1])[0];
      const inflectional = !!topRoot && topRoot[1] >= 2;

      out.push({
        key, toks: p.toks, slot: p.slot, n: p.n, lines: p.lines.size,
        fillers: [...p.fillers.entries()].sort((a, b) => b[1] - a[1]),
        kind: inflectional ? 'inflection' : 'lexical',
        root: inflectional ? topRoot[0] : '',
        stemmed,
      });
    }
    /* Distinct fillers first: a frame with nine fillers is a generator, one with two is a
       coincidence that happened twice, and total occurrences cannot tell them apart. */
    out.sort((a, b) => b.fillers.length - a.fillers.length || b.n - a.n);
    return out;
  }

  /* ---------- what you already know ---------- */
  /* The only honest thing the master can say about a chunk. Not "is this distinctive" — the
     corpus is nowhere near big enough for that — but "could you learn this today". */
  function annotate(toks) {
    const known = Progress.getKnown();
    const upto = Progress.isConfigured() ? Progress.introducedCount() : 0;
    let inDeck = 0, isKnown = 0, fresh = 0;
    for (const t of toks) {
      if (t === SLOT) continue;
      const w = Lex.lookup(t) || (stem(t) ? Lex.lookup(stem(t)) : null);
      if (!w) { fresh++; continue; }
      inDeck++;
      if ((w.guid && known[w.guid]) || (w.order && w.order <= upto)) isKnown++;
    }
    return { inDeck, known: isKnown, fresh, learnable: fresh === 0 };
  }

  const roman = toks => toks.map(t => t === SLOT ? '___'
    : (Lex.isTelugu(t) ? Te2Rom.romanize(t) : t)).join(' ');

  /* ---------- entry point ---------- */
  function mine(text, opts) {
    const o = Object.assign({ minCount: 2, minFillers: 3 }, opts || {});
    const lines = segment(text);
    const grams = count(lines);
    const ext = extensions(grams);

    const fixed = [];
    for (const [key, e] of grams) {
      if (e.toks.length > MAX_N) continue;       /* the extra order was scaffolding only */
      if (e.n < o.minCount) continue;
      if ((ext.get(key) || 0) >= e.n * ABSORB) continue;
      fixed.push({
        key, toks: e.toks, n: e.n, lines: e.lines.size,
        roman: roman(e.toks), words: annotate(e.toks),
      });
    }
    /* Line count first: five occurrences spread over five lines is a phrase the speaker
       reaches for; five inside one line is a stutter or a chorus. */
    fixed.sort((a, b) => b.lines - a.lines || b.n - a.n || b.toks.length - a.toks.length);

    const fr = frames(grams, o.minFillers).map(f => Object.assign(f, {
      roman: roman(f.toks), words: annotate(f.toks),
    }));

    return {
      lineCount: lines.length,
      tokenCount: lines.reduce((s, l) => s + l.length, 0),
      fixed, frames: fr, SLOT,
    };
  }

  return { mine, SLOT, stem, roman };
})();
