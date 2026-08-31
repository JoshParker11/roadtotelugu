# -*- coding: utf-8 -*-
"""Harvest the book's own VOCABULARY lists — its published gloss for every word it teaches.

    python3 tools/ic_vocab.py --report        # what would be harvested, per lesson
    python3 tools/ic_vocab.py                 # -> intensive/raw/vocab.tsv

Every lesson ends with a VOCABULARY section: a two-column list of the words it introduced, each
with an English gloss the publisher wrote. That is a checked bilingual glossary for the whole
book, sitting in the same PDFs the dialogues came from, and it is the answer to the reader
showing 3,251 words with no meaning when all 64 lessons are loaded.

WHY THIS BEATS ANYTHING GENERATED
The alternative was writing thousands of definitions from context. These are the book's own,
for exactly the words the book chose to teach, in the order it teaches them. Nothing is
inferred — the only step that can go wrong is reading the page, and that is measured.

THE LAYOUT, AND WHY IT IS POSITIONAL AGAIN
A headword sits at the column's left edge and its gloss a couple of points below and about
eighty to the right, with two columns per page:

    ṁæü*Ææÿ                     JṁóüÝëÇ            <- headwords, columns 1 and 2
        curry; vegetable            at once; ...   <- glosses

Reading order interleaves the columns, so the pairing is by coordinate: the gloss is the
nearest English run below-right of a headword and still inside that column.

THE DEVANAGARI TRAP
Each entry also carries a Devanagari transliteration, and Devanagari legacy fonts are
ASCII-heavy, so a naive "the non-Telugu run is the English" picks up `_m Îm§` as a gloss. A
gloss has to look like English — mostly ASCII letters, with real words in it.
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

import pymupdf
from ic_extract import lines_of, classify_fonts, lesson_files, PDFS, HEADINGS, STD
from ic_ocr import ZOOM, PAD, PSM, OEM, LANG, have_tesseract

OUT = os.path.join(ROOT, 'intensive', 'raw', 'vocab.tsv')
# No fixed column width. Unit I sets FOUR columns — Telugu, Devanagari, romanization, English —
# which puts the gloss 152pt from its headword, while the later two-column lessons put it 48pt
# away. A cap tuned to either one silently drops the other, and 150 dropped every lesson 1-6
# entry. Nearest-to-the-right inside the y-window handles both, because the competing column's
# gloss is always much further right than the correct one.
MAX_GLOSS_DX = 260.0
Y_WINDOW = 14.0          # a gloss sits a couple of points below its headword, never above by much
ENGLISHY = re.compile(r'^[\x20-\x7e]+$')


def looks_english(s):
    s = s.strip()
    if len(s) < 2 or not ENGLISHY.match(s):
        return False
    letters = sum(c.isalpha() for c in s)
    return letters >= 2 and letters / len(s) > 0.5


def vocab_boxes(doc):
    """(page, bbox, gloss) for every headword in a VOCABULARY section."""
    L = lines_of(doc)
    romf, telf = classify_fonts(L)
    # the section runs from the VOCABULARY heading to the next heading, or the end
    start = end = None
    for i, (pno, y, x0, x1, fonts, txt) in enumerate(L):
        t = txt.strip().upper().rstrip('.: ')
        if t.startswith('VOCABULARY') and start is None:
            start = i
        elif start is not None and t in HEADINGS and not t.startswith('VOCABULARY'):
            end = i
            break
    if start is None:
        return []
    section = L[start + 1:end]

    heads, glosses = [], []
    for pno, y, x0, x1, fonts, txt in section:
        if set(fonts) & telf:
            heads.append((pno, y, x0, x1, txt))
        elif all(f.startswith(STD) for f in fonts) and looks_english(txt):
            # THE FONT IS THE TEST, NOT THE CHARACTERS.
            # Each entry carries three non-Telugu runs: a Devanagari transliteration, a
            # romanization, and the English gloss. The first two are ASCII-heavy — legacy
            # Devanagari is nothing but ASCII punctuation, and a romanization IS Latin — so
            # "looks like English" picked `balla` and `A{X` as the meaning of బల్ల. Only the
            # English is set in a standard family; the other two are custom subset fonts.
            glosses.append((pno, y, x0, txt.strip()))

    out = []
    for pno, y, x0, x1, txt in heads:
        near = [g for g in glosses
                if g[0] == pno and -2.0 <= g[1] - y <= Y_WINDOW and x0 < g[2] < x0 + MAX_GLOSS_DX]
        if not near:
            continue
        near.sort(key=lambda g: (g[2] - x0))        # the nearest gloss to the right wins
        out.append((pno, (x0, y, x1, y + 13.0), near[0][3]))
    return out


def ocr_head(doc, page, box, tmp):
    from PIL import Image
    import subprocess
    pix = doc[page].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
    png = os.path.join(tmp, 'p.png')
    pix.save(png)
    img = Image.open(png)
    crop = (max(0, int((box[0] - PAD) * ZOOM)), max(0, int((box[1] - PAD) * ZOOM)),
            min(img.width, int((box[2] + PAD) * ZOOM)), min(img.height, int((box[3] + PAD) * ZOOM)))
    if crop[2] - crop[0] < 8 or crop[3] - crop[1] < 8:
        return ''
    c = os.path.join(tmp, 'c.png')
    img.crop(crop).save(c)
    p = subprocess.run(['tesseract', c, 'stdout', '-l', LANG, '--psm', PSM, '--oem', OEM],
                       capture_output=True, text=True)
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--num', type=int)
    ap.add_argument('--pdfs', default=PDFS)
    args = ap.parse_args()
    if not args.report and not have_tesseract():
        sys.exit('tesseract not on PATH — brew install tesseract tesseract-lang')

    import tempfile
    rows, tot = [], 0
    print(f'{"lesson":>6} {"entries":>8}')
    for num, path in lesson_files(args.pdfs):
        if args.num and num != args.num:
            continue
        doc = pymupdf.open(path)
        boxes = vocab_boxes(doc)
        tot += len(boxes)
        print(f'{num:>6} {len(boxes):>8}')
        if args.report:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            for page, box, gloss in boxes:
                te = ocr_head(doc, page, box, tmp)
                if te:
                    rows.append({'lesson': num, 'te': te, 'en': gloss})
    print(f'\n{tot} vocabulary entries across the book')
    if args.report:
        return
    if args.num:
        # --num is for inspecting one lesson; writing the file from it would leave vocab.tsv
        # holding that lesson alone, which is how a full harvest gets thrown away.
        print('--num: nothing written (it would truncate the file to one lesson)')
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, delimiter='\t', fieldnames=['lesson', 'te', 'en'])
        w.writeheader(); w.writerows(rows)
    print(f'{len(rows)} read -> {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
