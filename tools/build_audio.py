# -*- coding: utf-8 -*-
"""Build commute audio tracks from the audio HyperTTS generated in Anki.

    brew install ffmpeg
    python3 tools/build_audio.py --track shadow --sets 1-4
    python3 tools/build_audio.py --track production --sets 1-4 --speed 1.0
    python3 tools/build_audio.py --track comprehension --sets 1-2

Writes one MP3 per set into audio/, tagged as an album so it appears in Apple Music /
CarPlay as an ordered track list. No phone interaction while driving; steering-wheel
controls skip and rewind.

WHY THREE TRACK TYPES

Driving is partial attention. That matters more than it sounds, because the study
techniques differ in how much attention they need:

  shadow         Telugu -> gap -> Telugu -> gap -> Telugu. Imitation, not recall. Builds
                 articulation and prosody. Attention-cheap, so it survives traffic — the
                 best fit for a car, and the default.
  production     English -> gap -> Telugu -> shadow -> shadow. This is retrieval practice,
                 which is the single most attention-hungry thing you can do and the thing
                 that most rewards full attention. It works in the car, but it is the least
                 efficient use of car time and you cannot tell when you were wrong.
                 Best on material already drilled at the desk.
  comprehension  Telugu -> gap -> English. Trains understanding rather than production, and
                 is the bridge toward real comprehensible input.

WHY IT ONLY USES CARDS YOU HAVE ALREADY SEEN

Audio-only exposure to language you have never studied is close to worthless at beginner
level — you cannot segment what you cannot yet parse. By default only cards already in
review are included, so the commute is the second exposure and does consolidation work.
--include-new overrides this.
"""
import argparse, csv, io, os, re, shutil, sqlite3, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'audio')
COL = os.path.expanduser('~/Library/Application Support/Anki2/User 1/collection.anki2')
MEDIA = os.path.expanduser('~/Library/Application Support/Anki2/User 1/collection.media')

SOUND = re.compile(r'\[sound:([^\]]+)\]')

# (source field, gap in seconds after it) — the shape of one item in each track type
LAYOUTS = {
    'shadow':        [('te', 2.5), ('te', 2.5), ('te', 3.0)],
    'production':    [('en', 6.0), ('te', 2.0), ('te', 2.0), ('te', 3.0)],
    'comprehension': [('te', 4.0), ('en', 2.0)],
}


def need_ffmpeg():
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg not found. Install it with:  brew install ffmpeg')


def load_notes():
    """guid -> {en: media file, te: media file, tags}. Reads a copy; never touches the live
    collection."""
    if not os.path.exists(COL):
        sys.exit(f'no collection at {COL}')
    tmp = tempfile.mkdtemp()
    snap = os.path.join(tmp, 'col.anki2')
    shutil.copy2(COL, snap)
    for ext in ('-wal', '-shm'):
        if os.path.exists(COL + ext):
            shutil.copy2(COL + ext, snap + ext)
    db = sqlite3.connect(f'file:{snap}?mode=ro', uri=True)
    db.create_collation('unicase', lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))
    db.row_factory = sqlite3.Row

    nt = db.execute("select id from notetypes where name='Telugu Sentence v3'").fetchone()
    if not nt:
        sys.exit("note type 'Telugu Sentence v3' not found — import first")
    names = [r['name'] for r in
             db.execute('select name from fields where ntid=? order by ord', (nt['id'],))]
    need = {'EnglishAudio', 'Audio'}
    if not need <= set(names):
        sys.exit(f'note type is missing {sorted(need - set(names))} — see anki/IMPORT.md')
    iEn, iTe = names.index('EnglishAudio'), names.index('Audio')

    out = {}
    for n in db.execute('select id, guid, flds, tags from notes where mid=?', (nt['id'],)):
        vals = n['flds'].split('\x1f')
        grab = lambda i: (SOUND.search(vals[i]).group(1) if i < len(vals) and SOUND.search(vals[i]) else '')
        reps = db.execute('select max(reps) from cards where nid=?', (n['id'],)).fetchone()[0] or 0
        out[n['guid']] = {'en': grab(iEn), 'te': grab(iTe),
                          'tags': (n['tags'] or '').split(), 'reps': reps}
    db.close(); shutil.rmtree(tmp, ignore_errors=True)
    return out


def silence(path, secs):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', f'anullsrc=r=24000:cl=mono', '-t', f'{secs}',
                    '-c:a', 'libmp3lame', '-q:a', '5', path], check=True)


def build(track, items, dest, album, title, speed):
    tmp = tempfile.mkdtemp()
    gaps = {}
    parts = []
    for it in items:
        for field, gap in LAYOUTS[track]:
            f = it.get(field)
            if not f:
                continue
            p = os.path.join(MEDIA, f)
            if not os.path.exists(p):
                continue
            parts.append(p)
            if gap not in gaps:
                gaps[gap] = os.path.join(tmp, f'sil{gap}.mp3')
                silence(gaps[gap], gap)
            parts.append(gaps[gap])
    if not parts:
        shutil.rmtree(tmp, ignore_errors=True)
        return 0

    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write("file '" + p.replace("'", "'\\''") + "'\n")
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst]
    if speed and abs(speed - 1.0) > 0.01:
        cmd += ['-filter:a', f'atempo={speed}']
    cmd += ['-c:a', 'libmp3lame', '-q:a', '5',
            '-metadata', f'album={album}', '-metadata', f'title={title}',
            '-metadata', 'artist=Road to Telugu', '-metadata', f'genre=Language', dest]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return len(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--track', choices=sorted(LAYOUTS), default='shadow')
    ap.add_argument('--sets', default='1-4', help='set numbers, e.g. 1-4 or 3')
    ap.add_argument('--speed', type=float, default=1.0, help='1.0, or 1.15 once comfortable')
    ap.add_argument('--include-new', action='store_true',
                    help='include cards never reviewed (not recommended — see module docstring)')
    a = ap.parse_args()
    need_ffmpeg()

    lo, _, hi = a.sets.partition('-')
    wanted = {f'set::{n:03d}' for n in range(int(lo), int(hi or lo) + 1)}

    notes = load_notes()
    master = {r['id']: r for r in csv.DictReader(
        open(os.path.join(ROOT, 'data', 'master_sentences.tsv'), encoding='utf-8'), delimiter='\t')}

    by_set = {}
    skipped_new = skipped_audio = 0
    for guid, n in notes.items():
        tag = next((t for t in n['tags'] if t.startswith('set::')), None)
        if tag not in wanted:
            continue
        if not a.include_new and n['reps'] == 0:
            skipped_new += 1; continue
        if not n['te']:
            skipped_audio += 1; continue
        if a.track != 'shadow' and not n['en']:
            skipped_audio += 1; continue
        by_set.setdefault(tag, []).append((guid, n))

    if not by_set:
        print('nothing to build.')
        print(f'  {skipped_new} cards skipped as never reviewed (use --include-new to override)')
        print(f'  {skipped_audio} skipped for missing audio — run HyperTTS first, see anki/IMPORT.md')
        return

    os.makedirs(OUT, exist_ok=True)
    album = f'Telugu {a.track}'
    total = 0
    for i, (tag, rows) in enumerate(sorted(by_set.items()), 1):
        rows.sort(key=lambda gn: master.get(gn[0], {}).get('id', gn[0]))
        name = f'{a.track}-{tag.split("::")[1]}' + (f'-{a.speed:g}x' if a.speed != 1.0 else '')
        dest = os.path.join(OUT, name + '.mp3')
        n = build(a.track, [n for _, n in rows], dest, album, name, a.speed)
        print(f'  {os.path.relpath(dest, ROOT):<40} {len(rows):>4} sentences')
        total += len(rows)
    print(f'\n{total} sentences across {len(by_set)} track(s) -> {os.path.relpath(OUT, ROOT)}/')
    if skipped_new:
        print(f'{skipped_new} skipped as never reviewed — study them at the desk first')
    if skipped_audio:
        print(f'{skipped_audio} skipped for missing audio')


if __name__ == '__main__':
    main()
