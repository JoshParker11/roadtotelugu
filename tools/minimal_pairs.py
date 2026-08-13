# -*- coding: utf-8 -*-
"""Find minimal pairs for ear training.

    python3 tools/minimal_pairs.py

Telugu has three contrasts English does not, and you cannot acquire from input you cannot
hear correctly. This pulls every pair in the word master that differs by exactly one of them:

    length      nela "month"        vs  nēla "ground"
    retroflex   nīti "morality"     vs  nīṭi "water"
    gemination  prati "every"       vs  pratti "cotton"

The filter that matters is the gloss check. ṭamāṭa/ṭamāṭā and peḷli/peḷḷi come out of a naive
scan too, but they are one word spelled two ways, not a contrast — if the two glosses share a
content word the pair is discarded. That is the same test the gloss resolver uses.

Output is a recording script: `review/minimal-pairs.tsv`. Hand it to a native speaker, record
the two columns, and it becomes the discrimination drill that is the single best use of car
time. Until then it is still worth reading aloud at the desk.
"""
import csv, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import glosses

ROOT = os.path.normpath(os.path.join(HERE, '..'))
WORDS = os.path.join(ROOT, 'data', 'master_words.tsv')
OUT = os.path.join(ROOT, 'review', 'minimal-pairs.tsv')

LONG = {'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o'}
RETRO = {'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ḷ': 'l'}

# Pairs the lessons single out that may not both be in the master yet. Kept so the drill
# always contains the ones the course explicitly warns about.
SEEDED = [
    ('length', 'paḍu', 'పడు', 'to fall', 'pāḍu', 'పాడు', 'to sing', 'lesson-07'),
    ('length', 'nenu', 'నెను', '(not a word — the mistake)', 'nēnu', 'నేను', 'I', 'lesson-02'),
]


def variants(s):
    """Every single-feature neutralisation of s, tagged with the contrast it removes."""
    out = []
    for i, c in enumerate(s):
        if c in LONG:
            out.append(('length', s[:i] + LONG[c] + s[i + 1:]))
        if c in RETRO:
            out.append(('retroflex', s[:i] + RETRO[c] + s[i + 1:]))
    for m in re.finditer(r'(.)\1', s):
        out.append(('gemination', s[:m.start()] + m.group(1) + s[m.end():]))
    return out


def same_word(a, b):
    """Two glosses describing one word rather than two — a spelling variant, not a pair."""
    ca, cb = glosses.content_words(a), glosses.content_words(b)
    if not ca or not cb:
        return glosses.normalise(a) == glosses.normalise(b)
    return bool(ca & cb)


def main():
    rows = [r for r in csv.DictReader(open(WORDS, encoding='utf-8'), delimiter='\t')
            if r['telugu'] and r['roman'] and not ({'needs-script', 'no-script', 'kannada-script',
                                                    'bound-suffix'} & set(r['flags'].split()))]
    by = {}
    for r in rows:
        by.setdefault(r['roman'], r)

    found, rejected = {}, 0
    for rom in by:
        for kind, neutral in variants(rom):
            other = by.get(neutral)
            if not other or other['roman'] == rom:
                continue
            a, b = sorted((rom, neutral))
            if (kind, a, b) in found:
                continue
            if same_word(by[a]['english'], by[b]['english']):
                rejected += 1
                continue
            found[(kind, a, b)] = (by[a], by[b])

    out = []
    for (kind, a, b), (ra, rb) in sorted(found.items()):
        out.append({'contrast': kind, 'a_rom': a, 'a_telugu': ra['telugu'],
                    'a_english': ra['english'][:44], 'b_rom': b, 'b_telugu': rb['telugu'],
                    'b_english': rb['english'][:44], 'source': 'master', 'recorded': ''})
    have = {(r['a_rom'], r['b_rom']) for r in out}
    for kind, ar, at, ae, br, bt, be, src in SEEDED:
        if (ar, br) not in have and (br, ar) not in have:
            out.append({'contrast': kind, 'a_rom': ar, 'a_telugu': at, 'a_english': ae,
                        'b_rom': br, 'b_telugu': bt, 'b_english': be,
                        'source': src, 'recorded': ''})
    order = {'length': 0, 'retroflex': 1, 'gemination': 2}
    out.sort(key=lambda r: (order[r['contrast']], r['a_rom']))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cols = ['contrast', 'a_rom', 'a_telugu', 'a_english', 'b_rom', 'b_telugu', 'b_english',
            'source', 'recorded']
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t')
        w.writeheader(); w.writerows(out)

    print(f'{len(out)} minimal pairs -> {os.path.relpath(OUT, ROOT)}')
    print(f'  {rejected} rejected as spelling variants of one word')
    for k, n in Counter(r['contrast'] for r in out).items():
        print(f'    {k:<12} {n}')
    print()
    for r in out:
        print(f"  {r['contrast'][:4]}  {r['a_rom']:<12}{r['a_english'][:26]:<28}"
              f"{r['b_rom']:<12}{r['b_english'][:26]}")


if __name__ == '__main__':
    main()
