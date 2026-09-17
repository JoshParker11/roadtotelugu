# -*- coding: utf-8 -*-
"""Export any baked reader dataset to the TSVs Anki + HyperTTS drive.

    python3 tools/reader_hypertts_export.py reader/data/poa.js --sentences
    python3 tools/reader_hypertts_export.py reader/data/poa.js --words
    python3 tools/reader_hypertts_export.py reader/data/poa.js --words --limit 800

WHY GENERIC AND NOT A FOURTH COPY
ms_hypertts_export.py and ic_hypertts_export.py do the same job for their own corpora, reading
their own intermediate TSVs. A third import would have meant a third copy, and the same is true
of every import after it. The baked reader dataset already holds everything this needs — guid,
spelling, gloss, and which section a line belongs to — so reading that instead works for every
corpus, present and future, and cannot disagree with what the reader actually shows.

Output matches the existing round trip exactly: `#separator:tab`, `#html:false`, and the columns
guid/telugu/audio/english in that order, because tools/ms_hypertts_import.py matches the audio
back by the guid in column one and that guid must survive Anki untouched.

WHAT IS LEFT OUT OF THE WORD EXPORT, AND WHY
  - Forms with no Telugu at all. A Telugu neural voice reading "Hogwarts" produces a mispronounced
    English word, not a pronunciation guide. These are the protected names the graded readers keep
    in Latin on purpose; they are clickable and glossed, but they are not vocabulary to drill.
  - Forms the source marked reference-only (`ref`) — names and numbers the pipeline itself says
    should not enter study.
  - Anything already recorded. Same skip-if-exists discipline as the other two exporters: a word
    with a clip is not re-exported, so a partial batch can be resumed by re-running this.
Pass --all to override the first two.
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
TELUGU = re.compile(r'[ఀ-౿]')


def load_dataset(path):
    """Read a `window.X_DATA = {...};` file back into a dict."""
    raw = open(path, encoding='utf-8').read()
    i = raw.index('=', raw.index('window.')) + 1
    body = raw[i:].strip()
    if body.endswith(';'):
        body = body[:-1]
    return json.loads(body)


def existing(dirs):
    """Guids that already have a clip anywhere we might have put one."""
    have = set()
    for d in dirs:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            have |= {n[:-4] for n in os.listdir(p) if n.endswith('.mp3')}
    return have


def write_tsv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('#separator:tab\n#html:false\n#columns:guid\ttelugu\taudio\tenglish\n')
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data', help='e.g. reader/data/poa.js')
    ap.add_argument('--words', action='store_true')
    ap.add_argument('--sentences', action='store_true')
    ap.add_argument('--out', default='', help='override the output path')
    ap.add_argument('--audio-dir', default='', help='where clips will land, for skip-if-exists')
    ap.add_argument('--limit', type=int, default=0, help='first N only — HyperTTS batches')
    ap.add_argument('--all', action='store_true', help='include Latin-only and reference forms')
    args = ap.parse_args()
    if not (args.words or args.sentences):
        raise SystemExit('pick --words or --sentences')

    data = load_dataset(os.path.join(ROOT, args.data))
    tag = data.get('tag', 'x')
    base = args.audio_dir or (data.get('clips', '').replace('../', '') or f'{tag}/audio/words')
    sent_dir = os.path.dirname(base.rstrip('/')) or f'{tag}/audio'

    if args.words:
        have = existing([base, 'ministories/audio/words', 'intensive/audio/words'])
        rows, skipped, latin, ref = [], 0, 0, 0
        for l in data['lex']:
            if l['g'] in have:
                skipped += 1
                continue
            if not args.all and not TELUGU.search(l['te']):
                latin += 1
                continue
            if not args.all and l.get('ref'):
                ref += 1
                continue
            rows.append([l['g'], l['te'], '', l.get('en', '')])
        total = len(rows)
        if args.limit:
            rows = rows[:args.limit]
        out = os.path.join(ROOT, args.out or f'{tag}_hypertts_words.tsv')
        write_tsv(out, rows)
        print(f'{os.path.relpath(out, ROOT)}  {len(rows)} of {total} pending words')
        print(f'  skipped: {skipped} already recorded, {latin} Latin-only, {ref} reference-only')
        dest = base
        print(f'  clips belong in {base}/')
    else:
        have = existing([sent_dir])
        rows, skipped = [], 0
        for st in data['stories']:
            for ln in st['lines']:
                te = ''.join(t[0] for t in ln['t'])
                if not te.strip() or not TELUGU.search(te):
                    continue
                if ln['g'] in have:
                    skipped += 1
                    continue
                rows.append([ln['g'], te, '', ln.get('en', '')])
        total = len(rows)
        if args.limit:
            rows = rows[:args.limit]
        out = os.path.join(ROOT, args.out or f'{tag}_hypertts_sentences.tsv')
        write_tsv(out, rows)
        print(f'{os.path.relpath(out, ROOT)}  {len(rows)} of {total} pending sentences')
        print(f'  skipped: {skipped} already recorded')
        dest = sent_dir
        print(f'  clips belong in {sent_dir}/')

    print()
    print('  In Anki: File > Import, then HyperTTS batch on the `telugu` field into `audio`,')
    print('  then export the deck as plain text and run tools/ms_hypertts_import.py --from-anki')
    print(f'  --dest {dest} to file the clips by guid.')


if __name__ == '__main__':
    main()
