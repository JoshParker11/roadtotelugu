# -*- coding: utf-8 -*-
"""Hand corrections that survive a rebuild.

The masters are generated from the adapters, so editing data/master_*.tsv directly is
pointless — the next `python3 tools/build_master.py` overwrites it. This is where a fix
goes instead. Overrides are applied last, after merging and after gloss resolution.

    data/overrides_words.tsv
    data/overrides_sentences.tsv

Columns: telugu, action, english, example, notes, reason

  action = edit   replace any non-empty column given; blanks leave the generated value
           drop   remove the entry entirely (it should not be a card)

`telugu` is the match key because the script is the anchor everywhere else in the pipeline.
`reason` is for you, six months from now, wondering why a card looks like that.
"""
import csv, os

COLS = ['telugu', 'action', 'english', 'example', 'notes', 'reason']


def _load(path):
    if not os.path.exists(path):
        return {}
    out = {}
    for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'):
        te = (r.get('telugu') or '').strip()
        if not te or te.startswith('#'):
            continue
        out[te] = {k: (r.get(k) or '').strip() for k in COLS}
    return out


def apply(rows, path, kind='word'):
    """Mutates rows in place; returns (edited, dropped, unmatched)."""
    ov = _load(path)
    if not ov:
        return 0, 0, []
    seen, edited, dropped = set(), 0, 0
    keep = []
    for r in rows:
        o = ov.get(r.get('telugu', '').strip())
        if not o:
            keep.append(r); continue
        seen.add(r['telugu'].strip())
        if o['action'] == 'drop':
            dropped += 1
            continue
        for field in ('english', 'example', 'notes'):
            if o.get(field):
                r[field] = o[field]
        if isinstance(r.get('flags'), set):
            r['flags'].add('override')
        edited += 1
        keep.append(r)
    rows[:] = keep
    return edited, dropped, sorted(set(ov) - seen)


def template(path):
    """Create the file with a header and a worked example if it does not exist yet."""
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(COLS)
    return True
