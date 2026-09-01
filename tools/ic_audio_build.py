# -*- coding: utf-8 -*-
"""Concatenate a lesson's turn clips into one file the reader can seek through.

    python3 tools/ic_audio_build.py            # every lesson whose turns are all voiced
    python3 tools/ic_audio_build.py --num 3

Writes, per lesson:
    intensive/lr/lesson_NN.mp3     one continuous recording
    intensive/audio_cues.tsv       guid -> (lesson, start, end), for build_ic_reader

WHY ONE FILE PER LESSON RATHER THAN ONE PER TURN
The reader is built around a single recording with seek offsets, and on a phone thirty separate
requests to start a lesson is thirty chances to stall. It also makes continuous listening
possible, which is the point of having the audio at all.

WHY THE CUES ARE WRITTEN DOWN INSTEAD OF RECOMPUTED
build_ms_reader recomputes the mini stories' offsets by importing ms_lr_export's own functions,
so the two agree only as long as nobody changes one of them. They stopped agreeing once —
ms_lr_export dropped untranslated titles and the reader did not, and every timing after the
missing row pointed at the wrong sentence. Here the concatenator emits the offsets it actually
used and the reader reads them, so there is one arithmetic and no way to disagree with it.
"""
import argparse
import collections
import csv
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from msfiles import work_tsvs

IC = os.path.join(ROOT, 'intensive')
WORK = os.path.join(IC, 'work')
AUDIO = os.path.join(IC, 'audio')
OUT = os.path.join(IC, 'lr')
CUES = os.path.join(IC, 'audio_cues.tsv')
GAP = 0.7          # a breath between turns; a dialogue read with no gaps is a wall


def duration(path):
    from mutagen.mp3 import MP3
    return MP3(path).info.length


def lesson_turns():
    per = collections.defaultdict(list)
    for p in work_tsvs(WORK):
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
            if r['te'].strip() and r.get('guid'):
                per[int(r['lesson'])].append(r)
    for n in per:
        per[n].sort(key=lambda r: int(r['seq']))
    return per


def build(num, rows):
    missing = [r for r in rows if not os.path.exists(os.path.join(AUDIO, r['guid'] + '.mp3'))]
    if missing:
        return None, f'{len(missing)} turn(s) not voiced yet'

    inputs, filters, labels, cues = [], [], [], []
    t, idx = 0.0, 0
    for i, r in enumerate(rows):
        if i:
            inputs += ['-f', 'lavfi', '-i', f'anullsrc=r=24000:cl=mono:d={GAP}']
            filters.append(f'[{idx}:a]anull[s{idx}]'); labels.append(f'[s{idx}]'); idx += 1
            t += GAP
        path = os.path.join(AUDIO, r['guid'] + '.mp3')
        inputs += ['-i', path]
        filters.append(f'[{idx}:a]anull[s{idx}]'); labels.append(f'[s{idx}]'); idx += 1
        start = t
        t += duration(path)
        cues.append((r['guid'], round(start, 2), round(t, 2)))

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f'lesson_{num:02d}.mp3')
    cmd = ['ffmpeg', '-y', *inputs, '-filter_complex',
           ';'.join(filters) + ';' + ''.join(labels) + f'concat=n={len(labels)}:v=0:a=1[out]',
           '-map', '[out]', '-c:a', 'libmp3lame', '-b:a', '96k', dst]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, f'ffmpeg failed: {p.stderr[-300:]}'
    return (cues, round(t, 2)), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', type=int)
    args = ap.parse_args()

    per = lesson_turns()
    existing = {}
    if os.path.exists(CUES):
        with open(CUES, encoding='utf-8') as f:
            existing = {r['guid']: r for r in csv.DictReader(f, delimiter='\t')}

    built = 0
    for num in sorted(per):
        if args.num and num != args.num:
            continue
        got, why = build(num, per[num])
        if got is None:
            if 'not voiced' not in why:
                print(f'lesson {num:02d}: {why}')
            continue
        cues, total = got
        for g, s, e in cues:
            existing[g] = {'guid': g, 'lesson': num, 'start': s, 'end': e, 'total': total}
        built += 1
        print(f'lesson {num:02d}: {len(cues)} turns, {total:.0f}s -> lr/lesson_{num:02d}.mp3')

    with open(CUES, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, delimiter='\t', fieldnames=['guid', 'lesson', 'start', 'end', 'total'])
        w.writeheader(); w.writerows(existing.values())
    print(f'\n{built} lesson(s) built · {len(existing)} cues -> {os.path.relpath(CUES, ROOT)}')


if __name__ == '__main__':
    main()
