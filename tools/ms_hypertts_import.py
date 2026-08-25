# -*- coding: utf-8 -*-
"""Pull HyperTTS-generated audio out of Anki and into ministories/audio/, by guid.

    python3 tools/ms_hypertts_import.py exported.tsv          # locate collection.media itself
    python3 tools/ms_hypertts_import.py exported.tsv --media /path/to/collection.media

`exported.tsv` is what Anki's "Export Notes... > Notes in Plain Text" writes after you have run
HyperTTS's batch generator on the file from tools/ms_hypertts_export.py — same four columns
(guid, telugu, audio, english), with `audio` now holding Anki's `[sound:NAME.mp3]` tag instead of
being empty.

WHY THIS COPIES RATHER THAN MOVES
Anki's media collection is not ours to edit — another note somewhere might reference the same
audio file, and Anki's own database expects it to still be there. Copying into
ministories/audio/<guid>.mp3 leaves Anki's collection untouched and gives this project its own
independent copy, matching every other guid-keyed artefact here.

WHY --media IS OPTIONAL
Anki's profile directory name (`User 1` by default) is not fixed, and some setups have more than
one profile. Auto-detection walks every `Anki2/*/collection.media` it can find and asks if there
is more than one; --media skips the search entirely once you know the path.
"""
import argparse
import csv
import glob
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
AUDIO = os.path.join(ROOT, 'ministories', 'audio')

SOUND = re.compile(r'\[sound:([^\]]+)\]')
# Our guids: ids.py emits a one-letter prefix + 12 hex — 'M' for Mini Story segments, 'W' for
# word headwords, 'S' for sentences elsewhere in the repo. A row that doesn't match is not one of
# ours, most likely a pre-existing card swept in because Anki's plain-text export works on a whole
# deck rather than just the notes from one import (seen on a real export: an unrelated vocabulary
# card sitting in the same file). Without this check its first field would be read as a 'guid' and,
# if its audio column happened to hold a [sound:...] tag, copied in under a garbage filename.
# 'W' was missing from this class originally, which would have made a word-audio import silently
# discard every row it was given — the filter is meant to reject foreign notes, not our own clips.
GUID = re.compile(r'^[MSW][0-9a-f]{12}$')


def find_media():
    candidates = sorted(set(
        glob.glob(os.path.expanduser('~/Library/Application Support/Anki2/*/collection.media'))
        + glob.glob(os.path.expanduser('~/.local/share/Anki2/*/collection.media'))
        + glob.glob(os.path.expanduser('~/AppData/Roaming/Anki2/*/collection.media'))
    ))
    if not candidates:
        sys.exit("Couldn't find an Anki collection.media folder. Pass --media <path> directly — "
                 "it's inside your Anki profile folder, named after the profile "
                 "(commonly 'User 1').")
    if len(candidates) > 1:
        sys.exit('Found more than one Anki profile:\n  ' + '\n  '.join(candidates) +
                 '\nPass --media <path> to pick one.')
    return candidates[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exported', help='the file Anki wrote via Export Notes > Plain Text')
    ap.add_argument('--media', help='path to Anki\'s collection.media (auto-detected if omitted)')
    ap.add_argument('--force', action='store_true', help='overwrite audio already in the repo')
    ap.add_argument('--words', action='store_true',
                    help='these are per-headword clips; write them to audio/words/ instead')
    args = ap.parse_args()

    media = args.media or find_media()
    if not os.path.isdir(media):
        sys.exit(f'{media} is not a directory')

    with open(args.exported, encoding='utf-8') as f:
        lines = [l for l in f if not l.startswith('#')]
    rows = list(csv.reader(lines, delimiter='\t'))

    # Word clips live in their own subdirectory because they are keyed by WORD guid, not segment
    # guid — two different id spaces that must not share a namespace on disk.
    out_dir = os.path.join(AUDIO, 'words') if args.words else AUDIO
    os.makedirs(out_dir, exist_ok=True)
    copied = skipped = no_audio = missing_file = bad_row = foreign = 0
    for row in rows:
        if len(row) < 3:
            bad_row += 1
            continue
        guid, _telugu, audio = row[0].strip(), row[1], row[2]
        if not GUID.match(guid):
            foreign += 1     # not one of ours — see the GUID comment above
            continue
        m = SOUND.search(audio)
        if not m:
            no_audio += 1
            continue
        src = os.path.join(media, m.group(1))
        dst = os.path.join(out_dir, guid + '.mp3')
        if not os.path.exists(src):
            print(f'MISSING  {guid}  expected {m.group(1)} in collection.media, not found')
            missing_file += 1
            continue
        if os.path.exists(dst) and not args.force:
            skipped += 1
            continue
        shutil.copyfile(src, dst)
        copied += 1

    print(f'-> {out_dir}')
    print(f'copied {copied}, skipped {skipped} (already had audio), '
         f'{no_audio} had no [sound:...] tag yet, {missing_file} referenced a missing file, '
         f'{foreign} row(s) were not one of ours (foreign guid, ignored), '
         f'{bad_row} malformed row(s)')
    if no_audio:
        print('Rows with no audio tag means HyperTTS has not been run on them yet, or the '
             'export happened before the batch job finished.')


if __name__ == '__main__':
    main()
