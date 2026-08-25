# -*- coding: utf-8 -*-
"""Export translated segments to a TSV that Anki's importer and HyperTTS's batch generator
can drive, as an alternative to tools/ms_audio.py's direct Azure calls.

    python3 tools/ms_hypertts_export.py            # everything translated so far
    python3 tools/ms_hypertts_export.py --num 1     # one story

Writes ministories/hypertts_export.tsv. That file is the input to a manual step in Anki — see
ministories/README.md "Audio via HyperTTS" for the exact import/batch/export sequence — and
tools/ms_hypertts_import.py is what reads Anki's output back into ministories/audio/.

WHY THIS PATH EXISTS ALONGSIDE ms_audio.py
Two ways to get Azure Neural Telugu audio: call Azure directly with your own Speech resource
(ms_audio.py, fully scripted), or generate it through HyperTTS Pro, which already includes Azure
under a subscription you are already paying for and needs no separate account (this path, with
one manual step in the Anki GUI). Both end up at the same file layout — one mp3 per guid in
ministories/audio/ — so everything downstream of audio generation does not care which was used.

WHY guid IS COLUMN ONE
Anki's plain-text importer keeps column order, and the guid has to survive the round trip through
Anki completely unchanged so ms_hypertts_import.py can match the exported audio back to the right
segment. `en` rides along as a fourth column purely so you have the English on screen while
working in Anki — HyperTTS is never pointed at it.

WHY THIS DEDUPLICATES BY GUID
The retell-boilerplate line ("Here is the same story told in a different way.") is deliberately
keyed on one shared guid across all 60 lessons (DECISIONS.md #3), and the moment it is translated
once, ms_apply.py writes that translation into every lesson file that carries it — including the
55 lessons that are otherwise still untranslated. A naive export picks up that one row 60 times
over: once verified on a real run, all 60 happened to resolve to the identical HyperTTS-cached
audio file, so nothing was actually wasted — but that was the TTS provider's caching saving us,
not something this script should depend on. Deduplicating here means Anki only ever sees one note
for one guid, however many lessons reference it.
"""
import argparse
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
CATALOG = os.path.join(MS, 'CATALOG.tsv')
OUT = os.path.join(MS, 'hypertts_export.tsv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', help='only this story number')
    args = ap.parse_args()

    with open(CATALOG, encoding='utf-8') as f:
        cat = {r['id']: r for r in csv.DictReader(f, delimiter='\t')}

    seen, rows, dupes = {}, [], 0
    for path in sorted(glob.glob(os.path.join(WORK, '*.tsv'))):
        sid = os.path.basename(path)[:-4]
        if args.num and int(cat[sid]['num']) != int(args.num):
            continue
        with open(path, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if not r['te'].strip():
                    continue
                if r['guid'] in seen:
                    dupes += 1
                    continue
                seen[r['guid']] = True
                rows.append((r['guid'], r['te'], '', r['en']))

    if not rows:
        print('Nothing translated yet in that scope.')
        return
    if dupes:
        print(f'({dupes} row(s) skipped — same guid already included, most likely shared '
              'boilerplate carried into other lessons)')

    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        # #separator / #html / #notetype-ish directives are for Anki's newer importer; harmless
        # if your Anki version ignores them, in which case just map columns by hand on import.
        f.write('#separator:tab\n#html:false\n#columns:guid\ttelugu\taudio\tenglish\n')
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerows(rows)

    print(f'{len(rows)} segment(s) -> {OUT}')
    print('Import into Anki as a 4-field note type (guid / telugu / audio / english), point '
         "HyperTTS's batch generator at telugu -> audio with a Telugu voice, run it, then "
         "File > Export Notes in Plain Text (same 4 fields, tab-separated) and hand that file "
         'to tools/ms_hypertts_import.py.')


if __name__ == '__main__':
    main()
