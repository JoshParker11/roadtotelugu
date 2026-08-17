# -*- coding: utf-8 -*-
"""Find proper nouns in the source that the glossary does not yet classify.

    python3 tools/hp_terms.py --ch 1        # before translating a chapter
    python3 tools/hp_terms.py               # whole book

WHY
The glossary decides which words stay in Latin script. If a name reaches a translated paragraph
before it reaches the glossary, it gets handled ad hoc — anchored in one paragraph, transliterated
into Telugu script two paragraphs later — and that inconsistency is invisible until someone reads
the chapter end to end. Running this first turns the question into a checklist.

The list is derived from the text rather than from memory of the book, so it cannot quietly miss
a character who only appears twice.

HOW IT DECIDES
A capitalised word is only evidence of a proper noun when it appears capitalised *mid-sentence* —
otherwise every word that happens to start a sentence qualifies. Terms that never occur
mid-sentence are dropped, which is why "The", "And" and "Yes" do not appear in the output.
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from hp_segment import read_source, split_chapters

GLOSSARY = os.path.join(ROOT, 'translate', 'glossary.tsv')

# A capitalised run, allowing the lowercase particles that sit inside real names
# ("Mirror of Erised", "Ministry of Magic").
CAP = re.compile(r"\b[A-Z][A-Za-z'’\-]*(?:\s+(?:of|the|and)\s+[A-Z][A-Za-z'’\-]*"
                 r"|\s+[A-Z][A-Za-z'’\-]*)*")
# Capitalised for reasons that have nothing to do with being a name.
STOP = set("""A An The And But Or So Yes No Not I I'm I've I'll I'd It It's He She They We You
Your My His Her Their This That These Those There Here What Where When Why How Who Which If As
At In On To For From With Without Of By Up Out Down Over Under Then Than Now Well Oh Ah Er Look
Come Go Get Let Just Only Very Never Always Once Still Even Still Sir Madam Mr Mrs Ms Dear
One Two Three Four Five Six Seven Eight Nine Ten First Next Last Someone Something Nothing
Everyone Everything Anyone Anything Nobody Somebody All Both Each Every Some Any More Most
Perhaps Maybe Please Thanks Thank Sorry Right Left Okay OK Good Great Fine True False
Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June
July August September October November December Professor Uncle Aunt""".split())


def load_glossary():
    """Canonical terms plus their source-spelling variants — the scan hyphenates You-Know-Who
    three different ways, and all three mean the same anchor."""
    if not os.path.exists(GLOSSARY):
        return set()
    known = set()
    with open(GLOSSARY, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r.get('term'):
                known.add(r['term'].strip())
            for v in (r.get('variants') or '').split('|'):
                if v.strip():
                    known.add(v.strip())
    return known


def scan(text):
    """-> {term: (total, mid_sentence)}"""
    total, mid = collections.Counter(), collections.Counter()
    for m in CAP.finditer(text):
        t = m.group().strip().rstrip("'’")
        if len(t) < 3 or t in STOP:
            continue
        # Strip a possessive so Harry's and Harry are one term.
        t = re.sub(r"['’]s$", '', t)
        if not t or t in STOP:
            continue
        total[t] += 1
        before = text[max(0, m.start() - 2):m.start()]
        if not re.search(r'[.!?"“]\s*$|^$', before):
            mid[t] += 1
    return {t: (c, mid[t]) for t, c in total.items() if mid[t]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ch', type=int, help='one chapter only')
    ap.add_argument('--all', action='store_true', help='include terms already in the glossary')
    args = ap.parse_args()

    known = load_glossary()
    chapters = split_chapters(read_source())
    if args.ch:
        chapters = [c for c in chapters if c[0] == args.ch]
        if not chapters:
            raise SystemExit(f'no chapter {args.ch}')

    text = '\n'.join(p for _, _, body in chapters for p in body)
    found = scan(text)

    # A term is covered if it is in the glossary, or if every word of it is ("Professor
    # McGonagall's office" is not a new name), or if it is an English plural of something that
    # is — "Muggles" and "the Dursleys" are the same anchors as Muggle and Dursley, since the
    # translation takes Telugu's plural anyway (STYLE.md §4).
    def bases(w):
        """Both plural strips. "Muggles" -> Muggle (drop s), not Muggl (drop es); "witches" ->
        witche or witch. Trying both and accepting either is cheaper than being clever."""
        out = [w]
        if len(w) > 3:
            if w.endswith('es'):
                out += [w[:-1], w[:-2]]
            elif w.endswith('s'):
                out.append(w[:-1])
        return out

    def ok(w):
        # Lowercase joiners inside a phrase ("Lily and James Potter") are not names.
        return (w.lower() in ('and', 'of', 'the') or w in STOP
                or any(b in known for b in bases(w)))

    def covered(t):
        return any(b in known for b in bases(t)) or all(ok(w) for w in t.split())

    missing = {t: v for t, v in found.items() if not covered(t)}
    show = found if args.all else missing

    scope = f'chapter {args.ch}' if args.ch else 'the whole book'
    print(f'{len(found)} proper nouns in {scope}, {len(found) - len(missing)} already classified\n')
    if not show:
        print('  nothing unclassified — the glossary covers this chapter')
        return
    print(f'  {"term":<38}{"total":>6}{"mid":>5}')
    for t, (c, m) in sorted(show.items(), key=lambda kv: -kv[1][0]):
        print(f'  {t:<38}{c:>6}{m:>5}')
    print(f'\nAdd the real names to translate/glossary.tsv before translating {scope}.')
    print('Ignore the ones that are just sentence-initial capitals — the filter is not perfect.')


if __name__ == '__main__':
    main()
