# -*- coding: utf-8 -*-
"""Build one continuous audio file + two synced SRT files per story, for Language Reactor import.

    python3 tools/ms_lr_export.py --num 1        # story 1 (spans 01a/01b/01c)
    python3 tools/ms_lr_export.py --num 2
    python3 tools/ms_lr_export.py                # every story that is fully covered

Writes, per story:
    ministories/lr/story_<NN>.mp3       one continuous recording
    ministories/lr/story_<NN>.te.srt    Telugu subtitle track
    ministories/lr/story_<NN>.en.srt    English subtitle track, IDENTICAL timing

Import both SRTs alongside the mp3 as Language Reactor's own dual-subtitle track pair. Both
tracks are ours — LR never runs its own machine translation on this, because we supplied both
sides ourselves. That is the whole point of this file: it turns "checked translation + generated
audio" into the one shape LR actually knows how to import.

PLAY ORDER, NOT FILE ORDER
Story one is split across three lesson files (01a/01b/01c) because that is how LingQ split it,
but a listener wants one continuous recording of "the story" — title, story, the retell intro
line, the retell, then the questions. Group by story NUMBER exactly the way check_ms.py already
does for its cross-file checks, then order by a fixed rule: meta(title) -> story -> meta(retell
intro) -> retell -> questions. The two meta rows are told apart by their own seq (1 = title,
2 = retell intro), not by which file they happen to live in.

WHY SILENCE IS INSERTED RATHER THAN LEFT TO THE CLIPS THEMSELVES
Each clip was synthesized alone and butts up against a hard edge with no breath in it. Playing
232 of them back to back with zero gap is not how a person reads a story aloud. A short gap
between sentences and a longer one at a genuine section change (LONG_GAP before the retell intro,
before the retell itself, and before the questions) is the acoustic equivalent of a paragraph
break — nothing is fabricated in the *text*, only in the pacing of already-real speech.

WHY FFMPEG'S FILTER-GRAPH CONCAT AND NOT THE CONCAT DEMUXER
The demuxer's stream-copy path only glues cleanly when every input shares identical codec
parameters, which is not guaranteed across two audio-generation paths (ms_audio.py vs HyperTTS).
Decoding every input and the inserted silence through one filter graph, then encoding once at the
end, is slower but correct regardless of what produced each clip.
"""
import argparse
import csv
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ms_segment import RETELL  # the one existing test for "this meta row is the
from msfiles import work_tsvs
                                # retell-intro line", already verified in ms_segment.py

ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
AUDIO = os.path.join(MS, 'audio')
CATALOG = os.path.join(MS, 'CATALOG.tsv')
OUT = os.path.join(MS, 'lr')

SHORT_GAP = 0.6   # seconds, between sentences within one part
LONG_GAP = 1.6    # seconds, at a section change
PART_RANK = {'story': 1, 'retell': 3, 'questions': 4}


def sort_key(r):
    """Play order: title -> story -> retell-intro -> retell -> questions.

    Meta rows CANNOT be told apart by seq: ms_segment.py numbers seq per file, and story one's
    retell-intro line lives alone in 01b.tsv, where it is (correctly, for that file) seq=1 — the
    same seq value the title carries in 01a.tsv. A first version of this sorted on seq and put
    the retell-intro line second in the whole recording, right after the title, before any story
    line. Classify by CONTENT instead: RETELL is the one regex that already exists to answer
    "is this meta line the retell-intro", reused from ms_segment.py rather than re-guessed here.
    """
    if r['part'] == 'meta':
        return (2, 0) if RETELL.match(r['en']) else (0, 0)
    return (PART_RANK[r['part']], int(r['seq']))


def gap_before(prev, cur):
    """LONG_GAP at a section change, SHORT_GAP between two lines of the same section."""
    if prev is None:
        return 0.0
    return SHORT_GAP if sort_key(prev)[0] == sort_key(cur)[0] else LONG_GAP


def rows_for(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def story_rows(num, cat):
    rows = []
    for path in work_tsvs(WORK):
        sid = os.path.basename(path)[:-4]
        if int(cat[sid]['num']) == int(num):
            rows.extend(rows_for(path))
    rows.sort(key=sort_key)
    return rows


def duration(path):
    from mutagen.mp3 import MP3
    return MP3(path).info.length


def srt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ms = round((s - int(s)) * 1000)
    return f'{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}'


def build(num, cat):
    rows = story_rows(num, cat)
    missing = [r for r in rows if not os.path.exists(os.path.join(AUDIO, r['guid'] + '.mp3'))]
    if missing:
        print(f'story {num}: skipped — {len(missing)} segment(s) have no audio yet '
              f'(e.g. {missing[0]["guid"]})')
        return False
    if not rows:
        print(f'story {num}: no segments found')
        return False

    os.makedirs(OUT, exist_ok=True)
    # stream_idx counts actual -i occurrences, one per increment — NOT len(inputs), which counts
    # raw CLI-argument tokens and drifts as soon as a lavfi input (4 tokens: -f lavfi -i ...) and
    # a plain file input (2 tokens: -i path) are mixed. Using len(inputs) as the ffmpeg stream
    # number was the bug on the first run: indices jumped by 2 or 4 instead of 1, and ffmpeg
    # rejected the resulting filtergraph as malformed.
    inputs, filters, labels, cues = [], [], [], []
    t = 0.0
    prev = None
    stream_idx = 0
    for r in rows:
        gap = gap_before(prev, r)
        if gap:
            inputs += ['-f', 'lavfi', '-i', f'anullsrc=r=24000:cl=mono:d={gap}']
            filters.append(f'[{stream_idx}:a]anull[s{stream_idx}]')
            labels.append(f'[s{stream_idx}]')
            stream_idx += 1
            t += gap
        path = os.path.join(AUDIO, r['guid'] + '.mp3')
        inputs += ['-i', path]
        filters.append(f'[{stream_idx}:a]anull[s{stream_idx}]')
        labels.append(f'[s{stream_idx}]')
        stream_idx += 1
        start = t
        t += duration(path)
        cues.append((start, t, r['te'], r['en']))
        prev = r

    filter_complex = ';'.join(filters) + ';' + ''.join(labels) + f'concat=n={len(labels)}:v=0:a=1[out]'
    mp3_path = os.path.join(OUT, f'story_{int(num):02d}.mp3')
    cmd = ['ffmpeg', '-y', *inputs, '-filter_complex', filter_complex,
           '-map', '[out]', '-c:a', 'libmp3lame', '-b:a', '96k', mp3_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'ffmpeg failed for story {num}:\n{r.stderr[-2000:]}')

    for lang, col in (('te', 2), ('en', 3)):
        path = os.path.join(OUT, f'story_{int(num):02d}.{lang}.srt')
        with open(path, 'w', encoding='utf-8') as f:
            for i, cue in enumerate(cues, 1):
                f.write(f'{i}\n{srt_time(cue[0])} --> {srt_time(cue[1])}\n{cue[col]}\n\n')

    # Combined fallback: some players (including the specific tool this project first tried in
    # Language Reactor) accept exactly ONE subtitle file and would otherwise auto-translate it
    # themselves for a second line — discarding the checked English in favour of a fresh,
    # unverified machine translation of the Telugu. Two lines in one cue sidesteps that: whatever
    # accepts a single SRT gets both languages, verbatim, with nothing left for the player to
    # translate on its own.
    bi_path = os.path.join(OUT, f'story_{int(num):02d}.bilingual.srt')
    with open(bi_path, 'w', encoding='utf-8') as f:
        for i, cue in enumerate(cues, 1):
            f.write(f'{i}\n{srt_time(cue[0])} --> {srt_time(cue[1])}\n{cue[2]}\n{cue[3]}\n\n')

    print(f'story {num}: {len(rows)} segments, {t:.0f}s -> '
          f'story_{int(num):02d}.mp3 + .te.srt + .en.srt + .bilingual.srt')
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', help='only this story number; default is every fully-covered story')
    args = ap.parse_args()

    with open(CATALOG, encoding='utf-8') as f:
        cat = {r['id']: r for r in csv.DictReader(f, delimiter='\t')}
    nums = [int(args.num)] if args.num else sorted({int(r['num']) for r in cat.values()})

    built = 0
    for n in nums:
        if build(n, cat):
            built += 1
    print(f'\n{built}/{len(nums)} stor{"y" if built == 1 else "ies"} built')


if __name__ == '__main__':
    main()
