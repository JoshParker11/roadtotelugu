# -*- coding: utf-8 -*-
"""Rebuild ministories/names.tsv — the proper nouns needing a transliteration decision.

    python3 tools/ms_names.py            # rebuild, carrying existing transliterations forward
    python3 tools/ms_names.py --rejected # also list what was excluded, and why

WHY THIS IS NOT JUST "GREP FOR CAPITALS"
It was, in its first version, and the result was 225 entries of which about 135 were not names:
every sentence-initial adverb (However, Finally, Maybe) and every title-cased common noun from a
lesson heading (Cook, Umbrella, Vacation). A name list that is 60% noise is worse than no list,
because check_ms.py reads it and starts reporting things that are not problems — and a checker
that cries wolf once a run is a checker nobody reads.

Two tests separate a proper noun from a capitalised common one, and both come free from having
the whole corpus in hand:

1. **Does the word ever appear lowercase?** "Cook" is capitalised in the title *Mike is a Cook*
   and lowercase in *Mike is a cook at a restaurant*. One lowercase occurrence anywhere is proof
   the capital was positional, not lexical. This alone removes most of the noise.
2. **Does it ever appear away from the start of a sentence?** "However" is capitalised every time
   it occurs, so test 1 clears it — but it is *only* ever sentence-initial, which no real name is
   across 1,700 occurrences.

A word must pass both to be kept. Everything rejected is listed with --rejected, because a
silent filter is how a real name goes missing for sixty lessons.

**`meta` rows are excluded from the scan entirely.** LingQ's lesson titles are Title Case, so
every word in them is capitalised, never appears lowercase, and is not sentence-initial — they
defeat both tests at once and smuggle in Business, Decision, Routine, Searches, Visits and the
spelled-out numbers from "Story Eighteen". Nothing is lost by ignoring them: a lesson's title
names its protagonist, but so does its first sentence.

WHY `kind` MATTERS
Not every proper noun is a person. France, Friday, French and Uber all need transliterating, but
they are different decisions — a place name has a conventional Telugu form, a brand usually keeps
its sound, a weekday has an ordinary Telugu word that should probably win. Grouping them means
deciding once per group instead of once per word.
"""
import argparse
import csv
import glob
import os
import re
import sys
from msfiles import work_tsvs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
NAMES = os.path.join(MS, 'names.tsv')

COLS = ['name', 'kind', 'te', 'count', 'lessons', 'notes']

# Proper nouns that are not personal names. Each group is one decision, not N decisions.
KINDS = {
    'place': {'France', 'Canada', 'Los', 'Angeles', 'United', 'States', 'North', 'West'},
    'lang': {'French', 'Thai', 'Italian', 'English'},
    'brand': {'Uber', 'Kindle', 'Internet'},
    'day': {'Friday', 'Monday', 'Mondays', 'Saturdays'},
    'subject': {'Sociology', 'Humanities', 'Math', 'History', 'Science'},
    'kin': {'Mom'},
}
# Sentence-initial position: start of the field, or after terminal punctuation or a colon.
INITIAL = re.compile(r'(?:^|[.!?:]\s+|["“]\s*)([A-Z][a-z]+)')
WORD = re.compile(r"\b([A-Za-z][a-z]+)\b")


def scan():
    upper, lower, initial, where = {}, set(), {}, {}
    for path in work_tsvs(WORK):
        sid = os.path.basename(path)[:-4]
        with open(path, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if r['part'] == 'meta':
                    continue          # Title Case defeats both tests; see the module docstring
                en = r['en']
                inits = set(INITIAL.findall(en))
                for w in WORD.findall(en):
                    if w[0].isupper():
                        upper[w] = upper.get(w, 0) + 1
                        where.setdefault(w, set()).add(sid)
                        if w in inits:
                            initial[w] = initial.get(w, 0) + 1
                    else:
                        lower.add(w.lower())
    return upper, lower, initial, where


def classify(w):
    for kind, members in KINDS.items():
        if w in members:
            return kind
    return 'person'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rejected', action='store_true', help='list excluded words and why')
    args = ap.parse_args()

    upper, lower, initial, where = scan()
    carry = {}
    if os.path.exists(NAMES):
        with open(NAMES, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if r.get('te'):
                    carry[r['name']] = r['te']

    kept, rejected = [], []
    for w, n in sorted(upper.items(), key=lambda kv: (-kv[1], kv[0])):
        if w.lower() in lower:
            rejected.append((w, n, 'appears lowercase elsewhere — capital was positional'))
            continue
        if initial.get(w, 0) >= n:
            rejected.append((w, n, 'only ever sentence-initial'))
            continue
        ls = sorted(where[w])
        kept.append({'name': w, 'kind': classify(w), 'te': carry.get(w, ''), 'count': n,
                     'lessons': ','.join(ls[:6]) + ('...' if len(ls) > 6 else ''), 'notes': ''})

    with open(NAMES, 'w', encoding='utf-8', newline='') as f:
        wtr = csv.DictWriter(f, COLS, delimiter='\t', lineterminator='\n')
        wtr.writeheader()
        wtr.writerows(kept)

    by_kind = {}
    for r in kept:
        by_kind[r['kind']] = by_kind.get(r['kind'], 0) + 1
    done = sum(1 for r in kept if r['te'])
    print(f'{len(kept)} proper nouns kept, {len(rejected)} rejected '
          f'(was {len(kept) + len(rejected)} before filtering)')
    print('  by kind: ' + '  '.join(f'{k}={v}' for k, v in sorted(by_kind.items())))
    print(f'  transliterated so far: {done}/{len(kept)}')
    if args.rejected:
        print('\nrejected:')
        for w, n, why in sorted(rejected, key=lambda x: (-x[1], x[0])):
            print(f'  {w:<16}{n:>4}  {why}')


if __name__ == '__main__':
    main()
