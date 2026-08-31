# -*- coding: utf-8 -*-
"""One view of what is done, what is outstanding, and what to generate next.

    python3 tools/status.py

There are two corpora, three kinds of artefact (translation, definition, audio) and two audio
paths, and the state of all of it was previously only discoverable by running six tools and
holding the answers in your head. That is how a status tally came back 40% too high, and how
423 lines kept audio of a translation they no longer had.

Nothing here computes anything new. Every number is read from the file that owns it, so this
cannot drift from what the pipeline actually does.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from msfiles import work_tsvs, sweep
import ms_audio

MS = os.path.join(ROOT, 'ministories')
IC = os.path.join(ROOT, 'intensive')


def rows_of(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def bar(n, total, width=28):
    if not total:
        return ''
    fill = int(round(width * n / total))
    return '[' + '#' * fill + '.' * (width - fill) + f'] {n}/{total} ({n / total:.0%})'


def main():
    print('MINI STORIES')
    seg = [r for p in work_tsvs(os.path.join(MS, 'work')) for r in rows_of(p)]
    done = [r for r in seg if r['te'].strip()]
    native = [r for r in seg if r['status'] == 'native']
    print(f'  translated     {bar(len(done), len(seg))}')
    print(f'  native-sourced {bar(len(native), len(seg))}')
    stale = [r for r in done if ms_audio.is_stale(r)]
    print(f'  sentence audio {bar(len(done) - len(stale), len(done))}'
          f'{"  <- " + str(len(stale)) + " to generate" if stale else ""}')
    wm = os.path.join(MS, 'word_audio.tsv')
    if os.path.exists(wm):
        words = rows_of(wm)
        wdir = os.path.join(MS, 'audio', 'words')
        have = sum(1 for r in words if os.path.exists(os.path.join(wdir, r['guid'] + '.mp3')))
        print(f'  word audio     {bar(have, len(words))}'
              f'{"  <- " + str(len(words) - have) + " to generate" if have < len(words) else ""}')

    print('\nINTENSIVE COURSE')
    ic = [r for p in sorted(work_tsvs(os.path.join(IC, 'work'))) for r in rows_of(p)]
    if ic:
        with_te = [r for r in ic if r['te'].strip()]
        frombook = [r for r in ic if r.get('te_src') == 'rom']
        flagged = [r for r in ic if 'ocr-suspect' in (r.get('flags') or '')]
        print(f'  has Telugu     {bar(len(with_te), len(ic))}')
        print(f'  book-verified  {bar(len(frombook), len(ic))}   the rest is OCR at ~93%')
        print(f'  needs a look   {len(flagged)} flagged ocr-suspect')
        icaudio = os.path.join(IC, 'audio')
        have = sum(1 for r in with_te
                   if os.path.exists(os.path.join(icaudio, r['guid'] + '.mp3'))) if os.path.exists(icaudio) else 0
        print(f'  sentence audio {bar(have, len(with_te))}'
              f'{"  <- " + str(len(with_te) - have) + " to generate" if have < len(with_te) else ""}')
    vocab = os.path.join(IC, 'raw', 'vocab.tsv')
    if os.path.exists(vocab):
        print(f"  book glossary  {len(rows_of(vocab))} headwords harvested from the VOCABULARY lists")

    print('\nREPO')
    hits = sweep(ROOT)
    print(f'  iCloud conflict copies: {len(hits) or "none"}')

    print('\nNEXT')
    if stale:
        print(f'  python3 tools/ms_hypertts_export.py            # {len(stale)} story sentences')
    print( '  python3 tools/ms_hypertts_export.py --words     # word clips')
    if ic:
        print( '  python3 tools/ic_hypertts_export.py             # course sentences')


if __name__ == '__main__':
    main()
