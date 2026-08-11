# -*- coding: utf-8 -*-
"""Telugu script -> ISO-ish romanization, matching the convention already used across
this project (ā ī ū ē ō · ṭ ḍ ṇ ḷ ṣ ś · ch for చ · ṁ for anusvara).

This direction is near-deterministic: the script encodes vowel length, retroflexion and
gemination explicitly, which is exactly what romanization needs. The reverse direction is
not, which is why it is not attempted anywhere in this project.
"""
import re, unicodedata

VIRAMA = '్'
ANUSVARA = 'ం'
VISARGA = 'ః'
CANDRABINDU = 'ఁ'

CONS = {
 'క':'k','ఖ':'kh','గ':'g','ఘ':'gh','ఙ':'ṅ',
 'చ':'ch','ఛ':'chh','జ':'j','ఝ':'jh','ఞ':'ñ',
 'ట':'ṭ','ఠ':'ṭh','డ':'ḍ','ఢ':'ḍh','ణ':'ṇ',
 'త':'t','థ':'th','ద':'d','ధ':'dh','న':'n',
 'ప':'p','ఫ':'ph','బ':'b','భ':'bh','మ':'m',
 'య':'y','ర':'r','ఱ':'ṟ','ల':'l','ళ':'ḷ','ఴ':'ḻ',
 'వ':'v','శ':'ś','ష':'ṣ','స':'s','హ':'h','క్ష':'kṣ',
}
IND_VOW = {
 'అ':'a','ఆ':'ā','ఇ':'i','ఈ':'ī','ఉ':'u','ఊ':'ū',
 'ఋ':'ṛ','ౠ':'ṝ','ఌ':'ḷ̥','ౡ':'ḹ',
 'ఎ':'e','ఏ':'ē','ఐ':'ai','ఒ':'o','ఓ':'ō','ఔ':'au',
}
SIGN_VOW = {
 'ా':'ā','ి':'i','ీ':'ī','ు':'u','ూ':'ū',
 'ృ':'ṛ','ౄ':'ṝ','ె':'e','ే':'ē','ై':'ai',
 'ొ':'o','ో':'ō','ౌ':'au','ౢ':'l̥','ౣ':'l̥̄',
}
DIGITS = {chr(0x0c66+i): str(i) for i in range(10)}


ZERO_WIDTH = '\u200c\u200d\ufeff'   # ZWNJ/ZWJ appear inside loanwords: డాక్టర్‌ని

def romanize_word(w):
    w = ''.join(c for c in w if c not in ZERO_WIDTH)
    out = []
    i, n = 0, len(w)
    while i < n:
        c = w[i]
        if c in IND_VOW:
            out.append(IND_VOW[c]); i += 1; continue
        if c in DIGITS:
            out.append(DIGITS[c]); i += 1; continue
        if c in CONS:
            out.append(CONS[c]); i += 1
            # a consonant carries an inherent 'a' unless a vowel sign or virama follows
            if i < n and w[i] == VIRAMA:
                i += 1                      # dead consonant, no vowel
            elif i < n and w[i] in SIGN_VOW:
                out.append(SIGN_VOW[w[i]]); i += 1
            else:
                out.append('a')
            continue
        if c == ANUSVARA:
            out.append('ṁ'); i += 1; continue
        if c == VISARGA:
            out.append('ḥ'); i += 1; continue
        if c == CANDRABINDU:
            out.append('m̐'); i += 1; continue
        if c in SIGN_VOW:                    # stray sign, shouldn't happen
            out.append(SIGN_VOW[c]); i += 1; continue
        out.append(c); i += 1                # punctuation, latin, spaces
    return ''.join(out)


def _anusvara_place(s):
    """Anusvara assimilates to the following stop. The project writes the result rather
    than a bare ṁ: తింటాను -> tinṭānu, ఇంగ్లీష్ -> ingliṣ."""
    out = []
    for i, ch in enumerate(s):
        if ch != 'ṁ':
            out.append(ch); continue
        nxt = s[i+1] if i+1 < len(s) else ''
        # NB: '' is a substring of every string, so the empty case must be tested first
        if not nxt or nxt.isspace():  out.append('ṁ')   # word-final stays ṁ
        # ṅ and ñ carry no information an English reader lacks — "ng", "nch" already read
        # correctly — so both are written n, which is also what the course pages mostly do.
        elif nxt in 'kg':             out.append('n')   # rangu, inkā
        elif nxt in 'cj':             out.append('n')   # manchi, sanjay
        elif nxt in 'ṭḍ':             out.append('ṇ')   # reṇḍu, iṇṭlō — retroflexion does matter
        elif nxt in 'tdn':            out.append('n')
        elif nxt in 'pbm':            out.append('m')
        else:                         out.append('ṁ')   # before a fricative, y, l, v…
    return ''.join(out)


def romanize(text, assimilate=True):
    parts = re.split(r'(\s+)', text.strip())
    out = ''.join(p if p.isspace() else romanize_word(p) for p in parts)
    return _anusvara_place(out) if assimilate else out


if __name__ == '__main__':
    import json, sys, os
    D = os.path.dirname(os.path.abspath(__file__))
    pairs = []
    for fn in ('anki_rows.json', 'sent_rows.json'):
        p = os.path.join(D, fn)
        if not os.path.exists(p): continue
        for r in json.load(open(p)):
            rom, tel = r.get('rom', ''), r.get('tel', '')
            if rom and tel and not any(c in rom for c in '→·/_()[]'):
                pairs.append((tel, rom))
    seen, uniq = set(), []
    for t, r in pairs:
        if (t, r) not in seen: seen.add((t, r)); uniq.append((t, r))
    ok, bad = 0, []
    for tel, gold in uniq:
        got = romanize(tel)
        if got.lower() == gold.lower(): ok += 1
        else: bad.append((tel, gold, got))
    print(f'attested pairs: {len(uniq)}   exact: {ok}  ({100*ok/len(uniq):.1f}%)')
    for b in bad[:40]:
        print(f'   {b[0]:<22} gold={b[1]:<24} got={b[2]}')
