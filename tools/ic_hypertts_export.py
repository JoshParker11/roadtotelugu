# -*- coding: utf-8 -*-
"""Export Intensive Course turns and words for audio generation through Anki + HyperTTS.

    python3 tools/ic_hypertts_export.py                # turns with no current clip
    python3 tools/ic_hypertts_export.py --words        # the distinct-word manifest instead
    python3 tools/ic_hypertts_export.py --lessons 1-6  # a workable batch
    python3 tools/ic_hypertts_export.py --all          # everything, current clips included

Writes intensive/hypertts_export.tsv. Same shape and same round trip as
tools/ms_hypertts_export.py — guid first so it survives Anki unchanged — and the import side is
tools/ms_hypertts_import.py pointed at intensive/audio/.

WHY LESSONS 1-6 ARE THE BATCH TO RUN FIRST
Their Telugu is derived from the book's own romanization and round-trips back to it exactly.
Lessons 7-64 are OCR at ~93%, and 2.6% of turns are flagged ocr-suspect; voicing a line before
anyone has read it means paying to synthesize a wrong sentence and then hearing it as if it
were right. --lessons is there so the verified material can be voiced now and the rest waits.

STALE COUNTS AS MISSING
A clip whose text has since changed is not this turn's audio. The manifest in
intensive/audio_manifest.tsv records what each clip was made from, exactly as the mini stories
do, so re-exporting after a better OCR pass targets only what actually moved.
"""
import argparse
import csv
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from msfiles import work_tsvs

IC = os.path.join(ROOT, 'intensive')
WORK = os.path.join(IC, 'work')
AUDIO = os.path.join(IC, 'audio')
MANIFEST = os.path.join(IC, 'audio_manifest.tsv')
OUT = os.path.join(IC, 'hypertts_export.tsv')


def voiced():
    if not os.path.exists(MANIFEST):
        return {}
    with open(MANIFEST, encoding='utf-8') as f:
        return {r['guid']: r['te_sha1'] for r in csv.DictReader(f, delimiter='\t')}


def is_stale(guid, te, have):
    if not os.path.exists(os.path.join(AUDIO, guid + '.mp3')):
        return True
    want = hashlib.sha1(te.strip().encode('utf-8')).hexdigest()[:16]
    return have.get(guid) != want


def parse_lessons(spec):
    out = set()
    for part in spec.split(','):
        if '-' in part:
            a, b = part.split('-')
            out |= set(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words', action='store_true')
    ap.add_argument('--lessons')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--verified', action='store_true',
                    help='only turns whose Telugu came from the book, not from OCR')
    args = ap.parse_args()

    want = parse_lessons(args.lessons) if args.lessons else None
    have = voiced()
    rows, seen, skipped, unverified = [], set(), 0, 0
    for p in work_tsvs(WORK):
        with open(p, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if not r['te'].strip() or not r.get('guid'):
                    continue
                if want and int(r['lesson']) not in want:
                    continue
                if args.verified and r.get('te_src') != 'rom':
                    unverified += 1
                    continue
                if r['guid'] in seen:
                    continue
                seen.add(r['guid'])
                if not args.all and not is_stale(r['guid'], r['te'], have):
                    skipped += 1
                    continue
                rows.append((r['guid'], r['te'], '', r['en']))

    if args.words:
        sys.exit('--words needs a distinct-word manifest for the course; '
                 'build_ic_reader.py does not write one yet (see status.py NEXT).')
    if skipped:
        print(f'{skipped} turn(s) already have a current clip — not re-exported (--all overrides)')
    if unverified:
        print(f'{unverified} turn(s) skipped as OCR-sourced (--verified)')
    if not rows:
        print('Nothing to export in that scope.')
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerows(rows)
    print(f'{len(rows)} turn(s) -> {os.path.relpath(OUT, ROOT)}')
    print('Import into Anki as a 4-field note type (guid / telugu / audio / english), point '
          "HyperTTS's batch generator at telugu -> audio, run it, then export the notes as "
          'plain text and hand that file to tools/ms_hypertts_import.py with --dest '
          'intensive/audio.')


if __name__ == '__main__':
    main()
