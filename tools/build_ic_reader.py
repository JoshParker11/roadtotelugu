# -*- coding: utf-8 -*-
"""Bake the Intensive Course lessons into the LingQ-style reader.

    python3 tools/build_ic_reader.py                 # lessons whose Telugu came from the book
    python3 tools/build_ic_reader.py --all           # every lesson, OCR included
    python3 tools/build_ic_reader.py --lessons 1-6

Writes reader/data/intensive.js — window.IC_DATA, the same shape build_ms_reader.py writes for
the mini stories, so the reader needs no new rendering code.

EVERYTHING LOAD-BEARING IS IMPORTED, NOT REWRITTEN
The lexicon resolution, the verb-form lookup, the stem+suffix decomposition and the tokeniser
all live in build_ms_reader.Resolver and are reused verbatim. That is what makes a word marked
known in the mini stories show as known here for free: same guid scheme, same lexicon, one
implementation.

THE TURN IS THE LINE, AND IT IS NOT SPLIT INTO SENTENCES
A turn carries exactly one English translation. Several Telugu sentences often sit inside it —
`idi gōḍa. adi vākili.` is one turn with one gloss — and splitting the Telugu without splitting
the English would mean inventing an alignment nobody wrote down. The mini stories could be
sentence-per-line because LingQ supplied them that way; this book did not, and guessing is the
kind of quiet fabrication this project avoids. A turn is also a real unit: one speaker, one
thought, one thing to play back later.

DEFAULT IS LESSONS 1-6, ON PURPOSE
Those are the lessons where the book printed its own romanization, so their Telugu is derived
from the book's statement of what the Telugu is and round-trips back to it exactly (see
ic_ocr.py --build). Lessons 7-64 are OCR at ~93% word accuracy, which is good enough to read
and not good enough to study unreviewed. `--all` includes them and marks them.
"""
import argparse
import collections
import csv
import datetime
import re
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from build_ms_reader import Resolver, best_gloss
from ids import guid

WORK = os.path.join(ROOT, 'intensive', 'work')
VOCAB = os.path.join(ROOT, 'intensive', 'raw', 'vocab.tsv')
# Hand-written cards for words the book's own glossary does not cover — the course's
# equivalent of ministories/vocab.tsv, and the same honest status: nothing checks them.
CARDS = os.path.join(ROOT, 'intensive', 'vocab.tsv')
TITLES = os.path.join(ROOT, 'intensive', 'raw', 'titles.tsv')
OUT_JS = os.path.join(ROOT, 'reader', 'data', 'intensive.js')
OUT_WORDS = os.path.join(ROOT, 'intensive', 'word_audio.tsv')
CUES = os.path.join(ROOT, 'intensive', 'audio_cues.tsv')


ZW = '\u200c\u200d'
STRIP = ' .,;:!?()\'"\u2018\u2019\u201c\u201d-'


def key(te):
    """Match key: the word without joiners or edge punctuation.

    OCR keeps the comma it saw after హాస్టలు, and the full stop after కాయితం, so a raw
    comparison misses exactly the words the book bothered to gloss.
    """
    return (te or '').strip(STRIP).translate({ord(c): None for c in ZW})


def book_glosses():
    """The book's own VOCABULARY lists, keyed for lookup — see tools/ic_vocab.py.

    These are the publisher's glosses for the words the book chose to teach. Preferred over
    anything derived, and the reason all 64 lessons can go in the reader without 3,251 words
    showing no meaning.
    """
    out = {}
    if not os.path.exists(VOCAB):
        return out
    with open(VOCAB, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            k = key(r['te'])
            if k and r['en'].strip():
                out.setdefault(k, r['en'].strip())
    return out


def speaker_names():
    """Every name that opens a turn, as `<name> :` in the decoded Telugu.

    The book is dialogue, so a large share of its distinct words are the handful of people
    speaking — రవి, గిరి, లత, రామారావు. They will never appear in a VOCABULARY list because
    the book does not gloss its own characters, and left alone they are the single biggest
    block of words in the reader with no meaning attached.

    Taken from the text rather than from a hand-kept list: whoever speaks is whoever the
    extractor found before the colon, so a name cannot go missing when a later lesson
    introduces one.
    """
    names = collections.Counter()
    for fn in sorted(os.listdir(WORK)):
        if not fn.endswith('.tsv'):
            continue
        with open(os.path.join(WORK, fn), encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                m = re.match(r'^\s*(\S{2,20})\s*:', r.get('te') or '')
                if m:
                    names[key(m.group(1))] += 1
    # Once is a mis-split or an OCR slip; a real speaker recurs.
    return {n for n, c in names.items() if c >= 3 and n}


def written_cards():
    """guid-free gloss cards keyed on the Telugu, plus the words marked as OCR debris.

    `status=ocr-junk` is not a definition; it is a note that the "word" is a misreading and
    should never have been a headword. Marking them is what keeps them out of the audio
    manifest and out of any future definition batch — glossing OCR debris would be inventing a
    meaning for a word that does not exist.
    """
    glosses, junk = {}, set()
    if not os.path.exists(CARDS):
        return glosses, junk
    with open(CARDS, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            k = key(r['te'])
            if not k:
                continue
            if (r.get('status') or '').strip() == 'ocr-junk':
                junk.add(k)
            elif r.get('gloss', '').strip():
                glosses[k] = r['gloss'].strip()
    return glosses, junk


def parse_lessons(spec):
    out = set()
    for part in spec.split(','):
        if '-' in part:
            a, b = part.split('-')
            out |= set(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def titles():
    if not os.path.exists(TITLES):
        return {}
    with open(TITLES, encoding='utf-8') as f:
        return {int(r['lesson']): r['title'] for r in csv.DictReader(f, delimiter='\t')}


def cues():
    """guid -> (start, end, lesson total), written by ic_audio_build.py.

    Read rather than recomputed. build_ms_reader recomputes the mini stories' offsets from
    ms_lr_export's functions, and the two silently disagreed the moment one of them changed
    which rows it included — every timing after the missing row pointed at the wrong sentence.
    One arithmetic, written down once.
    """
    out = {}
    if not os.path.exists(CUES):
        return out
    with open(CUES, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            out[r['guid']] = (float(r['start']), float(r['end']), float(r['total']))
    return out


def bake(num, rs, tmap, allow_ocr, cue=None):
    path = os.path.join(WORK, f'{num:02d}.tsv')
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t') if r['te'].strip()]
    if not allow_ocr:
        rows = [r for r in rows if r.get('te_src') == 'rom']
    if not rows:
        return None

    cue = cue or {}
    lines, total = [], 0.0
    for r in rows:
        ln = {'g': guid('S', r['te']), 'p': 'turn',
              't': rs.resolve_line(r['te']), 'en': r['en']}
        c = cue.get(r.get('guid') or '')
        if c:
            ln['s'], ln['e'] = c[0], c[1]
            total = c[2]
        if r.get('speaker'):
            ln['sp'] = r['speaker']
        # The reader shows this as a caution on the line. `rom` means the book itself said what
        # the Telugu is; `ocr` means a model read it off the page and nobody has checked.
        if r.get('te_src') != 'rom':
            ln['ocr'] = 1
        lines.append(ln)

    # Audio only when EVERY turn has a cue. A lesson with half its turns voiced would play the
    # right sound at the wrong moments for the other half, which is worse than staying silent.
    voiced = all('s' in l for l in lines) and total > 0
    return {'num': num, 'title': {'te': '', 'en': tmap.get(num) or f'Lesson {num}'},
            'audio': f'../intensive/lr/lesson_{num:02d}.mp3' if voiced else '',
            'dur': total if voiced else 0, 'lines': lines}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lessons', default='1-6')
    ap.add_argument('--all', action='store_true', help='include OCR-sourced lessons')
    args = ap.parse_args()

    nums = parse_lessons('1-64' if args.all else args.lessons)
    rs = Resolver()
    rs.book = book_glosses()
    for n in speaker_names():
        rs.book.setdefault(n, 'a speaker in these dialogues (name)')
    written, junk = written_cards()
    rs.book.update(written)              # hand-written cards win over a derived name gloss
    rs.junk = junk
    tmap = titles()
    cue = cues()
    stories = [s for s in (bake(n, rs, tmap, args.all, cue) for n in nums) if s]
    if not stories:
        sys.exit('nothing to bake')

    # Which lesson each word is first met in. build_ms_reader records the same thing as `f`
    # for its stories, and the vocabulary table prints it — without it every course word read
    # "story undefined".
    # ...and how often it occurs, which the vocabulary table prints as "×N" and sorts by.
    # Neither was recorded here, so every course word read "×undefined · story undefined".
    first, count = {}, collections.Counter()
    for st in stories:
        for ln in st['lines']:
            for _, _, ix in ln['t']:
                if ix < 0:
                    continue
                g = rs.lex[ix]['g']
                count[g] += 1
                if g not in first:
                    first[g] = st['num']
    for l in rs.lex:
        l['f'] = first.get(l['g'], 0)
        l['n'] = count.get(l['g'], 0)

    data = {'generated': datetime.date.today().isoformat(),
            'source': 'An Intensive Course in Telugu',
            'lex': rs.lex, 'stories': stories}
    os.makedirs(os.path.dirname(OUT_JS), exist_ok=True)
    with open(OUT_JS, 'w', encoding='utf-8') as f:
        f.write('/* Generated by tools/build_ic_reader.py. Do not edit. */\n')
        f.write('window.IC_DATA = ' +
                json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')

    # The distinct-word manifest, same shape and same purpose as the mini stories': it is what
    # the per-headword pronunciation clips are generated from. build_ms_reader has always
    # written one; this side did not, which is why --words had nothing to export.
    # OCR debris is left out. The reader renders it inert with no speaker button, so a clip
    # for it could never be played — generating one is paying to synthesise a string that was
    # never on the page, and then storing it forever.
    voiceable = [l for l in rs.lex if not l.get('junk')]
    with open(OUT_WORDS, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['guid', 'te', 'en'])
        w.writerows((l['g'], l['te'], best_gloss(l)) for l in voiceable)

    turns = sum(len(s['lines']) for s in stories)
    ocr = sum(1 for s in stories for l in s['lines'] if l.get('ocr'))
    print(f'{len(stories)} lessons · {turns} turns · {len(rs.lex)} distinct words '
          f'-> reader/data/intensive.js')
    print(f'  {turns - ocr} from the book\'s own romanization, {ocr} from OCR')
    print(f'{len(voiceable)} voiceable words -> {os.path.relpath(OUT_WORDS, ROOT)}'
          f'   ({len(rs.lex) - len(voiceable)} OCR-debris entries left out)')
    print(f'{sum(1 for s in stories if s["audio"])} lesson(s) with audio')


if __name__ == '__main__':
    main()
