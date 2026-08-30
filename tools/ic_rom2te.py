# -*- coding: utf-8 -*-
"""The book's romanization -> Telugu script. The inverse of te2rom.py, for one narrow purpose.

    python3 tools/ic_rom2te.py --check        # round-trip every aligned turn, report

te2rom.py's docstring says the reverse direction is not deterministic and is not attempted
anywhere in this project. That is true in general and stays true: this is NOT a general
romanization reader. It parses ONE scheme — the one "An Intensive Course in Telugu" prints —
which is a strict scholarly transliteration where every distinction the script makes is written
down: vowel length, retroflexion, aspiration, gemination, and anusvara as its own symbol rather
than left to context.

WHY IT IS ALLOWED TO EXIST HERE, GIVEN THAT RULE
Because nothing downstream trusts it. Its only job is to turn the 182 turns that carry BOTH the
legacy bytes and the book's romanization into known-correct Telugu, so that ic_decode.py can be
derived against them. Every line it produces is checked by round-tripping back through
te2rom.py, and a line that does not come back identical is discarded rather than used. It is a
key-generator for a decipherment, not a translator.

WHERE THE BOOK'S SCHEME DIFFERS FROM THE PROJECT'S
  c   is చ      (te2rom writes ch)
  ch  is ఛ      (te2rom writes chh)
  ṁ   is ం       always, never assimilated — te2rom's `n`/`m`-before-a-stop rule is a display
                 convention, so comparison runs with assimilate=False
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import te2rom

VIRAMA = '్'

CONS = {
    'k': 'క', 'kh': 'ఖ', 'g': 'గ', 'gh': 'ఘ', 'ṅ': 'ఙ',
    'c': 'చ', 'ch': 'ఛ', 'j': 'జ', 'jh': 'ఝ', 'ñ': 'ఞ',
    'ṭ': 'ట', 'ṭh': 'ఠ', 'ḍ': 'డ', 'ḍh': 'ఢ', 'ṇ': 'ణ',
    't': 'త', 'th': 'థ', 'd': 'ద', 'dh': 'ధ', 'n': 'న',
    'p': 'ప', 'ph': 'ఫ', 'b': 'బ', 'bh': 'భ', 'm': 'మ',
    'y': 'య', 'r': 'ర', 'ṟ': 'ఱ', 'l': 'ల', 'ḷ': 'ళ', 'v': 'వ',
    'ś': 'శ', 'ṣ': 'ష', 's': 'స', 'h': 'హ',
}
IND = {'a': 'అ', 'ā': 'ఆ', 'i': 'ఇ', 'ī': 'ఈ', 'u': 'ఉ', 'ū': 'ఊ', 'ṛ': 'ఋ',
       'e': 'ఎ', 'ē': 'ఏ', 'ai': 'ఐ', 'o': 'ఒ', 'ō': 'ఓ', 'au': 'ఔ'}
SIGN = {'a': '', 'ā': 'ా', 'i': 'ి', 'ī': 'ీ', 'u': 'ు', 'ū': 'ూ', 'ṛ': 'ృ',
        'e': 'ె', 'ē': 'ే', 'ai': 'ై', 'o': 'ొ', 'ō': 'ో', 'au': 'ౌ'}
MARK = {'ṁ': 'ం', 'ḥ': 'ః'}

# Two-character forms must be tried before one-character ones or `kh` reads as k + h.
CONS_KEYS = sorted(CONS, key=len, reverse=True)
VOW_KEYS = sorted(SIGN, key=len, reverse=True)


def _match(s, i, keys):
    for k in keys:
        if s.startswith(k, i):
            return k
    return None


def word(w):
    """One romanized word to script.

    A Telugu syllable is a run of consonants followed by at most one vowel. Read the run
    greedily, then the vowel: every consonant but the last takes a virama (which is both how a
    conjunct is written and how gemination is written), and the last takes the vowel's sign —
    or a virama of its own if the word ends without one.
    """
    out, i, n = [], 0, len(w)
    while i < n:
        run = []
        while True:
            c = _match(w, i, CONS_KEYS)
            if not c:
                break
            run.append(CONS[c])
            i += len(c)
            if _match(w, i, VOW_KEYS):
                break                     # the vowel closes the run
        if run:
            v = _match(w, i, VOW_KEYS)
            if v:
                i += len(v)
                out.append(VIRAMA.join(run) + SIGN[v])
            else:
                out.append(VIRAMA.join(run) + VIRAMA)   # dead final consonant: ḍākṭar
            continue
        v = _match(w, i, VOW_KEYS)
        if v:                              # a vowel with no consonant before it stands alone
            out.append(IND[v]); i += len(v); continue
        if w[i] in MARK:
            out.append(MARK[w[i]]); i += 1; continue
        out.append(w[i]); i += 1           # punctuation and anything unrecognised
    return ''.join(out)


def convert(text):
    return ''.join(p if p.isspace() else word(p) for p in re.split(r'(\s+)', text))


def normalise(project_rom):
    """te2rom's output in the book's spelling, so the two can be compared at all."""
    s = project_rom.replace('chh', '\x00').replace('ch', 'c').replace('\x00', 'ch')
    return s.lower()


def check(path):
    ok = bad = 0
    misses = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            gold = row['rom'].strip()
            if not gold:
                continue
            got = normalise(te2rom.romanize(convert(gold), assimilate=False))
            if got == gold.lower():
                ok += 1
            else:
                bad += 1
                if len(misses) < 12:
                    misses.append((gold, got))
    tot = ok + bad
    print(f'{tot} aligned turns · {ok} round-trip clean ({ok/max(tot,1):.1%}) · {bad} rejected')
    for g, o in misses:
        print(f'\n  book  {g}\n  back  {o}')
    return ok, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--pairs', default=os.path.join(HERE, '..', 'intensive', 'raw', 'pairs.tsv'))
    ap.add_argument('text', nargs='?')
    args = ap.parse_args()
    if args.text:
        print(convert(args.text))
    elif args.check:
        check(args.pairs)
    else:
        ap.error('give text to convert, or --check')


if __name__ == '__main__':
    main()
