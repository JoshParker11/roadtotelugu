# -*- coding: utf-8 -*-
"""Turn fetched or pasted Mini Stories into one translatable TSV per story.

    python3 tools/ms_segment.py                 # everything available, both sources
    python3 tools/ms_segment.py --num 3         # just story 3
    python3 tools/ms_segment.py --report        # what is present, what is missing

Reads whichever of these exists for a story, preferring the API dump:
    ministories/source/api/<lesson_id>.json     <- tools/ms_fetch.py
    ministories/source/paste/<id>.txt           <- pasted by hand
Writes:
    ministories/work/<id>.tsv

THE SENTENCE IS THE UNIT HERE — THE OPPOSITE CALL FROM hp_segment.py
For the novel the paragraph is the unit, because a meaning-for-meaning translation has to move
information between sentences and locking the sentence count would force a word-for-word
rendering. Here that reasoning inverts. A Mini Story is not prose; it is a drill wearing a story
as a costume. Sentence n of the story becomes question n in part 2 and reappears re-personed in
part 3, and that three-way correspondence *is* the teaching content. Translate at paragraph
level and the correspondence dissolves — you get a nice Telugu paragraph that has stopped
teaching anything.

Sentence-level also happens to be what the downstream wants: Language Reactor aligns audio to
sentence-ish segments, so the unit we translate is the unit that gets a timestamp and a
click-to-look-up. One decision, both ends satisfied.

WHY `part` IS A COLUMN AND NOT A COMMENT
Part 2 is questions and part 3 is a person shift. A translator — human or model — who cannot see
which part a line belongs to will quietly flatten a question into a statement or drop the person
shift, and neither error is visible to a reader who cannot yet read Telugu. Making it a column
means check_ms.py can assert it: the questions part alternates prompt/question/answer, and the
retell must not reuse the story's third-person verb endings wholesale.

RE-RUNNING MUST NEVER COST WORK
Same contract as hp_segment.py: existing te/notes/status are carried forward by guid before
writing. The guid keys on the English sentence, so editing the English deliberately orphans its
translation — which is correct, because an edited source invalidates what was translated from it.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from ids import guid
from msfiles import work_tsvs

MS = os.path.join(ROOT, 'ministories')
API = os.path.join(MS, 'source', 'api')
PASTE = os.path.join(MS, 'source', 'paste')
WORK = os.path.join(MS, 'work')
CATALOG = os.path.join(MS, 'CATALOG.tsv')

COLS = ['guid', 'num', 'part', 'seq', 'en', 'te', 'notes', 'status']
PARTS = ('meta', 'story', 'retell', 'questions')

# A part header in a pasted file: "## questions", "# Part 2", "-- retell --". Generous on
# purpose — the whole point of the paste path is that it tolerates however you paste.
HEADER = re.compile(r'^\s*(?:[#\-=*]+\s*)?(?:part\s*)?([123]|story|questions?|retell\w*)\b'
                    r'\s*[#\-=*:.]*\s*$', re.I)
# Leading enumeration LingQ prints on each line: "1.", "12)", "3 -".
ENUM = re.compile(r'^\s*\d{1,2}\s*[.)\-]\s+')
# Sentence end: . ! ? optionally closed by a quote, followed by space + a capital or a quote.
SPLIT = re.compile(r'(?<=[.!?])["”\']?\s+(?=["“\']?[A-Z])')

PART_ALIAS = {'1': 'story', '2': 'retell', '3': 'questions',
              'story': 'story', 'question': 'questions', 'questions': 'questions',
              'retell': 'retell', 'retelling': 'retell', 'meta': 'meta'}

# How LingQ delimits the three parts inside a single lesson. There is no field for this and no
# explicit "Questions" heading — the boundaries are prose, so these three patterns are the whole
# of the structure. Verified against lesson 2; check_ms.py should assert all three fire per story.
# Titles appear as "Story Two:", "Story 10 -" and "Story Fifty-nine -": the ordinal is spelled
# out, hyphenated or a bare numeral depending on the lesson, so accept all three. Some lessons
# (21, and the 1a/1b/1c split) carry no title line at all, which is data variation, not a miss.
TITLE = re.compile(r'^\s*story\s+[\w\-]+\s*[:\-]', re.I)
RETELL = re.compile(r'^\s*(?:now,?\s*)?here is the same story', re.I)
# The questions section opens with an ordinal-prefixed restatement: "One: Dustin is excited...".
# The colon is what makes this safe — ordinary narration never starts "One:".
ORDINAL = re.compile(r'^\s*(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
                     r'thirteen|fourteen|fifteen)\s*:', re.I)
# Kept, but note it never fires in this course: there is no "Questions" heading anywhere in the
# 62 lessons. The ordinal-prefixed restatement below is the only signal the section has started.
QHEAD = re.compile(r'^\s*(?:now,?\s*)?(?:let.s\s+)?(?:ask|answer)?\s*.{0,20}questions?\s*[.:!]?\s*$', re.I)


def catalog():
    with open(CATALOG, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def sentences(block):
    """Split a text block into sentences, one per line if it already is one."""
    out = []
    for line in block.replace('\r', '').split('\n'):
        line = ENUM.sub('', line.strip())
        if not line:
            continue
        # Already one sentence per line (how LingQ lays these out) -> keep as is.
        out.extend(s.strip() for s in SPLIT.split(line) if s.strip())
    return out


def parse_paste(text):
    """A pasted story -> [(part, sentence), ...].

    With headers, parts are explicit. Without them, fall back to blank-line-separated blocks in
    story/questions/retell order, which is how the lessons are laid out on the page.
    """
    lines = text.replace('\r', '').split('\n')
    if any(HEADER.match(l) for l in lines):
        cur, buckets = None, {p: [] for p in PARTS}
        for line in lines:
            m = HEADER.match(line)
            if m:
                cur = PART_ALIAS[m.group(1).lower().rstrip('s') if
                                 m.group(1).lower() not in PART_ALIAS else m.group(1).lower()]
                continue
            if cur:
                buckets[cur].append(line)
        return [(p, s) for p in PARTS for s in sentences('\n'.join(buckets[p]))]

    # No headers: fall back to the same in-band markers the API text carries.
    return split_parts(sentences(text))


def split_parts(lines, force=None):
    """[sentence, ...] -> [(part, sentence), ...].

    `force` pins every line to one part, which is what stories 1a/1b/1c need — LingQ splits the
    first story across three lessons, so each of those lessons *is* a part and contains none of
    the boundary markers the combined lessons carry.
    """
    out, cur = [], 'story'
    for t in lines:
        if TITLE.match(t) or RETELL.match(t) or QHEAD.match(t):
            if RETELL.match(t):
                cur = 'retell'
            elif QHEAD.match(t):
                cur = 'questions'
            out.append(('meta', t))
            continue
        if cur != 'questions' and ORDINAL.match(t):
            cur = 'questions'
        out.append((force or cur, t))
    return out


def parse_api(payload, force=None):
    """A LingQ v3 lesson payload -> [(part, sentence), ...].

    The text is in `tokenizedText`: a list of paragraphs, each a list of sentence dicts carrying
    `text`, `tokens` and a two-element `timestamp` into the lesson audio. There is no plain-text
    field on the lesson at all — `text`/`content` simply do not exist, which is why the first
    version of this function found nothing.

    We keep only `text`. The timestamps are for LingQ's English audio and cannot transfer to
    Telugu TTS, whose sentences will have entirely different durations.
    """
    tt = payload.get('tokenizedText')
    if not isinstance(tt, list) or not tt:
        raise SystemExit(
            'No tokenizedText in the lesson payload. Top-level keys: '
            + ', '.join(sorted(payload)) +
            '\nAdd the right field name to parse_api() in tools/ms_segment.py.')
    lines = []
    for para in tt:
        for sent in (para if isinstance(para, list) else [para]):
            if isinstance(sent, dict) and isinstance(sent.get('text'), str):
                t = sent['text'].strip()
                if t:
                    lines.append(t)
            elif isinstance(sent, str) and sent.strip():
                lines.append(sent.strip())
    return split_parts(lines, force)


def carry(path):
    """Existing translations, by guid, so a rebuild never eats work."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return {r['guid']: r for r in csv.DictReader(f, delimiter='\t')}


def write(row_id, num, pairs):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, f'{row_id}.tsv')
    old = carry(path)
    seen, rows = set(), []
    for part in PARTS:
        seq = 0
        for p, sent in pairs:
            if p != part:
                continue
            seq += 1
            # Meta lines are fixed boilerplate repeated verbatim in all 60 stories ("Here is
            # the same story told in a different way"). Keying them on the text alone means the
            # same line carries the same guid everywhere, so one agreed translation can be
            # propagated across every file instead of being re-decided 60 times.
            g = guid('M', sent if part == 'meta' else f'{num}:{part}:{sent}')
            if g in seen:                     # same sentence twice in one part: keep both
                g = guid('M', f'{num}:{part}:{seq}:{sent}')
            seen.add(g)
            prev = old.get(g, {})
            rows.append({'guid': g, 'num': num, 'part': part, 'seq': seq, 'en': sent,
                         'te': prev.get('te', ''), 'notes': prev.get('notes', ''),
                         'status': prev.get('status', 'todo')})
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, COLS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    kept = sum(1 for r in rows if r['te'])
    return len(rows), kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', type=int, help='only this story number')
    ap.add_argument('--report', action='store_true', help='show coverage and stop')
    args = ap.parse_args()

    rows = catalog()
    if args.report:
        have_api = len(glob.glob(os.path.join(API, '*.json')))
        have_paste = len(glob.glob(os.path.join(PASTE, '*.txt')))
        done = sorted(os.path.basename(p)[:-4] for p in work_tsvs(WORK))
        print(f'catalog       {len(rows)} lessons')
        print(f'api dumps     {max(0, have_api - 1)}')
        print(f'pasted files  {have_paste}')
        print(f'segmented     {len(done)}')
        missing = [r['id'] for r in rows if r['id'] not in done]
        if missing:
            print('missing       ' + ' '.join(missing))
        return

    total = 0
    for r in rows:
        if args.num and int(r['num']) != args.num:
            continue
        paste = os.path.join(PASTE, r['id'] + '.txt')
        api = os.path.join(API, (r['lesson_id'] or '\0') + '.json')
        # 1a/1b/1c are single-part lessons; everything else carries its boundaries in-band.
        force = None if r['part'] == 'all' else r['part']
        if os.path.exists(api):
            pairs = parse_api(json.load(open(api, encoding='utf-8')), force)
        elif os.path.exists(paste):
            pairs = parse_paste(open(paste, encoding='utf-8').read())
        else:
            continue
        if not pairs:
            print(f'{r["id"]}: no sentences found — check the source file')
            continue
        n, kept = write(r['id'], r['num'], pairs)
        note = f' ({kept} translations carried)' if kept else ''
        print(f'{r["id"]}  {n:>3} sentences{note}  {r["title"][:40]}')
        total += n
    if total:
        print(f'\n{total} sentences into ministories/work/')
    else:
        print('Nothing to do. Put a story in ministories/source/paste/<id>.txt '
              '(ids are in CATALOG.tsv) or run tools/ms_fetch.py first.')


if __name__ == '__main__':
    main()
