/* Telugu script -> the project's romanization. A direct port of tools/te2rom.py.
 *
 * WHY A SECOND IMPLEMENTATION EXISTS, AND HOW IT IS KEPT HONEST
 * The Python version runs in the offline pipeline. This one runs in the browser, for
 * transcripts that cannot be committed and therefore cannot be baked — without it those texts
 * render as script the learner cannot read, which defeats the point of loading them.
 *
 * Two implementations of the same rule is exactly the drift this project has been careful to
 * avoid, so the port is deliberately mechanical — same tables, same order of tests, same
 * assimilation rules — and `tools/check_te2rom.py` diffs the two over every distinct Telugu
 * token available. Change one, run that, or they will part company silently.
 *
 * The direction is near-deterministic: the script marks vowel length, retroflexion and
 * gemination explicitly, which is what the romanization needs. The reverse is not, and is not
 * attempted anywhere in this project.
 */
const Te2Rom = (() => {
  const VIRAMA = '్', ANUSVARA = 'ం', VISARGA = 'ః', CANDRABINDU = 'ఁ';

  const CONS = {
    'క': 'k', 'ఖ': 'kh', 'గ': 'g', 'ఘ': 'gh', 'ఙ': 'ṅ',
    'చ': 'ch', 'ఛ': 'chh', 'జ': 'j', 'ఝ': 'jh', 'ఞ': 'ñ',
    'ట': 'ṭ', 'ఠ': 'ṭh', 'డ': 'ḍ', 'ఢ': 'ḍh', 'ణ': 'ṇ',
    'త': 't', 'థ': 'th', 'ద': 'd', 'ధ': 'dh', 'న': 'n',
    'ప': 'p', 'ఫ': 'ph', 'బ': 'b', 'భ': 'bh', 'మ': 'm',
    'య': 'y', 'ర': 'r', 'ఱ': 'ṟ', 'ల': 'l', 'ళ': 'ḷ', 'ఴ': 'ḻ',
    'వ': 'v', 'శ': 'ś', 'ష': 'ṣ', 'స': 's', 'హ': 'h',
  };
  const IND_VOW = {
    'అ': 'a', 'ఆ': 'ā', 'ఇ': 'i', 'ఈ': 'ī', 'ఉ': 'u', 'ఊ': 'ū',
    'ఋ': 'ṛ', 'ౠ': 'ṝ', 'ఌ': 'ḷ̥', 'ౡ': 'ḹ',
    'ఎ': 'e', 'ఏ': 'ē', 'ఐ': 'ai', 'ఒ': 'o', 'ఓ': 'ō', 'ఔ': 'au',
  };
  const SIGN_VOW = {
    'ా': 'ā', 'ి': 'i', 'ీ': 'ī', 'ు': 'u', 'ూ': 'ū',
    'ృ': 'ṛ', 'ౄ': 'ṝ', 'ె': 'e', 'ే': 'ē', 'ై': 'ai',
    'ొ': 'o', 'ో': 'ō', 'ౌ': 'au', 'ౢ': 'l̥', 'ౣ': 'l̥̄',
  };
  const DIGITS = {};
  for (let i = 0; i < 10; i++) DIGITS[String.fromCharCode(0x0c66 + i)] = String(i);

  const ZERO_WIDTH = '‌‍﻿';   // ZWNJ/ZWJ turn up inside loanwords

  function romanizeWord(w) {
    w = [...w].filter(c => !ZERO_WIDTH.includes(c)).join('');
    const out = [];
    let i = 0;
    const n = w.length;
    while (i < n) {
      const c = w[i];
      if (IND_VOW[c] !== undefined) { out.push(IND_VOW[c]); i++; continue; }
      if (DIGITS[c] !== undefined) { out.push(DIGITS[c]); i++; continue; }
      if (CONS[c] !== undefined) {
        out.push(CONS[c]); i++;
        // a consonant carries an inherent 'a' unless a vowel sign or virama follows
        if (i < n && w[i] === VIRAMA) i++;
        else if (i < n && SIGN_VOW[w[i]] !== undefined) { out.push(SIGN_VOW[w[i]]); i++; }
        else out.push('a');
        continue;
      }
      if (c === ANUSVARA) { out.push('ṁ'); i++; continue; }
      if (c === VISARGA) { out.push('ḥ'); i++; continue; }
      if (c === CANDRABINDU) { out.push('m̐'); i++; continue; }
      if (SIGN_VOW[c] !== undefined) { out.push(SIGN_VOW[c]); i++; continue; }
      out.push(c); i++;                         // punctuation, latin, spaces
    }
    return out.join('');
  }

  /* Anusvara assimilates to the following stop, and the project writes the result rather than
     a bare ṁ: తింటాను -> tiṇṭānu. ṅ and ñ carry nothing an English reader lacks — "ng" and
     "nch" already read correctly — so both are written n. Retroflexion does matter, so ṇ
     survives before ṭ and ḍ. */
  function anusvaraPlace(s) {
    const chars = [...s];
    return chars.map((ch, i) => {
      if (ch !== 'ṁ') return ch;
      const nxt = chars[i + 1] || '';
      if (!nxt || /\s/.test(nxt)) return 'ṁ';   // word-final stays ṁ
      if ('kg'.includes(nxt)) return 'n';
      if ('cj'.includes(nxt)) return 'n';
      if ('ṭḍ'.includes(nxt)) return 'ṇ';
      if ('tdn'.includes(nxt)) return 'n';
      if ('pbm'.includes(nxt)) return 'm';
      return 'ṁ';                                // before a fricative, y, l, v…
    }).join('');
  }

  function romanize(text, assimilate = true) {
    const parts = String(text || '').trim().split(/(\s+)/);
    const out = parts.map(p => /^\s+$/.test(p) ? p : romanizeWord(p)).join('');
    return assimilate ? anusvaraPlace(out) : out;
  }

  return { romanize, romanizeWord };
})();
