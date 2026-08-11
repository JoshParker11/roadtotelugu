# -*- coding: utf-8 -*-
"""Export the existing Anki collection to a flat snapshot for ingest.

    python3 tools/export_anki.py

Reads a *copy* of collection.anki2 — the live collection is never opened for writing and
never modified. Anki may be running; the write-ahead log is copied alongside so the snapshot
is consistent.

Three generations of note type accumulated in the collection, each naming its fields
differently. The ROLES table maps each one onto the canonical roles so they can all merge.
Two fields exist nowhere else in the project and are worth preserving:

  Pronunciation/Pronounce   syllable-stress guide, hand-made: "nēnu" -> "NAY-noo"
  Rank / Island             a frequency ordering and a topic grouping

Output: sources/private/anki_notes.tsv (gitignored — it is a dump of a personal collection).
"""
import csv, os, re, shutil, sqlite3, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'sources', 'private', 'anki_notes.tsv')
COL = os.path.expanduser('~/Library/Application Support/Anki2/User 1/collection.anki2')

# note type -> {role: field name}. kind says which master it feeds.
ROLES = {
 'Telugu Vocab':       dict(kind='word', en='English', rom='PRS',        te='Telugu',
                            pron='Pronounce',     island='Family', rank='Rank'),
 'Telugu Vocab v2':    dict(kind='word', en='English', rom='Romanized',  te='Telugu',
                            pron='Pronunciation', island='Island', rank='Rank'),
 'Telugu Production':  dict(kind='word', en='English', rom='Romanized',  te='TeluguScript',
                            example='Example'),
 'Word':               dict(kind='word', en='English', rom='Transliteration', te='Telugu'),
 'Telugu Sentence':    dict(kind='sentence', en='English', rom='PRS',       te='Telugu',
                            pron='Pronounce',     island='Island'),
 'Telugu Sentence v2': dict(kind='sentence', en='English', rom='Romanized', te='Telugu',
                            pron='Pronunciation', island='Island'),
 'Telugu Sentence v3': dict(kind='sentence', en='English', rom='Romanized', te='Telugu',
                            notes='Notes'),
 'Phrase':             dict(kind='sentence', en='English', rom='Transliteration', te='Telugu'),
}

TAG_RE = re.compile(r'<[^>]+>')
SOUND_RE = re.compile(r'\[sound:[^\]]*\]')


def clean(v):
    """Strip the HTML and [sound:] markers Anki stores inline."""
    v = SOUND_RE.sub('', v or '')
    v = v.replace('<br>', ' ').replace('<br/>', ' ').replace('&nbsp;', ' ')
    v = TAG_RE.sub('', v)
    v = (v.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
          .replace('&quot;', '"').replace('&#39;', "'"))
    return re.sub(r'\s+', ' ', v).strip()


def main():
    if not os.path.exists(COL):
        print(f'no collection at {COL}'); return
    tmp = tempfile.mkdtemp()
    snap = os.path.join(tmp, 'col.anki2')
    shutil.copy2(COL, snap)
    for ext in ('-wal', '-shm'):
        if os.path.exists(COL + ext):
            shutil.copy2(COL + ext, snap + ext)

    db = sqlite3.connect(f'file:{snap}?mode=ro', uri=True)
    db.create_collation('unicase', lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))
    db.row_factory = sqlite3.Row

    rows, skipped = [], {}
    for nt in db.execute('select id, name from notetypes'):
        spec = ROLES.get(nt['name'])
        n = db.execute('select count(*) from notes where mid=?', (nt['id'],)).fetchone()[0]
        if not spec:
            if n: skipped[nt['name']] = n
            continue
        names = [r['name'] for r in
                 db.execute('select name from fields where ntid=? order by ord', (nt['id'],))]
        idx = {role: names.index(f) for role, f in spec.items()
               if role != 'kind' and f in names}
        for note in db.execute('select id, flds, tags from notes where mid=?', (nt['id'],)):
            vals = note['flds'].split('\x1f')
            get = lambda role: clean(vals[idx[role]]) if role in idx and idx[role] < len(vals) else ''
            te, en = get('te'), get('en')
            if not te and not en:
                continue
            rows.append({'kind': spec['kind'], 'notetype': nt['name'], 'nid': note['id'],
                         'english': en, 'raw_rom': get('rom'), 'telugu': te,
                         'pronunciation': get('pron'), 'island': get('island'),
                         'rank': get('rank'), 'example': get('example'),
                         'notes': get('notes'), 'tags': (note['tags'] or '').strip()})
    db.close(); shutil.rmtree(tmp, ignore_errors=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cols = ['kind', 'notetype', 'nid', 'english', 'raw_rom', 'telugu', 'pronunciation',
            'island', 'rank', 'example', 'notes', 'tags']
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

    from collections import Counter
    print(f'exported {len(rows)} notes -> {os.path.relpath(OUT, ROOT)}')
    for k, v in sorted(Counter(r['notetype'] for r in rows).items()):
        kind = ROLES[k]['kind']
        script = sum(1 for r in rows if r['notetype'] == k and r['telugu'])
        pron = sum(1 for r in rows if r['notetype'] == k and r['pronunciation'])
        print(f'  {k:<22} {v:>5} {kind:<9} script:{script:<5} pronunciation:{pron}')
    if skipped:
        print('  not mapped:', dict(skipped))


if __name__ == '__main__':
    main()
