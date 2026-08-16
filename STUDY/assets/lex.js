/* Client-side word matching, shared by the analyzer and the reader's transcript loader.
 *
 * The offline pipeline (tools/build_reader.py) is still the better resolver — it has te2rom
 * for romanizing script, a 235k-word English dictionary, and the loose chat-romanization
 * fold. None of that can ship to the browser at a sane size. What *can* run here is the path
 * that matters most for real content: Telugu script matched straight against the master's
 * Telugu script, no romanization step required, no guessing.
 *
 * That is why this exists rather than being folded into build_reader: content the learner is
 * not allowed to republish has to be resolved on their own machine, in the page, from a file
 * they hold. Everything here is deliberately exact — a wrong gloss is worse than a gap.
 */
const Lex = (() => {
  const FOLD = { 'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ḷ': 'l', 'ṁ': 'm', 'ṣ': 's', 'ś': 's', 'ṛ': 'r' };
  const fold = s => (s || '').toLowerCase().replace(/[āīūēōṭḍṇḷṁṣśṛ]/g, c => FOLD[c]).replace(/[^a-z]/g, '');

  /* Telugu first and as a run: its vowel signs and virama are combining marks that \w does
     not match, so a plain \w+ shatters చేస్తాను into nine graphemes. */
  const TOKEN = /[ఀ-౿]+|[^\W\d_]+(?:['’][^\W\d_]+)*|\d+|[^\w\s]+|\s+/gu;
  const TELUGU = /[ఀ-౿]/;
  const isTelugu = s => TELUGU.test(s);

  let byScript = null, byRoman = null;
  function index() {
    if (byScript) return;
    byScript = new Map(); byRoman = new Map();
    const F = WORD_DATA.fields;
    WORD_DATA.words.forEach(row => {
      const w = {}; F.forEach((k, i) => w[k] = row[i]);
      if (w.telugu) byScript.set(w.telugu.trim(), w);
      const f = fold((w.roman || '').split(' ')[0]);
      if (f && !byRoman.has(f)) byRoman.set(f, w);
    });
  }

  function lookup(tok) {
    index();
    return (isTelugu(tok) ? byScript.get(tok.trim()) : byRoman.get(fold(tok))) || null;
  }

  /* A stable key for remembering a word's status. Script keys on the script itself, since
     without te2rom there is nothing else to key on. */
  const keyOf = tok => (isTelugu(tok) ? tok.trim() : fold(tok));

  function tokens(text) {
    return [...text.matchAll(TOKEN)].map(m => m[0]);
  }

  /* -> [surface, kind, lexIndex] plus a growing lex, matching the shape build_reader emits so
     the reader can render either without caring which produced it. */
  function resolveLine(text, lex, lexidx) {
    const out = [];
    for (const piece of tokens(text)) {
      const k = keyOf(piece);
      if (!k) { out.push([piece, 'p', -1]); continue; }
      const hit = lookup(piece);
      const id = hit ? hit.guid : k;
      if (!lexidx.has(id)) {
        lexidx.set(id, lex.length);
        lex.push(hit
          ? { k, r: hit.roman, te: hit.telugu, en: hit.english, o: hit.order, g: hit.guid }
          : { k, r: isTelugu(piece) ? Te2Rom.romanize(piece) : piece.toLowerCase(),
              te: isTelugu(piece) ? piece : '', en: '', o: 0, g: '' });
      }
      /* Script tokens carry their romanization as a fourth element, exactly as the offline
         pipeline emits — the reader renders that, because the learner cannot read the script
         yet and a page of it is a wall rather than practice. */
      const rom = isTelugu(piece) ? Te2Rom.romanize(piece) : null;
      out.push(rom ? [piece, hit ? 't' : 'w', lexidx.get(id), rom]
                   : [piece, hit ? 't' : 'w', lexidx.get(id)]);
    }
    return out;
  }

  return { fold, isTelugu, lookup, keyOf, tokens, resolveLine };
})();
