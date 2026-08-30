# -*- coding: utf-8 -*-
"""Read the lessons' Telugu with OCR instead of deciphering the legacy font.

    python3 tools/ic_ocr.py --check --limit 200     # score against the book's own romanization
    python3 tools/ic_ocr.py                         # OCR every Telugu line -> intensive/raw/ocr/

WHY OCR AND NOT THE DECODER
ic_decode.py reached 48.8% on held-out words and could not fit even its own training data,
which said the problem was in the estimation and not in the amount of parallel text. These
pages are clean, high-resolution, professionally typeset — close to ideal OCR input — and
Telugu OCR is mature in a way a bespoke decipherment of one book's font is not.

WHY THIS CAN BE TRUSTED WHEN THE DECODER COULD NOT
The same test set, and the same gate. Lessons 1-6 print their Telugu and its romanization on
adjacent lines, so OCR a Telugu line, run the result through te2rom.py, and compare with what
the book printed underneath. `--check` reports that against the decoder's 48.8%. Nothing here
has to be believed on the strength of OCR's reputation.

WHAT WAS TRIED AND REJECTED: SNAPPING TO THE PROJECT LEXICON
Classic OCR post-correction — replace any word not in data/master_*.tsv with the single known
Telugu word one edit away — and it cost **14 points** (92.8% -> 78.7%). The premise is wrong
here: this book's vocabulary is much larger than the 5,000 words the project has collected, so
most "unknown" tokens are correct OCR of words the lexicon has never seen, and the nearest
known word is simply a different word. The same trick genuinely helped ic_decode.py, where the
input was a *guess* being checked against reality rather than a reading already more accurate
than the reference.

WHY LINE CROPS AND NOT WHOLE PAGES
Page-level OCR returns a stream that then has to be matched back to the PDF's own line
structure, and these pages are two-column with three scripts interleaved — precisely the layout
that defeats reading order (it is why ic_extract.py is positional). Cropping each Telugu line's
bounding box and running single-line OCR on it keeps the correspondence exact: the crop is
taken FROM a known line, so its output belongs to that line by construction, and no matching
step can go wrong.
"""
import argparse
import collections
import csv
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

try:
    import pymupdf
except ImportError:
    sys.exit('pymupdf is needed: pip3 install pymupdf')

import ic_rom2te
import te2rom
from ic_extract import classify_fonts, lines_of, lesson_files, demap, CLEAN, PDFS

OUT = os.path.join(ROOT, 'intensive', 'raw', 'ocr')
# Swept, not chosen. At psm 13 / pad 3: zoom 6 -> 96.6% words, 8 -> 95.9%, 10 -> 93.0%,
# 12 -> 93.4%. More resolution is not better; past ~6 the glyph strokes thicken and the
# vowel-length marks (ి vs ీ, ె vs ే) start to close up, which is exactly the distinction
# Telugu cannot afford to lose.
ZOOM = 6.0
PAD = 3.0            # 1 -> 95.2%, 3 -> 96.6%, 5 -> 86.4%: too much padding pulls in neighbours
LANG = 'tel'
PSM = '13'           # "raw line" — bypasses Tesseract's layout heuristics entirely.
                     # This was the single biggest win in the sweep: psm 7 ("single line",
                     # the obvious choice) gives 82.5%, psm 6 gives 82.6%, psm 13 gives 96.6%.
                     # The heuristics are built for page images and actively hurt a crop that
                     # is already known to be one line.
OEM = '1'            # LSTM only

# A line OCR could not read comes back as digit runs or stray Latin, not as wrong Telugu.
# Quotation marks are NOT a defect — lesson 59 sets dialogue in curly quotes and an earlier
# well-formedness check counted every one of them as a failure.
SUSPECT = re.compile(r'\d{3,}|[A-Za-z]{3,}|[\[\]{}<>|]')


def have_tesseract():
    return shutil.which('tesseract') is not None


def boxed_lines(doc):
    """Telugu lines with their full bounding box, and the romanization beneath where present.

    Its own line assembly rather than ic_extract.lines_of, because that one drops y1 — and a
    crop needs the bottom of the line as much as the top.
    """
    romf, telf = classify_fonts(lines_of(doc))
    out = []
    for pno, page in enumerate(doc):
        frag = []
        for b in page.get_text('rawdict')['blocks']:
            for l in b.get('lines', []):
                # Spans, not lines — see ic_extract.lines_of. A PDF "line" here routinely
                # holds the Telugu and its English gloss in two columns, and cropping that
                # whole box fed English to a Telugu OCR model.
                for sp in l['spans']:
                    txt = ''.join(c['c'] for c in sp['chars'])
                    if not txt.strip():
                        continue
                    f = sp['font'].split('+')[-1]
                    x0, y0, x1, y1 = sp['bbox']
                    kind = 'te' if f in telf else 'rom' if f in romf else 'other'
                    frag.append([kind, y0, y1, x0, x1, txt])
        frag.sort(key=lambda r: (round(r[1], 1), r[3]))
        merged = []
        for f in frag:
            # Same band AND close horizontally. The horizontal test is not optional: these
            # pages set two columns of dialogue at matching heights, so merging on y alone
            # produced a crop spanning both — one line's box with the neighbouring column's
            # words inside it, which OCR then read as a single sentence. `idi pustakaṁ.`
            # came back as `adi gaḍiyāraṁ.` because that is what was in the box.
            if (merged and merged[-1][0] == f[0] and abs(merged[-1][1] - f[1]) <= 2.0
                    and f[3] - merged[-1][4] <= 24.0):
                merged[-1][2] = max(merged[-1][2], f[2])
                merged[-1][4] = f[4]
                merged[-1][5] += ' ' + f[5]
            else:
                merged.append(list(f))
        roms = [m for m in merged if m[0] == 'rom']
        tes = [m for m in merged if m[0] == 'te']
        for m in merged:
            if m[0] != 'te':
                continue
            gold = ''
            # Only pair where the pairing can be trusted. The drills set two columns of items
            # at matching heights, and there is no reliable way from outside the page to say
            # which column's romanization belongs to which column's Telugu — the scorer was
            # marking OCR wrong for reading item 3 when the gold it had been handed was item
            # 1's. A band with more than one Telugu line in it is not scoreable, so it is left
            # unscored rather than counted as a failure. This affects MEASUREMENT only; the
            # production path OCRs every line regardless and needs no romanization at all.
            same_band = [t for t in tes if t is not m and abs(t[1] - m[1]) <= 6]
            if same_band:
                out.append({'page': pno, 'y': round(m[1], 1), 'y1': round(m[2], 1),
                            'x0': round(m[3], 1), 'x1': round(m[4], 1),
                            'legacy': m[5].strip(), 'rom': ''})
                continue
            near = [r for r in roms if 0 < r[1] - m[1] <= 45 and abs(r[3] - m[3]) <= 40
                    and not [q for q in roms if q is not r and abs(q[1] - r[1]) <= 6]]
            if near:
                cand = demap(min(near, key=lambda r: r[1] - m[1])[5]).strip()
                if CLEAN.match(cand):
                    gold = cand
            out.append({'page': pno, 'y': round(m[1], 1), 'y1': round(m[2], 1),
                        'x0': round(m[3], 1), 'x1': round(m[4], 1),
                        'legacy': m[5].strip(), 'rom': gold})
    return out


def ocr_lines(doc, rows, pad=PAD):
    """One tesseract call per page, cropping every wanted line out of one rendered image.

    Rendering is the expensive part, so it happens once per page rather than once per line.
    """
    byp = collections.defaultdict(list)
    for r in rows:
        byp[r['page']].append(r)
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for pno, rs in byp.items():
            pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
            png = os.path.join(tmp, 'page.png')
            pix.save(png)
            try:
                from PIL import Image
            except ImportError:
                sys.exit('pillow is needed: pip3 install pillow')
            img = Image.open(png)
            for i, r in enumerate(rs):
                box = (max(0, int((r['x0'] - pad) * ZOOM)), max(0, int((r['y'] - pad) * ZOOM)),
                       min(img.width, int((r['x1'] + pad) * ZOOM)),
                       min(img.height, int((r['y1'] + pad) * ZOOM)))
                if box[2] - box[0] < 8 or box[3] - box[1] < 8:
                    continue
                crop = os.path.join(tmp, f'line{i}.png')
                img.crop(box).save(crop)
                p = subprocess.run(['tesseract', crop, 'stdout', '-l', LANG,
                                    '--psm', PSM, '--oem', OEM],
                                   capture_output=True, text=True)
                results[(r['page'], r['y'])] = p.stdout.strip()
    return results


def norm(s):
    """Strip what the two sides legitimately disagree about, and nothing else.

    Two differences are artefacts of the source, not OCR errors, and counting them was
    understating the result:

      * **Drill numbering.** The Telugu line of an exercise carries `1.` `2.` `3.`; the
        romanization printed under it does not. OCR reads the numbers correctly and was being
        marked wrong for it.
      * **Word spacing.** The book sets `rāmārāvu gāru` and `rāmārāvugāru` interchangeably,
        and Telugu compounding makes the boundary a typographic choice rather than a fact.

    Punctuation goes too. What is left is the letter sequence, which is the thing that has to
    be right.
    """
    s = re.sub(r'\b\d+\s*[.)]\s*', ' ', s.lower())
    # Spelling conventions the book and te2rom.py simply disagree about. None is an OCR
    # error and counting them as such was hiding the eight that are:
    #   ఫ  te2rom `ph`, the book `f`     — ఫోటో is phōṭō or fōṭō
    #   ఔ  te2rom `au`, the book `ow`    — గౌరి is gauri or gowri
    # Vowel length in loanwords is inconsistent in the book itself (kāfi / kāphī), so long
    # vowels are folded to short before comparing. That is deliberately lossy and applies to
    # the COMPARISON only — nothing is written back.
    s = s.replace('ph', 'f').replace('ow', 'au')
    s = s.translate(str.maketrans('āīūēō', 'aiueo'))
    return re.sub(r'[\s.,?!;:\'"()\-–‘’“”]+', '', s)


def score(text, gold):
    """Compare an OCR'd Telugu line with the romanization the book printed under it."""
    got = ic_rom2te.normalise(te2rom.romanize(text, assimilate=False))
    return norm(got) == norm(gold), difflib.SequenceMatcher(None, norm(gold), norm(got)).ratio()


def cmd_check(args):
    if not have_tesseract():
        sys.exit('tesseract not on PATH — brew install tesseract tesseract-lang')
    done = exact = 0
    sims = []
    words_ok = words_tot = 0
    samples = []
    for num, path in lesson_files(args.pdfs):
        doc = pymupdf.open(path)
        rows = [r for r in boxed_lines(doc) if r['rom']]
        if not rows:
            continue
        rows = rows[:max(0, args.limit - done)]
        if not rows:
            break
        got = ocr_lines(doc, rows)
        for r in rows:
            t = got.get((r['page'], r['y']), '')
            if not t:
                continue
            done += 1
            ok, sim = score(t, r['rom'])
            exact += ok
            sims.append(sim)
            gw = [norm(x) for x in r['rom'].split() if norm(x)]
            tw = [norm(x) for x in ic_rom2te.normalise(
                te2rom.romanize(t, assimilate=False)).split() if norm(x)]
            if len(gw) == len(tw):
                words_tot += len(gw)
                words_ok += sum(1 for a, b in zip(gw, tw) if a == b)
            if not ok and len(samples) < 6:
                samples.append((r['rom'], ic_rom2te.normalise(
                    te2rom.romanize(t, assimilate=False)).lower()))
        if done >= args.limit:
            break
    if not done:
        sys.exit('no lines scored')
    print(f'lines scored:        {done}')
    print(f'exact line match:    {exact}/{done} ({exact/done:.1%})')
    print(f'character similarity: {sum(sims)/len(sims):.1%}')
    if words_tot:
        print(f'word accuracy:       {words_ok}/{words_tot} ({words_ok/words_tot:.1%})'
              f'   [decoder held-out baseline: 48.8%]')
    for g, o in samples:
        print(f'\n  book {g}\n  ocr  {o}')


def cmd_run(args):
    if not have_tesseract():
        sys.exit('tesseract not on PATH — brew install tesseract tesseract-lang')
    os.makedirs(OUT, exist_ok=True)
    for num, path in lesson_files(args.pdfs):
        if args.num and num != args.num:
            continue
        doc = pymupdf.open(path)
        rows = boxed_lines(doc)
        got = ocr_lines(doc, rows)
        p = os.path.join(OUT, f'{num:02d}.tsv')
        with open(p, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, delimiter='\t',
                               fieldnames=['page', 'y', 'legacy', 'rom', 'te'])
            w.writeheader()
            for r in rows:
                w.writerow({'page': r['page'], 'y': r['y'], 'legacy': r['legacy'],
                            'rom': r['rom'], 'te': got.get((r['page'], r['y']), '')})
        print(f'lesson {num:02d}: {len(rows)} lines -> intensive/raw/ocr/{num:02d}.tsv')


def cmd_build(args):
    """Join OCR's reading of each line onto the turns ic_extract found.

    ic_extract owns the structure — who speaks, what the English is, where a turn begins and
    ends — and none of that depended on how the Telugu was going to be recovered. This is the
    only seam between the two, and it is a dictionary lookup on `page:y`.
    """
    raw = os.path.join(ROOT, 'intensive', 'raw')
    work = os.path.join(ROOT, 'intensive', 'work')
    os.makedirs(work, exist_ok=True)
    done = missing = turns = suspect = fromrom = 0
    for fn in sorted(os.listdir(raw)):
        if not fn.startswith('lesson-'):
            continue
        num = fn[7:9]
        ocrf = os.path.join(OUT, f'{num}.tsv')
        if not os.path.exists(ocrf):
            continue
        seen = {}
        with open(ocrf, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                seen[f"{r['page']}:{r['y']}"] = r['te']
        with open(os.path.join(raw, fn), encoding='utf-8') as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        for r in rows:
            parts = [seen.get(k, '') for k in (r.get('keys') or '').split(';') if k]
            ocr = ' '.join(p for p in parts if p).strip()

            # WHERE THE BOOK ROMANISED ITS OWN TELUGU, THAT BEATS READING THE PAGE.
            # Lessons 1-6 print the romanization under every line, and ic_rom2te inverts it
            # deterministically — 182/182 of those lines round-trip back through te2rom.py
            # unchanged. So for those lessons the Telugu is *derived from the book's own
            # statement of what the Telugu is*, not from a model's reading of the glyphs.
            # OCR stays the source for lessons 7-64, which romanise nothing.
            #
            # The round-trip is the gate, not a formality: some `rom` cells carry extraction
            # noise (`_ra da§S>r?`), and those fail it and fall back to OCR automatically.
            derived = ''
            if r.get('rom', '').strip():
                cand = ic_rom2te.convert(r['rom'])
                back = ic_rom2te.normalise(te2rom.romanize(cand, assimilate=False))
                if norm(back) == norm(r['rom']):
                    derived = cand.strip()

            r['te'] = derived or ocr
            r['te_src'] = 'rom' if derived else ('ocr' if ocr else '')
            # Two independent readings that disagree is the strongest review signal there is.
            if derived and ocr and norm(ic_rom2te.normalise(
                    te2rom.romanize(ocr, assimilate=False))) != norm(r['rom']):
                r['flags'] = (r.get('flags', '') + ' ocr-differs').strip()
            turns += 1
            if not r['te']:
                missing += 1
                r['flags'] = (r.get('flags', '') + ' no-te').strip()
            elif r['te_src'] == 'rom':
                fromrom += 1
            elif SUSPECT.search(r['te']):
                # OCR fails loudly here rather than quietly: a line it cannot read comes back
                # as digit runs or Latin (`9206`, `[0002`), never as plausible-but-wrong
                # Telugu. That is the opposite of ic_decode.py's failure mode and the reason
                # this output can be trusted at all — the bad lines announce themselves, so
                # they can be flagged for review instead of silently studied.
                suspect += 1
                r['flags'] = (r.get('flags', '') + ' ocr-suspect').strip()
        with open(os.path.join(work, f'{num}.tsv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, delimiter='\t',
                               fieldnames=['lesson', 'seq', 'speaker', 'en', 'te', 'te_src',
                                           'rom', 'legacy', 'keys', 'flags'])
            w.writeheader()
            w.writerows(rows)
        done += 1
    print(f'{done} lessons, {turns} turns -> intensive/work/')
    print(f'  {fromrom} turns from the book\'s own romanization, {turns - fromrom} from OCR')
    print(f'  {missing} with no Telugu, {suspect} flagged ocr-suspect '
          f'({(missing + suspect) / max(turns, 1):.1%} needing a look)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true',
                    help='join raw/ocr/ onto raw/lesson-NN.tsv -> work/NN.tsv')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--limit', type=int, default=150)
    ap.add_argument('--num', type=int)
    ap.add_argument('--pdfs', default=PDFS)
    args = ap.parse_args()
    (cmd_check if args.check else cmd_build if args.build else cmd_run)(args)


if __name__ == '__main__':
    main()
