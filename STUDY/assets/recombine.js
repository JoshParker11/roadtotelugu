/* Turning a verified sentence into exercises.
 *
 * The standing constraint is that no novel Telugu gets generated. What happens here is the
 * permitted case: a sentence that came from a source, with one verb swapped for another cell
 * of the *same verb* produced by the audited conjugation engine. Nothing is invented — the
 * sentence is real and the replacement form is one the Verb Lab already drills and already
 * shows in its paradigm tables.
 *
 * Requires verbs.js and engine.js to be loaded first. Nothing is precomputed offline, so a
 * correction to a stem in verbs.js reaches the drill on the next page load.
 */

const Recombine = (() => {

  /* ---- which paradigms are safe to transform *into* ----
   *
   * Not the whole FORMS list, and the exclusions are all grammatical rather than arbitrary:
   *
   *   wantTo / dontWant  take a DATIVE subject — nāku chēyālani undi, never nēnu. Swapping
   *                      the verb alone would leave the sentence ungrammatical.
   *   impFam / impPol    imperatives address someone; they delete the subject entirely.
   *   prohibFam/Pol      same.
   *   hort               "let's" — same problem, plus it forces a first-person-plural reading.
   *   purpose            "in order to" is a subordinate clause; it needs a main clause to
   *                      attach to and a bare sentence does not supply one.
   *   cond               "if ___" likewise: it produces a fragment, not a sentence.
   *
   * What is left changes the verb and nothing else, so the rest of the source sentence stays
   * exactly as it was written. */
  const TARGETS = ['future', 'present', 'past', 'negFuture', 'negPast', 'negPresent',
                   'immFuture', 'must', 'can', 'cannot', 'mustNot'];

  const strip = t => (t || '').replace(/[.,?!;:"“”']/g, '');

  /* surface Telugu -> every (verb, form, person) that produces it */
  let INDEX = null;
  function index() {
    if (INDEX) return INDEX;
    INDEX = new Map();
    VERBS.forEach(v => FORMS.forEach(f => {
      if (!f.person) return;                 // only person-inflected cells are swappable
      for (let pi = 0; pi < 6; pi++) {
        const a = conjugate(v, f.id, pi);
        if (!a) continue;
        if (!INDEX.has(a[1])) INDEX.set(a[1], []);
        INDEX.get(a[1]).push({ verb: v.id, form: f.id, person: pi, invariant: !!f.invariant });
      }
    }));
    return INDEX;
  }

  /* pronoun -> person index. PERSONS[5] carries two ("mīru / vāḷḷu"), so split. */
  let PRON = null;
  function pronouns() {
    if (PRON) return PRON;
    PRON = new Map();
    PERSONS.forEach((p, i) => p.pron[1].split(' / ').forEach(s => PRON.set(s.trim(), i)));
    return PRON;
  }

  const verb = id => VERBS.find(v => v.id === id);

  /* A verb with cueOv is one whose paradigm labels do not mean what they say — uṇḍu, where the
     row called `past` is the ordinary present copula. For those, only the cells cueOv actually
     covers can be offered: cueing a transformation "→ she did not wait" for lēdu would drill
     the wrong meaning into the most common verb in the language. The rule is written against
     cueOv rather than against uṇḍu by name so it stays correct as cueOv grows. */
  function cueTrustworthy(v, formId) {
    return !v.cueOv || !!v.cueOv[formId];
  }

  /* ---- analyse one sentence ----
   * Returns null when the sentence has no single unambiguous verb to work on. Sentences with
   * two recognisable forms are skipped rather than guessed at: the instruction "→ past" is
   * meaningless if the learner cannot tell which verb it refers to. */
  function analyse(s) {
    const toks = s.telugu.split(/\s+/);
    const hits = [];
    toks.forEach((t, j) => {
      const c = index().get(strip(t));
      if (c) hits.push({ j, cand: c[0] });
    });
    if (hits.length !== 1) return null;

    const { j, cand } = hits[0];
    const v = verb(cand.verb);
    if (!v) return null;

    /* The romanization is respaced independently of the script (build_sentences unglues
       tokens there and deliberately leaves the script alone), so the two token lists are not
       reliably the same length. Match the romanization by value, not by position. */
    const romForm = conjugate(v, cand.form, cand.person)[0];
    const romToks = s.roman.split(/\s+/);
    const rj = romToks.findIndex(t => strip(t) === romForm);
    if (rj < 0) return null;

    /* A person swap has to move the subject too, so it is only offered when there is a bare
       pronoun that agrees with the verb. Without that guard, `ikkaḍa okaṭi undi` becomes
       `nēnu ikkaḍa okaṭi unnānu` — grammatical, and nonsense. */
    let pron = null;
    if (!cand.invariant) {
      const pj = toks.findIndex(t => pronouns().has(strip(t)));
      if (pj >= 0 && pronouns().get(strip(toks[pj])) === cand.person) {
        const pRom = PERSONS[cand.person].pron[0].split(' / ')[0];
        const prj = romToks.findIndex(t => strip(t) === pRom);
        if (prj >= 0) pron = { j: pj, rj: prj };
      }
    }

    return { verb: cand.verb, form: cand.form, person: cand.person,
             invariant: cand.invariant, tel: { j, toks }, rom: { j: rj, toks: romToks },
             pron, check: v.conf === 'check' };
  }

  /* Replace one or more tokens by index, keeping any trailing punctuation each carried — the
     sentence-final "?" belongs to the sentence, not to the verb that happened to be last. */
  function swap(toks, edits) {
    const out = toks.slice();
    for (const j in edits) {
      const tail = (toks[j].match(/[.,?!;:"“”]+$/) || [''])[0];
      out[j] = edits[j] + tail;
    }
    return out.join(' ');
  }

  /* ---- the transformations available for an analysed sentence ---- */
  function options(a) {
    if (!a) return [];
    const v = verb(a.verb);
    const out = [];

    /* Tense and polarity: same subject, different cell. Always safe. */
    TARGETS.forEach(formId => {
      if (formId === a.form) return;
      if (!cueTrustworthy(v, formId)) return;
      const f = FORMS.find(x => x.id === formId);
      const cell = conjugate(v, formId, a.person);
      if (!cell) return;
      /* An invariant target from an invariant source can come out identical — no exercise. */
      if (cell[1] === strip(a.tel.toks[a.tel.j])) return;
      out.push({
        kind: 'tense', op: formId,
        /* No paradigm label for a cueOv verb. "→ will ___" next to the cue "she is (as a
           standing fact)" is a label contradicting the meaning printed beside it, and the
           cue is the half that is right. Showing only the cue is both correct and the better
           instruction: produce this meaning, rather than name this tense. */
        label: v.cueOv ? null : f.short,
        cue: cue(v, formId, a.person),
        tel: swap(a.tel.toks, { [a.tel.j]: cell[1] }),
        rom: swap(a.rom.toks, { [a.rom.j]: cell[0] }),
      });
    });

    /* Person: move the subject and the verb together. Only where a bare pronoun agreed. */
    if (a.pron && cueTrustworthy(v, a.form)) {
      PERSONS.forEach((p, pi) => {
        if (pi === a.person) return;
        const cell = conjugate(v, a.form, pi);
        if (!cell) return;
        const pronTel = p.pron[1].split(' / ')[0];
        const pronRom = p.pron[0].split(' / ')[0];
        out.push({
          kind: 'person', op: 'person:' + p.id,
          label: p.en,
          cue: cue(v, a.form, pi),
          tel: swap(a.tel.toks, { [a.tel.j]: cell[1], [a.pron.j]: pronTel }),
          rom: swap(a.rom.toks, { [a.rom.j]: cell[0], [a.pron.rj]: pronRom }),
        });
      });
    }

    return out;
  }

  /* ---- cloze ----
   * Blank the verb when there is one, because that is the part carrying the grammar.
   * Returns null when no honest blank can be made; the caller falls back to another mode.
   */
  function cloze(s, a) {
    const toks = s.telugu.split(/\s+/);
    const romToks = s.roman.split(/\s+/);
    if (toks.length < 2) return null;          // blanking the only word leaves no exercise

    if (a) {
      /* The verb was located in each script independently, by value, so the two indices are
         known to point at the same word even where the token lists differ in length. */
      return blanked(toks, romToks, a.tel.j, a.rom.j);
    }

    /* No verb to blank, so fall back to the longest token. That needs the two token lists to
       line up positionally, and they do not always: build_sentences respaces the romanization
       of glued tokens and deliberately leaves the script alone. Choosing an index separately
       in each list blanks two *different* words — it was showing `_____` over ippuḍu in the
       romanization and over veḷḷaku in the script, an exercise with two different answers.
       Only offer it when the lists agree on length. */
    if (toks.length !== romToks.length || toks.length < 3) return null;
    const j = romToks.reduce((b, t, i) => strip(t).length > strip(romToks[b]).length ? i : b, 0);
    return blanked(toks, romToks, j, j);
  }

  function blanked(toks, romToks, tj, rj) {
    return { tel: swap(toks, { [tj]: '_____' }), rom: swap(romToks, { [rj]: '_____' }),
             answerTel: strip(toks[tj]), answerRom: strip(romToks[rj]) };
  }

  return { analyse, options, cloze, TARGETS };
})();
