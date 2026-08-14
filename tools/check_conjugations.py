# -*- coding: utf-8 -*-
"""Diff the course's conjugation PDF against the Verb Lab generator.

    python3 tools/parse_conjugations.py && python3 tools/check_conjugations.py

GRAMMAR_LAB/data/verbs.js was built from a different PDF plus my own inference, and until week 2
nothing in it had been checked against an authoritative source. The bhashafy tables cover 18 of
its 35 verbs across three tenses, two polarities and eight persons — the largest independent
check available.

COMPARE ROWS, NOT CELLS
A first pass compared cell against cell and produced 375 "disagreements", nearly all of them one
of four systematic things wearing 375 different faces. A Telugu verb form is a stem plus an
ending, and those two fail independently: a wrong stem breaks all six cells of a row while every
ending stays perfect, which is a completely different finding from one ending being wrong. So
each (verb, tense, polarity) row is split into stem and endings, and the two are compared apart.

The stem is the text before the PDF's first hyphen, and the longest common prefix of the six
generated forms. What remains is the ending.

NORMALISATION — all notation rather than pronunciation:
  - a nasal before a retroflex is retroflex (our convention; the PDF writes plain n)
  - word-final anusvara is ṁ here, m there
  - the PDF joins `ḍam-lēdu` where we space it
  - the PDF's hyphen swallows the linking vowel — `u` in āḍ-tunnānu, `a` in āḍ-lēdu — so each
    hyphen is matched as an optional vowel

Two known-benign differences are absorbed rather than reported:
  - **we**: PDF -āmu (manamu) vs our -āṁ (manaṁ), a register scope choice already on record in
    review/verb-lab-audit.md.
  - **corrupt**: four pages were made by find-and-replacing "āḍu" in the Play page, and the
    replace ran over the body text — on the Drink page the pronoun Vāḍu prints as "Vtāgu" and the
    he-row ending -āḍu prints as "-tāgu". A defect in the source, not a disagreement.
"""
import csv, json, os, re, subprocess
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, 'sources', 'raw', 'conjugations.tsv')

VERB_ID = {
    'āḍu': 'adu', 'tāgu': 'tagu', 'cheppu': 'cheppu', 'pāḍu': 'padu', 'māṭlāḍu': 'matladu',
    'chēyi': 'cheyi', 'rāyi': 'rayi', 'kūrcho': 'kurcho', 'paḍuko': 'paduko',
    'nērchuko': 'nerchuko', 'veḷḷu': 'vellu', 'rā/vach': 'ra', 'ivvu': 'ivvu',
    'nērpinchu': 'nerpinchu', 'prēminchu': 'preminchu', 'tinu': 'tinu', 'unḍu': 'undu',
    'po': None,          # pō is taught in Lesson 7 but is not a Verb Lab headword
}
PERSONS = ['i', 'you', 'he', 'she', 'we', 'formal']
PERSON_IX = {p: i for i, p in enumerate(PERSONS)}
FORM_ID = {('past', 'pos'): 'past', ('present', 'pos'): 'present', ('future', 'pos'): 'future',
           ('past', 'neg'): 'negPast', ('present', 'neg'): 'negPresent',
           ('future', 'neg'): 'negFuture'}
VOWEL = '[aāiīuūeēoō]'


def generated():
    js = r'''
      const fs=require('fs');
      const src=fs.readFileSync('GRAMMAR_LAB/data/verbs.js','utf8').replace(/if \(typeof module[\s\S]*$/,'');
      const VERBS=(0,eval)(src+'; VERBS');
      const e=require('./GRAMMAR_LAB/data/engine.js');
      const out={};
      for(const v of VERBS) for(const f of ['past','present','future','negPast','negPresent','negFuture'])
        for(let i=0;i<6;i++){const c=e.conjugate(v,f,i); if(c) out[v.id+'|'+f+'|'+i]=c[0];}
      console.log(JSON.stringify(out));
    '''
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(r.stderr)
    return json.loads(r.stdout)


def fold(s):
    s = re.sub(r'n(?=[ṭḍ])', 'ṇ', (s or '').strip().lower())
    return s.replace('ṁ', 'm').replace(' ', '')


def same(pdf, ours):
    """Equal once each hyphen is read as an elided linking vowel."""
    pat = ''.join(VOWEL + '?' if c == '-' else re.escape(c) for c in fold(pdf))
    return re.fullmatch(pat, fold(ours)) is not None


def implied_stem(pdf_end, ours):
    """If our form ends with the PDF's ending, return the stem it implies; else None.
    The leading hyphen is an elided linking vowel, so it is matched as an optional vowel."""
    pat = ''.join(VOWEL + '?' if c == '-' else re.escape(c) for c in fold(pdf_end))
    m = re.search(pat + '$', fold(ours))
    return fold(ours)[:m.start()] if m else None


def uncorrupt(cell, root):
    """Undo the page's find-and-replace of āḍu -> <root> in the ending, not the stem."""
    if '-' not in cell:
        return cell
    stem, rest = cell.split('-', 1)
    return stem + '-' + re.sub(re.escape(root.lower()), 'āḍu', rest, flags=re.I)


def main():
    if not os.path.exists(SRC):
        raise SystemExit('run tools/parse_conjugations.py first')
    gen = generated()
    rows = list(csv.DictReader(open(SRC, encoding='utf-8'), delimiter='\t'))

    groups, roots, skipped = defaultdict(dict), {}, set()
    for r in rows:
        vid = VERB_ID.get(r['root'].lower(), 'UNMAPPED')
        if vid in (None, 'UNMAPPED'):
            skipped.add(r['root']); continue
        if r['person'] not in PERSON_IX:
            continue                                  # the avi row the Verb Lab does not model
        roots[vid] = r['root']
        groups[(vid, FORM_ID[(r['tense'], r['polarity'])])][r['person']] = r['form']

    clean, stem_only, findings = [], [], []
    n_cells = n_ok = 0
    for (vid, form), cells in sorted(groups.items()):
        lab = {p: gen.get(f'{vid}|{form}|{PERSON_IX[p]}') for p in cells}
        if not all(lab.values()):
            continue
        stem_hits, ending_diffs = [], []
        for p in PERSONS:
            if p not in cells:
                continue
            n_cells += 1
            cell = uncorrupt(cells[p], roots[vid])
            target = lab[p]
            if same(cell, target) or (p == 'we' and same(cell, re.sub(r'ṁ$', 'mu', target))):
                n_ok += 1
                continue
            # the ending is what follows the PDF's first hyphen; does our form end the same way?
            pdf_end = cell.split('-', 1)[1] if '-' in cell else cell
            st = implied_stem(pdf_end, target)
            if st is None and p == 'we':
                st = implied_stem(pdf_end, re.sub(r'ṁ$', 'mu', target))
            if st is not None:
                stem_hits.append((p, cell.split('-', 1)[0], st))
            else:
                ending_diffs.append((p, cell, target))

        if not stem_hits and not ending_diffs:
            clean.append((vid, form))
            continue
        if stem_hits and not ending_diffs:
            pdf_s = stem_hits[0][1]
            lab_s = stem_hits[0][2]
            consistent = len({h[2] for h in stem_hits}) == 1
            stem_only.append((vid, form, pdf_s, lab_s, len(stem_hits), consistent))
        else:
            findings.extend((vid, form, p, c, o) for p, c, o in ending_diffs)

    print(f'{n_cells} comparable cells, {len(groups)} verb×tense rows, 18 verbs')
    print(f'  {n_ok} cells agree once notation and the manaṁ/manamu split are normalised')
    print(f'  {len(clean)} of {len(groups)} rows fully clean')

    print(f'\n  {len(stem_only)} rows where only the STEM differs — every ending agrees:')
    for vid, form, ps, ls, n, ok in stem_only:
        note = '' if ok else '   (stem varies by person)'
        print(f'    {vid:<11}{form:<12}pdf {ps + "-":<14}lab {ls + "-":<16}{n} cells{note}')

    print(f'\n  {len(findings)} cells where an ENDING differs:')
    for vid, form, p, cell, ours in findings:
        print(f'    {vid:<11}{form:<12}{p:<8}pdf {cell:<22}lab {ours}')
    if skipped:
        print(f'\n  not compared: {", ".join(sorted(skipped))}')


if __name__ == '__main__':
    main()
