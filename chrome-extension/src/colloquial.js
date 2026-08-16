/* The romanization Telugu speakers actually type, as an alternative to the project's ISO-ish
 * scheme. Same input, different output conventions:
 *
 *     ISO          colloquial
 *     nēnu         nenu
 *     kūḍā         kooda
 *     āyana        aayana
 *     tinu         thinu          (dental t takes the h; retroflex ṭ stays plain t)
 *     veḷḷu        vellu
 *
 * WHY BOTH EXIST
 * The ISO scheme marks vowel length and retroflexion unambiguously, which is what makes it
 * safe to romanize *from* the script and to match against the deck. Nobody types it. The
 * colloquial one is what appears in messages, in the family transcripts, and in most Telugu
 * written by Telugu speakers in Latin letters — so it is the one to read if the goal is to
 * recognise the language as it is actually written informally.
 *
 * IT IS LOSSY ON PURPOSE, AND AMBIGUOUS AS A RESULT.
 * ē and e both come out "e", ō and o both "o", ఠ and త both "th". That is the convention, not
 * a bug: real chat spelling does not distinguish them either. Do not use this output to look a
 * word up — it cannot round-trip. Use it to read.
 */
const Colloquial = (() => {
  const VIRAMA = '్', ANUSVARA = 'ం', VISARGA = 'ః', CANDRABINDU = 'ఁ';

  const CONS = {
    'క': 'k', 'ఖ': 'kh', 'గ': 'g', 'ఘ': 'gh', 'ఙ': 'n',
    'చ': 'ch', 'ఛ': 'chh', 'జ': 'j', 'ఝ': 'jh', 'ఞ': 'n',
    // retroflex stays plain; the dental series takes the h. This is the split that makes
    // "thinu" read as తిను and "tinu" as టిను to someone used to chat spelling.
    'ట': 't', 'ఠ': 'th', 'డ': 'd', 'ఢ': 'dh', 'ణ': 'n',
    'త': 'th', 'థ': 'th', 'ద': 'dh', 'ధ': 'dh', 'న': 'n',
    'ప': 'p', 'ఫ': 'ph', 'బ': 'b', 'భ': 'bh', 'మ': 'm',
    'య': 'y', 'ర': 'r', 'ఱ': 'r', 'ల': 'l', 'ళ': 'l', 'ఴ': 'l',
    'వ': 'v', 'శ': 'sh', 'ష': 'sh', 'స': 's', 'హ': 'h',
  };
  const IND_VOW = {
    'అ': 'a', 'ఆ': 'aa', 'ఇ': 'i', 'ఈ': 'ee', 'ఉ': 'u', 'ఊ': 'oo',
    'ఋ': 'ru', 'ౠ': 'ru', 'ఌ': 'lu', 'ౡ': 'lu',
    'ఎ': 'e', 'ఏ': 'e', 'ఐ': 'ai', 'ఒ': 'o', 'ఓ': 'o', 'ఔ': 'au',
  };
  const SIGN_VOW = {
    'ా': 'aa', 'ి': 'i', 'ీ': 'ee', 'ు': 'u', 'ూ': 'oo',
    'ృ': 'ru', 'ౄ': 'ru', 'ె': 'e', 'ే': 'e', 'ై': 'ai',
    'ొ': 'o', 'ో': 'o', 'ౌ': 'au', 'ౢ': 'lu', 'ౣ': 'lu',
  };
  const DIGITS = {};
  for (let i = 0; i < 10; i++) DIGITS[String.fromCharCode(0x0c66 + i)] = String(i);

  const ZERO_WIDTH = '‌‍﻿';

  function word(w) {
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
        if (i < n && w[i] === VIRAMA) i++;
        else if (i < n && SIGN_VOW[w[i]] !== undefined) { out.push(SIGN_VOW[w[i]]); i++; }
        else out.push('a');
        continue;
      }
      if (c === ANUSVARA) { out.push('ṁ'); i++; continue; }   // resolved below
      if (c === VISARGA) { out.push('h'); i++; continue; }
      if (c === CANDRABINDU) { out.push('n'); i++; continue; }
      if (SIGN_VOW[c] !== undefined) { out.push(SIGN_VOW[c]); i++; continue; }
      out.push(c); i++;
      }
    return out.join('');
  }

  /* Same assimilation the ISO scheme does, but everything lands on plain n or m — chat
     spelling has no ṇ, so "ఇంట్లో" is written intlo, not iṇṭlō. */
  function nasal(s) {
    const chars = [...s];
    return chars.map((ch, i) => {
      if (ch !== 'ṁ') return ch;
      const nxt = chars[i + 1] || '';
      if (!nxt || /\s/.test(nxt)) return 'm';
      if ('pbm'.includes(nxt)) return 'm';
      return 'n';
    }).join('');
  }

  /* Doubling a consonant across a virama is how gemination shows up, and chat spelling keeps
     it — pelli, ammā. Nothing to do; concatenation already produces it. */
  /* Word-final long ā is written single in practice. The family transcripts settle it:
     kooda 28 / koodaa 0, baaga 9 / baagaa 0, manchiga 14. Applied per word, so the ā inside
     kūḍā's first syllable still doubles. */
  const finalA = w => w.replace(/aa$/, 'a');

  function romanize(text) {
    const parts = String(text || '').trim().split(/(\s+)/);
    return nasal(parts.map(p => /^\s+$/.test(p) ? p : finalA(word(p))).join(''));
  }

  return { romanize };
})();

if (typeof module !== 'undefined') module.exports = { Colloquial };
