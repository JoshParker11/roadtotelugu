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
BRIEFS = os.path.join(ROOT, 'translate', 'briefs')

# Reading order for the brief: who, then where, then the invented vocabulary. Categories the
# glossary uses, in the order a listener meets them.
CAT_ORDER = ['person', 'place', 'institution', 'creature', 'spell', 'quidditch',
             'coined', 'culture', 'meaningful']
CAT_LABEL = {
    'person': 'People',
    'place': 'Places',
    'institution': 'Institutions and organisations',
    'creature': 'Creatures',
    'spell': 'Spells and incantations',
    'quidditch': 'Quidditch',
    'coined': 'Invented words',
    'culture': 'Wizarding culture',
    'meaningful': 'Names that carry a meaning',
}

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


def _bases(w):
    """Both plural strips. "Muggles" -> Muggle (drop s), not Muggl (drop es); "witches" ->
    witche or witch. Trying both and accepting either is cheaper than being clever."""
    out = [w]
    if len(w) > 3:
        if w.endswith('es'):
            out += [w[:-1], w[:-2]]
        elif w.endswith('s'):
            out.append(w[:-1])
    return out


def glossary_rows():
    """Every glossary row, plus a lookup from each source spelling to its row."""
    if not os.path.exists(GLOSSARY):
        return [], {}
    with open(GLOSSARY, encoding='utf-8', newline='') as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t') if (r.get('term') or '').strip()]
    by_spelling = {}
    for r in rows:
        by_spelling[r['term'].strip()] = r
        for v in (r.get('variants') or '').split('|'):
            if v.strip():
                by_spelling[v.strip()] = r
    return rows, by_spelling


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


def write_brief(num, found, known, by_spelling, bases):
    """A per-chapter list of what must stay in Latin script, to hand to a generator.

    WHY A PER-CHAPTER SUBSET AND NOT THE WHOLE GLOSSARY
    The glossary is the whole book: 158 terms, most of which a given chapter never mentions.
    A generator told to preserve 158 names while retelling one chapter has been handed a
    haystack, and the failure mode is not refusal — it is quietly keeping the famous ones and
    transliterating the rest, which is the exact inconsistency the glossary exists to prevent.
    So: only what this chapter actually contains, counted from its text.

    Two groups, kept apart on purpose. The classified ones carry the glossary's judgement.
    The detected ones are this script's capitalisation guess and include false positives —
    useful, because an unclassified name should still stay in English, but not something to
    present as settled.
    """
    os.makedirs(BRIEFS, exist_ok=True)
    groups = collections.defaultdict(list)
    detected = []
    for term, (total, _mid) in sorted(found.items(), key=lambda kv: -kv[1][0]):
        row = by_spelling.get(term) or next(
            (by_spelling[b] for b in bases(term) if b in by_spelling), None)
        if row:
            canon = row['term'].strip()
            cat = (row.get('category') or '').strip() or 'meaningful'
            if not any(canon == t for t, _ in groups[cat]):
                groups[cat].append((canon, total))
        elif not all(w.lower() in ('and', 'of', 'the') or w in STOP for w in term.split()):
            detected.append((term, total))

    n_class = sum(len(v) for v in groups.values())
    out = []
    add = out.append
    add(f'# Chapter {num} — keep these in English')
    add('')
    add(f'{n_class} terms the glossary classifies, {len(detected)} more detected in the text.')
    add('Generated by `python3 tools/hp_terms.py --ch %d --brief` from the chapter itself, so it'
        % num)
    add('lists only what this chapter actually mentions.')
    add('')
    add('## Instruction')
    add('')
    add('> Narrate in Telugu. Every name below stays in English, in Latin script, spelled')
    add('> exactly as written — people, places, institutions, creatures, spells, Quidditch')
    add('> terms and invented words. Do not translate them, do not transliterate them into')
    add('> Telugu script, and do not substitute a Telugu equivalent. Everything else should be')
    add('> natural spoken Telugu.')
    add('')
    for cat in CAT_ORDER:
        if not groups.get(cat):
            continue
        add(f'## {CAT_LABEL.get(cat, cat.title())}')
        add('')
        add(', '.join(t for t, _ in sorted(groups[cat], key=lambda x: -x[1])))
        add('')
    if detected:
        add('## Also detected, unverified')
        add('')
        add('Capitalised mid-sentence in this chapter but not in the glossary. Real names here')
        add('should stay in English too; the list also catches false positives, so read it'
            ' before pasting.')
        add('')
        add(', '.join(t for t, _ in detected))
        add('')
    path = os.path.join(BRIEFS, f'ch{num:02d}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    return path, n_class, len(detected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ch', type=int, help='one chapter only')
    ap.add_argument('--all', action='store_true', help='include terms already in the glossary')
    ap.add_argument('--brief', action='store_true',
                    help='write translate/briefs/chNN.md — the keep-in-English list for a '
                         'generator. With no --ch, writes all 17.')
    args = ap.parse_args()

    known = load_glossary()
    chapters = split_chapters(read_source())
    if args.ch:
        chapters = [c for c in chapters if c[0] == args.ch]
        if not chapters:
            raise SystemExit(f'no chapter {args.ch}')

    if args.brief:
        _rows, by_spelling = glossary_rows()
        for num, _title, body in chapters:
            found_ch = scan('\n'.join(body))
            path, n_class, n_det = write_brief(num, found_ch, known, by_spelling, _bases)
            print(f'  ch{num:02d}  {n_class:3d} classified  {n_det:3d} detected  '
                  f'-> {os.path.relpath(path, ROOT)}')
        return

    text = '\n'.join(p for _, _, body in chapters for p in body)
    found = scan(text)

    # A term is covered if it is in the glossary, or if every word of it is ("Professor
    # McGonagall's office" is not a new name), or if it is an English plural of something that
    # is — "Muggles" and "the Dursleys" are the same anchors as Muggle and Dursley, since the
    # translation takes Telugu's plural anyway (STYLE.md §4).
    bases = _bases

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
