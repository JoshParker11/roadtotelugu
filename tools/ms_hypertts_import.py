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
import hashlib
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
# Then 'I' was added for the Intensive Course and this rejected all 173 rows of the first import,
# the same failure a second time. So the letter is no longer enumerated: the SHAPE is what
# identifies one of ours, and a new corpus must not require editing a file it has nothing to do
# with. A foreign Anki note's first field is a word or a sentence, not a capital plus twelve hex.
GUID = re.compile(r'^[A-Z][0-9a-f]{12}$')


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


def manifest_path(base):
    """The manifest sits BESIDE the audio directory, never inside it.

    One function so the reader and the writer cannot disagree about where it lives — they did,
    which made every clip look current because the file the check opened was never there.
    """
    return os.path.join(os.path.dirname(os.path.normpath(base)), 'audio_manifest.tsv')


def _stale(dst, guid, telugu, base):
    """True when the clip on disk was made from different text than this row carries."""
    man = manifest_path(base)
    if not os.path.exists(man):
        return False                     # nothing recorded — assume what is there is current
    with open(man, encoding='utf-8') as f:
        have = {r['guid']: r['te_sha1'] for r in csv.DictReader(f, delimiter='\t')}
    want = hashlib.sha1((telugu or '').strip().encode('utf-8')).hexdigest()[:16]
    return have.get(guid) != want


def rows_from_anki(profile=None):
    """Read the notes straight out of Anki's collection, skipping the export step.

    WHY THIS EXISTS
    "File > Export > Notes in Plain Text" is a hand-driven step with several silent failure
    modes, and two of them have already cost a round trip: an export whose field order came
    from a different note type, and an export of 41 bytes — three header lines and no notes at
    all, because the dialog had nothing selected. The audio was generated and attached both
    times; only the handover failed.

    The collection is a SQLite database. Fields are \x1f-separated, the guid is the first, and
    the [sound:] tag is wherever HyperTTS put it — so it is searched for rather than assumed to
    be column three. Read from a COPY: Anki keeps the live file open, and this must never be
    the process that touches it.
    """
    import shutil as _sh, sqlite3, tempfile
    base = profile or os.path.join(os.path.expanduser('~'), 'Library', 'Application Support',
                                   'Anki2', 'User 1')
    src = os.path.join(base, 'collection.anki2')
    if not os.path.exists(src):
        sys.exit(f'no Anki collection at {src} — pass --profile <dir>')
    tmp = os.path.join(tempfile.mkdtemp(), 'collection.anki2')
    _sh.copy2(src, tmp)
    db = sqlite3.connect(f'file:{tmp}?mode=ro', uri=True)
    out = []
    for (flds,) in db.execute('select flds from notes'):
        f = flds.split('\x1f')
        if not f or not GUID.match(f[0].strip()):
            continue
        sound = next((x for x in f if SOUND.search(x)), '')
        out.append([f[0].strip(), f[1] if len(f) > 1 else '', sound])
    db.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exported', nargs='?',
                    help='the file Anki wrote via Export Notes > Plain Text')
    ap.add_argument('--from-anki', action='store_true',
                    help="read Anki's collection directly instead of an export file")
    ap.add_argument('--profile', help='Anki profile directory (default: User 1)')
    ap.add_argument('--media', help='path to Anki\'s collection.media (auto-detected if omitted)')
    ap.add_argument('--force', action='store_true', help='overwrite audio already in the repo')
    ap.add_argument('--words', action='store_true',
                    help='these are per-headword clips; write them to audio/words/ instead')
    ap.add_argument('--dest', help='write into this audio directory instead of ministories/audio '
                                   '(use intensive/audio for the Intensive Course)')
    args = ap.parse_args()

    media = args.media or find_media()
    if not os.path.isdir(media):
        sys.exit(f'{media} is not a directory')

    if args.from_anki:
        rows = rows_from_anki(args.profile)
        # THE COLLECTION HOLDS EVERY CORPUS AT ONCE, so reading it directly has to filter by
        # what the destination is for. An export file was implicitly one batch; this is not.
        # Without the filter, --words swept mini-story segments and course sentences into
        # audio/words/ under ids that directory's reader will never look up.
        want = 'W' if args.words else 'MI'
        before = len(rows)
        rows = [r for r in rows if r[0][:1] in want]
        print(f'{before} note(s) in the collection · {len(rows)} match this destination '
              f'({"word" if args.words else "segment"} ids)')
    else:
        if not args.exported:
            sys.exit('give an export file, or pass --from-anki to read the collection directly')
        with open(args.exported, encoding='utf-8') as f:
            lines = [l for l in f if not l.startswith('#')]
        rows = list(csv.reader(lines, delimiter='\t'))
        if not rows:
            sys.exit(f'{args.exported} contains no notes — the export dialog produced only '
                     'headers. Re-export with the notes selected, or use --from-anki.')

    # Word clips live in their own subdirectory because they are keyed by WORD guid, not segment
    # guid — two different id spaces that must not share a namespace on disk.
    base = os.path.abspath(args.dest) if args.dest else AUDIO
    out_dir = os.path.join(base, 'words') if args.words else base
    os.makedirs(out_dir, exist_ok=True)
    copied = skipped = no_audio = missing_file = bad_row = foreign = 0
    voiced_text = {}
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
        # STALE IS NOT DONE. Skipping on file existence alone is what left 291 segments
        # holding audio of the previous translation while the export had correctly asked for
        # new clips: the file was there, so the import declined to replace it. A clip counts
        # as present only if the manifest says it was made from the text we are importing now.
        if os.path.exists(dst) and not args.force and not _stale(dst, guid, _telugu, base):
            skipped += 1
            continue
        shutil.copyfile(src, dst)
        # Recorded HERE, after the copy — not when the row was parsed. Recording on parse
        # marked skipped rows as voiced with text their file does not contain, which made the
        # manifest assert the opposite of the truth for 291 segments.
        voiced_text[guid] = _telugu
        copied += 1

    print(f'-> {out_dir}')

    # The clip alone does not say which Telugu is inside it, and a segment id is derived from
    # the English, so a re-translated line keeps pointing at the old audio. Recording the text
    # each clip was made from is what lets build_ms_reader withhold audio that has gone stale
    # instead of playing the previous wording under the new text.
    if copied and not args.words:
        man = manifest_path(base)
        prev = {}
        if os.path.exists(man):
            with open(man, encoding='utf-8') as f:
                prev = {r['guid']: r['te_sha1'] for r in csv.DictReader(f, delimiter='\t')}
        for g, te in voiced_text.items():
            prev[g] = hashlib.sha1((te or '').strip().encode('utf-8')).hexdigest()[:16]
        with open(man, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['guid', 'te_sha1'])
            w.writerows(sorted(prev.items()))
        print(f'audio manifest updated: {os.path.relpath(man, ROOT)}')

    print(f'copied {copied}, skipped {skipped} (already had audio), '
         f'{no_audio} had no [sound:...] tag yet, {missing_file} referenced a missing file, '
         f'{foreign} row(s) were not one of ours (foreign guid, ignored), '
         f'{bad_row} malformed row(s)')
    if no_audio:
        print('Rows with no audio tag means HyperTTS has not been run on them yet, or the '
             'export happened before the batch job finished.')


if __name__ == '__main__':
    main()
