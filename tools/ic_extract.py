# -*- coding: utf-8 -*-
"""Pull the dialogues out of "An Intensive Course in Telugu" (64 lesson PDFs).

    python3 tools/ic_extract.py --report          # what is there, nothing written
    python3 tools/ic_extract.py                   # write intensive/raw/lesson-NN.tsv
    python3 tools/ic_extract.py --num 7           # one lesson
    python3 tools/ic_extract.py --pairs           # the aligned corpus, for ic_decode.py

Reads:  the lesson PDFs (third-party, gitignored — see intensive/README.md)
Writes: intensive/raw/lesson-NN.tsv   one row per speaker turn
        intensive/raw/pairs.tsv       (--pairs) legacy<TAB>roman, the decoder's evidence

WHAT THESE PDFs ACTUALLY CONTAIN, WHICH IS NOT WHAT IT LOOKS LIKE
The Telugu is set in a legacy pre-Unicode font with no ToUnicode map, so it does not extract as
Telugu. Lesson 1's first line comes out as `A¨ HÑ$sìý?`. That is not corruption to be cleaned
up — it is a different encoding, and `legacy` is that text preserved byte for byte. Turning it
into Telugu is ic_decode.py's job, deliberately kept separate: extraction is positional and
boring, decipherment is neither, and mixing them would mean re-parsing 64 PDFs every time a
mapping entry changes.

ROMANIZATION EXISTS FOR SIX LESSONS, NOT SIXTY-FOUR
Unit I (lessons 1-6) prints four lines per turn: Telugu, English, Devanagari, romanization.
From lesson 7 the scaffolding is dropped and a turn is Telugu plus English only — measured, not
assumed: 291 romanized dialogue lines in lessons 1-6 and exactly zero after. So the romanization
cannot be the route into the script for the other 58 lessons. What it CAN do is prove a decoder
right, which is what --pairs is for.

THE UNIT IS THE SPEAKER TURN, NOT THE LINE
Line-level pairing looked obvious and is wrong. The two columns wrap independently, so one
English line routinely spans two Telugu lines and vice versa — lesson 7 has a turn whose Telugu
occupies three lines and whose English occupies four, interleaved. There is no line-to-line
correspondence to recover because the typesetter never created one. A turn, delimited by the
`speaker :` label, is a real unit on both sides, and it is also the unit the reader wants: one
click-to-play, one translation.

POSITIONAL, LIKE parse_book.py
Reading order is unusable — English, Devanagari and romanization interleave unpredictably. Lines
are rebuilt by banding on the y coordinate and ordering by x, the same technique parse_book.py
uses on the 1000-words book and for the same reason.
"""
import argparse
import csv
import collections
import glob
import os
import re
import sys

try:
    import pymupdf
except ImportError:
    sys.exit('pymupdf is needed: pip3 install pymupdf')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'intensive', 'raw')
PDFS = os.path.expanduser(
    '~/Downloads/Lesson PDFs - An Intensive Course in Telugu')

STD = ('Times', 'Helvetica', 'Courier', 'Arial')
HEADINGS = ('DRILLS', 'EXERCISES', 'VOCABULARY', 'GRAMMAR NOTES', 'GRAMMER NOTES')
RUNHEAD = re.compile(r'^(An Intensive Course in Telugu|Lesson\s+\d+|UNIT\s+[IVX]+|\d+)\s*$')
SPEAKER = re.compile(r'^\s*\S{1,18}\s*:\s')

# Read off the page rather than inferred: each was rendered from the embedded font and looked
# at. `∆` was guessed as ū from context first and is actually ṇ — [gaṇṭa], not [gaūṭa] — which
# is why none of the rest were left to inference.
GLYPH = {'¡': 'ā', '•': 'ī', '£': 'ē', 'ª': 'ō', '¶': 'ū', '∂': 'ḍ',
         'ß': 'ṣ', '∆': 'ṇ', '˚': 'ḷ', '≈': 'ś', '\xa0': 'ṭ', 'M': 'ṁ'}
CLEAN = re.compile(r"^[a-zāīūēōṛṭḍṇḷṣśñṅṁ\s.,?!:;'‘’\"()\-–/0-9]+$")

# The Telugu legacy font's own high-frequency glyphs. Used only to tell it apart from the
# Devanagari legacy font, which is ASCII-heavy and would otherwise look like romanization.
TE_SIGNATURE = set('æèþýÆÿÐËÑÄìð™…Ç³ü¯')


def demap(s):
    return ''.join(GLYPH.get(c, c) for c in s)


def lines_of(doc):
    """Every visual line: (page, y, x0, x1, fonts, text), built from SPANS not from PDF lines.

    A "line" in these PDFs is not one line of one language. The typesetter sets the Telugu and
    its English gloss side by side at the same height, and PyMuPDF reports both columns as a
    single line object whose spans switch font mid-way:

        TT4F6O00     'పాప : తెలుగు పుస్తకం పేరా?'      <- left column, Telugu
        Times-Roman  'The name of the Telugu book:'    <- right column, English

    Taking the font set of the whole line then calls that line Telugu, and its text is Telugu
    AND English glued together. Downstream that meant English being cropped and handed to a
    Telugu OCR model, which returned digit noise — `00 0296 0126 1019la 0001` — and made two
    lessons look like an OCR quality problem when they were a segmentation problem.

    So fragments are spans, each with one font, and only same-font neighbours on the same band
    merge. The horizontal-gap guard keeps two columns of the SAME script apart for the same
    reason.
    """
    out = []
    for pno, page in enumerate(doc):
        frag = []
        for b in page.get_text('rawdict')['blocks']:
            for l in b.get('lines', []):
                for sp in l['spans']:
                    txt = ''.join(c['c'] for c in sp['chars'])
                    if not txt.strip():
                        continue
                    x0, y0, x1, y1 = sp['bbox']
                    frag.append([round(y0, 1), round(x0, 1), round(x1, 1),
                                 (sp['font'].split('+')[-1],), txt])
        frag.sort(key=lambda r: (r[0], r[1]))
        merged = []
        for f in frag:
            if (merged and abs(merged[-1][0] - f[0]) <= 2.0 and merged[-1][3] == f[3]
                    and f[1] - merged[-1][2] <= 24.0):
                merged[-1][2] = f[2]
                merged[-1][4] += ' ' + f[4]
            else:
                merged.append(list(f))
        out.extend((pno, m[0], m[1], m[2], m[3], m[4]) for m in merged)
    return out


def classify_fonts(lines):
    """Which subset fonts carry romanization, and which carry Telugu script.

    Neither is identified by name — the names are per-file subset tags (TT377OI00 in lesson 1,
    TT694O00 in lesson 7) and carry no meaning. They are identified by what they contain, which
    is stable: romanization reads as clean romanization once the diacritics are mapped, and the
    Telugu font is dense in glyphs that neither of the other two uses. Standard families are
    excluded up front because English *is* clean romanization by this test.
    """
    rom = collections.defaultdict(lambda: [0, 0])
    tel = collections.defaultdict(lambda: [0, 0])
    for _, _, _, _, fonts, txt in lines:
        if len(fonts) != 1 or fonts[0].startswith(STD):
            continue
        f = fonts[0]
        t = demap(txt).strip()
        if len(t) >= 4:
            rom[f][0] += 1
            if CLEAN.match(t):
                rom[f][1] += 1
        for ch in txt:
            tel[f][0] += 1
            if ch in TE_SIGNATURE:
                tel[f][1] += 1
    romf = {f for f, (n, ok) in rom.items() if n >= 3 and ok / n >= 0.6}
    # The ratio is what discriminates; the count only guards against deciding from four
    # characters. It was 200, which silently dropped every Telugu set in a heading or a small
    # inset — lesson 41 alone lost two fonts, 108 characters, because they were not the body
    # face. Those lines were not misfiled, they were discarded.
    telf = {f for f, (n, s) in tel.items() if n >= 20 and s / n > 0.25} - romf
    return romf, telf


def dialogue_end(lines):
    """The dialogue is everything above the first section heading (DRILLS / EXERCISES / ...)."""
    for pno, y, x0, x1, fonts, txt in lines:
        if txt.strip().upper().rstrip('.: ') in HEADINGS:
            return (pno, y)
    return (10 ** 6, 0.0)


def turns(doc):
    """Group the dialogue into speaker turns.

    A turn opens on a Telugu line carrying a `speaker :` label and runs until the next one.
    Every Telugu, romanization and English line inside that span belongs to it. English is
    NOT matched to individual Telugu lines — see the module docstring.
    """
    L = lines_of(doc)
    romf, telf = classify_fonts(L)
    end = dialogue_end(L)
    dlg = [r for r in L if (r[0], r[1]) < end]

    kind = []
    for pno, y, x0, x1, fonts, txt in dlg:
        if set(fonts) & telf:
            k = 'te'
        elif set(fonts) & romf:
            k = 'rom'
        elif all(f.startswith(STD) for f in fonts):
            if RUNHEAD.match(txt.strip()) or not re.search(r'[A-Za-z]', txt):
                continue
            k = 'en'
        else:
            continue                       # Devanagari, and anything unrecognised
        kind.append((pno, y, k, txt))

    out, cur = [], None
    for pno, y, k, txt in kind:
        if k == 'te' and SPEAKER.match(txt):
            cur = {'te': [], 'rom': [], 'en': [], 'keys': [],
                   'speaker': txt.split(':', 1)[0].strip(), 'prose': False}
            out.append(cur)
        if cur is None:
            continue                       # a title or a stray line before the first turn
        cur[k].append(txt.strip())
        if k == 'te':
            # Where this line sits, so ic_ocr.py can join its reading of the same line back
            # onto the turn. The turn is the unit for the reader; the line is the unit OCR
            # works on; this column is the only thing connecting them.
            #
            # DEDUPED, because one visual line can arrive as two entries — the extractor
            # splits a line wherever the font changes, and a Telugu line with a bold name in
            # it is two runs at one y. Both carry the same key, and the join looked the same
            # line up twice: every such turn came out with its text doubled.
            key = f'{pno}:{y}'
            if key not in cur['keys']:
                cur['keys'].append(key)
    return out or prose_blocks(kind)


def prose_blocks(kind):
    """The reading passages, which have no speakers to delimit them.

    Twelve lessons are not dialogues — 61 to 64 are "OVERALL REVIEW" newspaper passages, the
    rest are revision units — and they are still graded Telugu with a facing translation, so
    dropping them would be throwing away the hardest-won reading material in the book.

    They are paired by band instead: the two columns run side by side at matching heights, so a
    Telugu line and the English beside it share a y. That is line-level pairing, which the
    docstring above rejects for dialogue — and it is weaker here for the same reason, because
    the columns still wrap independently. It is flagged `prose` rather than presented as equal
    to a turn, and it is the right unit to revisit first if a passage reads out of step.
    """
    out = []
    en = [(y, t) for _, y, k, t in kind if k == 'en']
    for pno, y, k, txt in kind:
        if k != 'te':
            continue
        near = [t for ey, t in en if abs(ey - y) <= 9]
        out.append({'te': [txt.strip()], 'rom': [], 'en': [t.strip() for t in near],
                    'keys': [f'{pno}:{y}'], 'speaker': '', 'prose': True})
    return out


def rows_for(path, num):
    doc = pymupdf.open(path)
    ts = turns(doc)
    rows = []
    for i, t in enumerate(ts, 1):
        legacy = ' '.join(t['te']).strip()
        rom = demap(' '.join(t['rom'])).strip()
        en = ' '.join(t['en']).strip()
        flags = []
        if t.get('prose'):
            flags.append('prose')
        if not en:
            flags.append('no-en')
        if not rom:
            flags.append('no-rom')
        elif not CLEAN.match(rom):
            flags.append('unmapped-glyph')
        rows.append({'lesson': num, 'seq': i, 'speaker': t['speaker'], 'en': en, 'rom': rom,
                     'legacy': legacy, 'keys': ';'.join(t.get('keys', [])),
                     'flags': ' '.join(flags)})
    return rows


def title_of(doc):
    """The lesson's English title, set in bold caps above the dialogue.

    Lesson 1 heads its page WHAT IS THAT? / AND WHO IS HE?, on two lines. Taken from page one
    only, above the first turn, and only the all-caps bold lines — which excludes the running
    head ("Lesson 1", "UNIT I") without needing to know what those say.
    """
    parts = []
    for pno, y, x0, x1, fonts, txt in lines_of(doc):
        if pno > 0:
            break
        t = txt.strip()
        if not t or not any(f.startswith(('Times-Bold', 'Helvetica-Bold')) for f in fonts):
            continue
        if RUNHEAD.match(t) or not re.search(r'[A-Z]', t):
            continue
        if t.upper() != t:
            continue
        parts.append(t)
    # Not str.title(): it capitalises after an apostrophe, giving "Friend'S House".
    return re.sub(r"[A-Za-z]+(['’][A-Za-z]+)?",
                  lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(),
                  ' '.join(parts))


def line_pairs(doc):
    """Every Telugu line anywhere in the lesson, paired with the romanization line beneath it.

    pairs.tsv originally covered only the DIALOGUE of lessons 1-6 — 182 turns. But Unit I
    romanizes the whole lesson: the repetition drills, the substitution drills, the exercises.
    Lesson 1 alone sets 774 romanization spans and the dialogue accounts for 27 lines of them.
    Ignoring the rest threw away most of the parallel text in the book for no reason other than
    that the dialogue was what the extractor happened to be walking at the time.

    The pairing rule is the layout's own: the romanization is printed directly under its Telugu
    at the same left margin, so the match is the nearest Telugu line above, within 45pt, whose
    left edge agrees within 40pt. Anything looser starts pairing across columns.
    """
    L = lines_of(doc)
    romf, telf = classify_fonts(L)
    te = [(p, y, x, t) for p, y, x, _, f, t in L if set(f) & telf]
    out = []
    for pno, y, x0, x1, fonts, txt in L:
        if not set(fonts) & romf:
            continue
        cands = [c for c in te if c[0] == pno and 0 < y - c[1] <= 45 and abs(c[2] - x0) <= 40]
        if not cands:
            continue
        _, _, _, tel = max(cands, key=lambda c: c[1])      # the nearest one above
        rm = demap(txt).strip()
        if tel.strip() and rm and CLEAN.match(rm):
            out.append((tel.strip(), rm))
    return out


def inline_pairs(doc):
    """Legacy word immediately followed by its own romanization, on the same line.

    The grammar notes gloss inline — `^èþ§æþ$Ðèþ#ṁø caduvukō`, `Ðèþ…yæþ$ṁø vaṁḍukō` — and so do
    the notes' running prose: "-a occurs after A¯èþ$ anu group of verbs". Every one of those is
    a parallel pair that costs nothing to collect, and unlike the lessons 1-6 dialogues they
    are spread over the WHOLE book, so they reach the glyphs Unit I never uses. That coverage
    is the entire point: the decoder's ceiling was never the model, it was six lessons' worth
    of vocabulary.

    Runs are taken per character rather than per span, because a span boundary is not a script
    boundary — the typesetter switches font mid-span often enough that trusting spans loses
    roughly a third of these.
    """
    romf, telf = classify_fonts(lines_of(doc))
    out = []
    for page in doc:
        for b in page.get_text('rawdict')['blocks']:
            for l in b.get('lines', []):
                seq = []
                for sp in l['spans']:
                    f = sp['font'].split('+')[-1]
                    k = 'te' if f in telf else 'rom' if f in romf else 'other'
                    for ch in sp['chars']:
                        seq.append((k, ch['c']))
                runs = []
                for k, ch in seq:
                    if runs and runs[-1][0] == k:
                        runs[-1][1] += ch
                    else:
                        runs.append([k, ch])
                for i in range(len(runs) - 1):
                    if runs[i][0] != 'te' or runs[i + 1][0] != 'rom':
                        continue
                    te = runs[i][1].strip(' \t.,;:!?()\'"&-–=+/')
                    rm = demap(runs[i + 1][1]).strip(' \t.,;:!?()\'"&-–=+/')
                    # One word against one word. A long romanization run beside a short Telugu
                    # one is the notes' English commentary, not a gloss.
                    if not te or not rm or ' ' in te or not CLEAN.match(rm):
                        continue
                    if not (0.4 <= len(rm) / max(len(te), 1) <= 2.5):
                        continue
                    out.append((te, rm))
    return out


def lesson_files(pdfs):
    out = []
    for p in sorted(glob.glob(os.path.join(pdfs, '*.pdf'))):
        m = re.search(r'Lesson\s+(\d+)', os.path.basename(p))
        if m:
            out.append((int(m.group(1)), p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', type=int, help='only this lesson')
    ap.add_argument('--report', action='store_true', help='print counts, write nothing')
    ap.add_argument('--pairs', action='store_true',
                    help='also write raw/pairs.tsv and raw/inline_pairs.tsv — decoder evidence')
    ap.add_argument('--pdfs', default=PDFS, help='directory of lesson PDFs')
    args = ap.parse_args()

    files = lesson_files(args.pdfs)
    if not files:
        sys.exit(f'no lesson PDFs under {args.pdfs}')
    if args.num:
        files = [f for f in files if f[0] == args.num]

    if not args.report:
        os.makedirs(OUT, exist_ok=True)

    tot = collections.Counter()
    pairs = []
    inline = []
    titles = []
    print(f'{"lesson":>6} {"turns":>6} {"no-en":>6} {"with rom":>9}')
    for num, path in files:
        rows = rows_for(path, num)
        noen = sum(1 for r in rows if 'no-en' in r['flags'])
        wrom = sum(1 for r in rows if r['rom'])
        tot['turns'] += len(rows); tot['noen'] += noen; tot['rom'] += wrom
        print(f'{num:>6} {len(rows):>6} {noen:>6} {wrom:>9}')
        titles.append((num, title_of(pymupdf.open(path))))
        if args.pairs:
            d = pymupdf.open(path)
            pairs.extend(line_pairs(d))
            inline.extend(inline_pairs(d))
        if not args.report:
            p = os.path.join(OUT, f'lesson-{num:02d}.tsv')
            with open(p, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, delimiter='\t',
                                   fieldnames=['lesson', 'seq', 'speaker', 'en', 'rom',
                                               'legacy', 'keys', 'flags'])
                w.writeheader()
                w.writerows(rows)

    print(f'\n{len(files)} lessons · {tot["turns"]} turns · {tot["noen"]} without English '
          f'· {tot["rom"]} with romanization')
    if not args.report:
        with open(os.path.join(OUT, 'titles.tsv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['lesson', 'title'])
            w.writerows(titles)
        print(f'{sum(1 for _, t in titles if t)} lesson titles -> intensive/raw/titles.tsv')

    if args.pairs and not args.report:
        p = os.path.join(OUT, 'pairs.tsv')
        with open(p, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['legacy', 'rom'])
            w.writerows(pairs)
        seenp = set()
        pairs = [p for p in pairs if not (p in seenp or seenp.add(p))]
        print(f'{len(pairs)} aligned legacy/romanization lines -> intensive/raw/pairs.tsv')
        seen = set()
        uniq = [p for p in inline if not (p in seen or seen.add(p))]
        q = os.path.join(OUT, 'inline_pairs.tsv')
        with open(q, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['legacy', 'rom'])
            w.writerows(uniq)
        print(f'{len(inline)} inline glosses ({len(uniq)} distinct) -> intensive/raw/inline_pairs.tsv')


if __name__ == '__main__':
    main()
