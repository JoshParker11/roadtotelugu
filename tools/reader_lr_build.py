# -*- coding: utf-8 -*-
"""Join a dataset's per-sentence clips into one continuous track per section, with exact cues.

    python3 tools/reader_lr_build.py reader/data/poa.js
    python3 tools/reader_lr_build.py reader/data/poa.js --gap 0.6 --bitrate 80k

WHY A CONTINUOUS TRACK AND NOT 925 LITTLE FILES
The reader plays one file per section and seeks inside it: a line's play button sets
currentTime, and the highlight follows whichever line's [s,e] window the clock is in. That
needs a single track. It is also much better over a network — one request instead of
twenty-seven, and the phone can buffer ahead — and it is the shape the other two corpora
already use, so nothing downstream needs a second code path.

THE TIMINGS HERE ARE MEASURED, NOT DERIVED
Every other timing in this project was estimated from character counts and then, for the
chapter-one discussion, corrected by recognising the audio. None of that applies here: each
sentence is its own file, so its duration is a fact from ffprobe and the cue is exact. This is
the one corpus whose per-line seeking is simply correct.

WHAT IS COMMITTED
The joined tracks and the cue file, not the 925 per-sentence clips they were built from — the
same division the other corpora make. The clips are the regenerable intermediate; the track is
what the site serves. Re-encoding to mono at a speech bitrate is what keeps that affordable:
44 MB of separate clips becomes a few MB per chapter, and speech loses nothing.
"""
import argparse
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))


def load_dataset(path):
    raw = open(path, encoding='utf-8').read()
    i = raw.index('=', raw.index('window.')) + 1
    return json.loads(raw[i:].strip().rstrip(';'))


def duration(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def build_story(clips, out_path, gap, bitrate):
    """Concatenate with a gap between sentences. -> [(start, end)] per clip, and the total.

    The gap is inserted as silence in the filter graph rather than by padding each clip, so a
    cue boundary lands exactly where the next sentence starts speaking.
    """
    inputs, filters, labels = [], [], []
    for i, c in enumerate(clips):
        inputs += ['-i', c]
        filters.append(f'[{i}:a]aresample=24000[a{i}]')
        labels.append(f'[a{i}]')
    # One silence source, reused between every pair.
    n = len(clips)
    sil = f'[{n}:a]'
    inputs += ['-f', 'lavfi', '-t', str(gap), '-i', 'anullsrc=r=24000:cl=mono']
    filters.append(f'{sil}aresample=24000[sil]')

    # ffmpeg cannot link one filter output twice, so the silence is duplicated into as many
    # copies as there are gaps — with ASPLIT, not split: `split` is the video filter and fails
    # with "media type mismatch ... (audio) and ... (video)", which reads like a codec problem
    # rather than the wrong filter name.
    gaps = len(clips) - 1
    if gaps == 1:
        filters.append('[sil]acopy[s0]')
    elif gaps > 1:
        filters.append(f'[sil]asplit={gaps}' + ''.join(f'[s{i}]' for i in range(gaps)))

    seq, cues, t, gi = [], [], 0.0, 0
    for i, c in enumerate(clips):
        d = duration(c)
        cues.append((t, t + d))
        seq.append(f'[a{i}]')
        t += d
        if i != len(clips) - 1:
            seq.append(f'[s{gi}]')
            gi += 1
            t += gap

    fc = ';'.join(filters) + ';' + ''.join(seq) + f'concat=n={len(seq)}:v=0:a=1[out]'
    cmd = ['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', fc,
           '-map', '[out]', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', bitrate, out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'ffmpeg failed for {os.path.basename(out_path)}:\n{r.stderr[-1500:]}')
    return cues, duration(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('--clips', default='', help='per-sentence clip directory')
    ap.add_argument('--out', default='', help='where the joined tracks go')
    ap.add_argument('--cues', default='', help='cue TSV path')
    ap.add_argument('--gap', type=float, default=0.5, help='silence between sentences')
    ap.add_argument('--bitrate', default='64k')
    ap.add_argument('--only', default='', help='e.g. 1,2 — rebuild these section numbers only')
    args = ap.parse_args()

    data = load_dataset(os.path.join(ROOT, args.data))
    tag = data.get('tag', 'x')
    clips = os.path.join(ROOT, args.clips or f'{tag}/audio')
    outdir = os.path.join(ROOT, args.out or f'{tag}/lr')
    cues_path = os.path.join(ROOT, args.cues or f'{tag}/audio_cues.tsv')
    os.makedirs(outdir, exist_ok=True)
    only = {int(x) for x in args.only.split(',') if x.strip()}

    prior = {}
    if os.path.exists(cues_path):
        with open(cues_path, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                prior[r['guid']] = r

    rows, built, skipped = [], 0, 0
    for st in data['stories']:
        num = st['num']
        have = [(ln, os.path.join(clips, ln['g'] + '.mp3')) for ln in st['lines']]
        have = [(ln, p) for ln, p in have if os.path.exists(p)]
        if not have:
            skipped += 1
            continue
        out_path = os.path.join(outdir, f'section_{num:02d}.mp3')
        if only and num not in only and os.path.exists(out_path):
            # Carry its cues forward untouched rather than dropping them.
            for ln, _ in have:
                if ln['g'] in prior:
                    rows.append(prior[ln['g']])
            continue
        cues, total = build_story([p for _, p in have], out_path, args.gap, args.bitrate)
        for (ln, _), (s, e) in zip(have, cues):
            rows.append({'guid': ln['g'], 'section': num,
                         'start': f'{s:.2f}', 'end': f'{e:.2f}', 'total': f'{total:.2f}'})
        built += 1
        print(f'  section_{num:02d}.mp3  {len(have):3d} sentences  {total / 60:5.2f} min  '
              f'{os.path.getsize(out_path) / 1048576:4.1f} MB')

    with open(cues_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, ['guid', 'section', 'start', 'end', 'total'],
                           delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

    total_mb = sum(os.path.getsize(os.path.join(outdir, n))
                   for n in os.listdir(outdir) if n.endswith('.mp3')) / 1048576
    print(f'\n{built} track(s) built, {skipped} section(s) had no clips')
    print(f'{os.path.relpath(outdir, ROOT)}/  {total_mb:.1f} MB total')
    print(f'{os.path.relpath(cues_path, ROOT)}  {len(rows)} cues')


if __name__ == '__main__':
    main()
