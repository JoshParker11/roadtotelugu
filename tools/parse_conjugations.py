# -*- coding: utf-8 -*-
"""Parse the course's verb-conjugation PDF into a table we can check and republish.

    python3 tools/parse_conjugations.py [path-to-pdf]

The PDF (bhashafy.com, linked from course video 22) is 18 verbs over 36 pages: for each verb a
positive page and a negative page, each a grid of eight pronoun rows × three tense columns.

WHY POSITIONAL, AND WHY GAP-CLUSTERED
The text layer has no table structure and splits cells mid-word — "kūrchuṇṭānu" arrives as three
spans, `kūrchun-` / `ṭā` / `nu` — while reading order interleaves the columns. So cells are
rebuilt from coordinates.

The first attempt banded x into fixed column ranges and lost 42 cells, because the columns are
not in the same place on every page: on the Play page the present column starts at x=594, on the
Sit page at x=572, and a fixed boundary at 580 cuts one of them in half. Instead, spans in a row
are clustered by the *gap* between them — fragments of one cell sit within a few points of each
other, and there is a ~100pt gutter between cells — and each cluster is then assigned to whichever
tense header its left edge is nearest. That is layout-independent and recovers every cell.

WHAT IT IS FOR
This is the only authoritative full paradigm available. `verbs.js` was built from a different PDF
plus inference, so this is an independent second source covering 18 of its 35 verbs. Feeds
tools/check_conjugations.py, which diffs it against the generator.

Output: sources/raw/conjugations.tsv — verb_en, root, irregular, polarity, person, tense, form.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'sources', 'raw', 'conjugations.tsv')

ROWS = ['i', 'you', 'he', 'she', 'we', 'formal', 'it', 'they-n']
GRID_X = 380          # everything left of this is pronoun labels, not conjugations
GAP = 40              # a gutter wider than this starts a new cell


def spans(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip():
                    out.append({'y': s['bbox'][1], 'x0': s['bbox'][0], 'x1': s['bbox'][2],
                                'size': s['size'], 't': s['text']})
    return out


def header(sp):
    """Verb name, root, and whether the page is marked '* Irregular verb'."""
    big = [s for s in sp if s['size'] >= 22 and s['x0'] < 130]
    name = next((s['t'].strip() for s in sorted(big, key=lambda s: s['y']) if s['y'] < 30), '')
    root = next((s['t'].strip() for s in sorted(big, key=lambda s: s['y']) if 30 < s['y'] < 70), '')
    irregular = any('Irregular' in s['t'] for s in sp)
    return name, root, irregular


def tense_columns(sp):
    """{x_of_header: tense-name}. A header may cover two tenses ('PRESENT / PAST')."""
    cols = {}
    for s in sp:
        if s['y'] > 40 or s['x0'] < 300:
            continue
        txt = s['t'].upper()
        found = [t for t in ('PAST', 'PRESENT', 'FUTURE') if t in txt]
        if found:
            cols[s['x0']] = [t.lower() for t in found]
    return cols


def cells(sp, cols):
    """[(y, tense, text)] — one entry per reconstructed grid cell."""
    body = sorted((s for s in sp if s['x0'] >= GRID_X and s['y'] > 80),
                  key=lambda s: (s['y'], s['x0']))
    bands = []
    for s in body:
        if bands and abs(bands[-1][0] - s['y']) <= 6:
            bands[-1][1].append(s)
        else:
            bands.append((s['y'], [s]))

    out = []
    for y, items in bands:
        items.sort(key=lambda s: s['x0'])
        groups, cur = [], [items[0]]
        for prev, s in zip(items, items[1:]):
            if s['x0'] - prev['x1'] > GAP:
                groups.append(cur); cur = [s]
            else:
                cur.append(s)
        groups.append(cur)
        for g in groups:
            text = ''.join(s['t'] for s in g).strip()
            if not text or 'bhashafy' in text:      # the page footer sits inside the grid's x range
                continue
            # nearest tense header to this cell's left edge
            x0 = g[0]['x0']
            hx = min(cols, key=lambda h: abs(h - x0))
            out.append((y, cols[hx], text))
    return out


def parse(path):
    import pymupdf
    doc = pymupdf.open(path)
    rows, seen, problems = [], [], []
    for i in range(1, len(doc)):
        page = doc[i]
        sp = spans(page)
        name, root, irregular = header(sp)
        cols = tense_columns(sp)
        polarity = 'neg' if re.search(r"not|n’t|n't", page.get_text(), re.I) else 'pos'
        got = cells(sp, cols)
        seen.append((i + 1, name, root, polarity))

        # Group by the column a cell landed in, not by tense: uṇḍu's negative page merges past
        # and present under one "PRESENT / PAST" header, so a tense can belong to two columns.
        by_col = {}
        for y, tenses, text in got:
            by_col.setdefault(tuple(tenses), []).append(text)

        for tenses, vals in by_col.items():
            if len(vals) == len(ROWS):
                persons = ROWS
            elif len(vals) == len(ROWS) - 1:
                persons = [p for p in ROWS if p != 'formal']   # merged formal cell
            elif len(vals) <= 3:
                # Person-invariant column: one tall merged cell, whose text the PDF sometimes
                # breaks across y-bands (nērchuko-ḍam- / lēdu). Rejoin, then apply to every row.
                joined = vals[0]
                for part in vals[1:]:
                    joined += part if joined.endswith('-') else ' ' + part
                persons, vals = ROWS, [joined] * len(ROWS)
            else:
                problems.append(f'page {i+1} {name} {polarity} {"/".join(tenses)}: {len(vals)} cells')
                continue
            for tense in tenses:
                for person, form in zip(persons, vals):
                    rows.append([name, root, 'yes' if irregular else '', polarity,
                                 person, tense, form])
    return rows, seen, problems


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        '~/Downloads/Telugu+Verb+Conjugations+Bhashafy.pdf')
    if not os.path.exists(path):
        raise SystemExit(f'not found: {path}')
    rows, seen, problems = parse(path)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['verb_en', 'root', 'irregular', 'polarity', 'person', 'tense', 'form'])
        w.writerows(rows)

    verbs = sorted({(v[1], v[2]) for v in seen})
    print(f'{len(rows)} cells, {len(verbs)} verbs -> {os.path.relpath(OUT, ROOT)}')
    for en, root in verbs:
        n = sum(1 for r in rows if r[0] == en)
        print(f'    {en:<14}{root:<14}{n:>4} cells')
    if problems:
        print(f'\n  {len(problems)} unparsed:')
        for p in problems:
            print(f'    {p}')


if __name__ == '__main__':
    main()
