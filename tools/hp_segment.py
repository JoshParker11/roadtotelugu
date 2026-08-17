# -*- coding: utf-8 -*-
"""Cut the English novel into translatable segments, one TSV per chapter.

    python3 tools/hp_segment.py            # all chapters
    python3 tools/hp_segment.py --ch 1     # just one

WHY A SEGMENT STORE AND NOT A DOCUMENT
Translating into a Word file means the English and the Telugu drift apart the moment either is
edited, and there is then no way to ask "which paragraphs are done" or "did we drop a sentence".
Keeping paragraph pairs in a table makes both answerable by a script, which is the only kind of
quality control available to a translator who cannot yet read the target language.

THE PARAGRAPH IS THE UNIT, DELIBERATELY
Not the sentence. A meaning-for-meaning translation moves information between sentences all the
time — English piles up participles where Telugu wants two finite clauses, and English end-focus
has to be rebuilt as Telugu word order. Locking the sentence count would force a word-for-word
rendering, which is the thing we are explicitly not doing. The paragraph is small enough to hold
in your head and large enough to restructure inside.

RE-RUNNING THIS MUST NEVER COST WORK
It reads whatever is already in translate/work/ and carries the te/notes/status columns forward
by guid before writing. This is the same lesson as carry_sequencing() in build_master.py: a
rebuild that silently discards hand-entered columns is the most expensive kind of bug in this
repo, because nothing looks wrong until much later.

GUIDs are content-derived (see tools/ids.py for the full argument). The key is the English
paragraph, so a segment keeps its identity when paragraphs above it are added or removed, and
*loses* it if the English itself is edited — which is what we want, since an edited source
paragraph invalidates its translation.
"""
import argparse
import csv
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from ids import guid

SRC = os.path.join(ROOT, 'translate', 'source', 'hp1_en.txt')
WORK = os.path.join(ROOT, 'translate', 'work')

COLS = ['guid', 'ch', 'para', 'kind', 'en', 'te', 'notes', 'status']

# The chapter marker as it appears when the scan got it right.
MARKER = re.compile(r"^CHAPTER\s+[A-Z]+$")
# An all-caps line is a chapter title. Quoted all-caps is shouted dialogue, not a title — that
# distinction is the only thing separating the title of chapter nine from a character yelling.
CAPS = re.compile(r"^[A-Z][A-Z '\-]{3,}$")
# Chapter seventeen's title paragraph has the first sentence of the chapter glued onto it. Split
# where an all-caps run gives way to ordinary sentence case.
GLUED = re.compile(r"^([A-Z][A-Z '\-]+?)\s+((?:[A-Z][a-z]|It was).*)$")

WORDNUM = ('ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN FOURTEEN '
           'FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN TWENTY').split()


def read_source():
    """The file is a cp1252 scan with CRLF line endings and hard-wrapped lines."""
    raw = open(SRC, 'rb').read()
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f'cannot decode {SRC}')
    txt = unicodedata.normalize('NFC', txt.replace('\r\n', '\n').replace('\r', '\n'))
    # Hard wrapping is an artefact of the scan, not the book. Collapse it so a paragraph is one
    # line and the TSV stays a TSV.
    return [' '.join(p.split()) for p in re.split(r'\n\s*\n', txt) if p.strip()]


def split_chapters(paras):
    """-> [(number, title, [body paragraphs])]

    Three shapes have to be recognised, because the scan is inconsistent:
      1. CHAPTER TWO / THE VANISHING GLASS          — the normal case
      2. THE MIDNIGHT DUEL                          — chapter nine lost its CHAPTER marker
      3. CHAPTER SEVENTEEN / THE MAN WITH TWO FACES It was...  — title glued to the first line
    """
    chapters, n, title, body = [], 0, None, []

    def flush():
        # A title with no prose under it is not a chapter — it is the "THE END" line at the foot
        # of the file, which matches CAPS exactly as well as a real title does.
        if n and body:
            chapters.append((n, title, body))

    i = 0
    while i < len(paras):
        p = paras[i]
        started = False
        if MARKER.match(p):
            flush()
            n, body = WORDNUM.index(p.split()[1]) + 1, []
            i += 1
            title, extra = take_title(paras[i] if i < len(paras) else '')
            if extra:
                body.append(extra)
            started = True
        elif CAPS.match(p) and '"' not in p:
            # A bare title. Only believable as a chapter start once we are already in the book.
            flush()
            n, body = (n + 1) if n else 1, []
            title, extra = take_title(p)
            if extra:
                body.append(extra)
            started = True
        if not started:
            if n:
                body.append(p)
        i += 1
    flush()
    return chapters


def take_title(p):
    """Return (title, leftover body text) for a title paragraph that may have prose attached."""
    m = GLUED.match(p)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return p.strip(), ''


def existing(path):
    """Hand-entered columns already on disk, keyed by guid. See the module docstring."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8', newline='') as f:
        return {r['guid']: r for r in csv.DictReader(f, delimiter='\t')}


def write_chapter(num, title, body, keep_only=None):
    if keep_only and num != keep_only:
        return None
    path = os.path.join(WORK, f'ch{num:02d}.tsv')
    prior = existing(path)
    rows, seen = [], {}
    units = [('title', title)] + [('body', b) for b in body]
    for idx, (kind, text) in enumerate(units):
        # Two identical short paragraphs ('"What?"') would otherwise share a guid. Disambiguate
        # by occurrence, which is stable as long as the source is.
        seen[text] = seen.get(text, 0) + 1
        key = text if seen[text] == 1 else f'{text}#{seen[text]}'
        g = guid('H', key)
        old = prior.get(g, {})
        rows.append({
            'guid': g, 'ch': num, 'para': idx, 'kind': kind, 'en': text,
            'te': old.get('te', ''), 'notes': old.get('notes', ''),
            'status': old.get('status', 'todo'),
        })
    carried = sum(1 for r in rows if r['te'])
    dropped = [g for g in prior if g not in {r['guid'] for r in rows} and prior[g].get('te')]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, COLS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    return path, len(rows), carried, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ch', type=int, help='only rebuild this chapter')
    args = ap.parse_args()

    os.makedirs(WORK, exist_ok=True)
    chapters = split_chapters(read_source())
    print(f'{len(chapters)} chapters')

    total_dropped = []
    for num, title, body in chapters:
        res = write_chapter(num, title, body, args.ch)
        if not res:
            continue
        path, n, carried, dropped = res
        note = f'  ({carried} translated carried forward)' if carried else ''
        warn = f'  !! {len(dropped)} translated rows no longer match any paragraph' if dropped else ''
        print(f'  ch{num:02d}  {n:4d} segments  {title[:38]:<38}{note}{warn}')
        total_dropped += dropped

    if total_dropped:
        print('\nWARNING: translations exist for segments the source no longer contains.')
        print('Either the English was edited, or a paragraph moved. Nothing was deleted from')
        print('disk before this run, but the rewritten file no longer carries them. Recover with')
        print('`git stash` if needed — or just re-check those paragraphs by hand.')


if __name__ == '__main__':
    main()
