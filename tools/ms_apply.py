# -*- coding: utf-8 -*-
"""Apply a batch of translations to ministories/work/, keyed by guid.

    python3 tools/ms_apply.py --pending 2      # what still needs translating in story 2
    python3 tools/ms_apply.py patch.tsv        # apply; refuses to clobber existing work
    python3 tools/ms_apply.py patch.tsv --force  # ...unless you mean it

A patch is a TSV with a `guid` column, a `te` column, and optionally `notes` and `status`.
Anything not named is left alone.

WHY A PATCH FILE AND NOT DIRECT EDITS
Translations produced in a chat session have to land somewhere reviewable. Writing them straight
into the work TSVs with a throwaway script means the only record of what changed is the diff,
mixed in with whatever else moved that day, and a mistake is unpickable. A patch is a diffable
artefact: it says exactly which segments were touched and with what, it can be re-applied after a
re-segment, and it can be thrown away without touching anything else.

WHY IT KEYS ON GUID AND NOT ON POSITION
Because guids are content-derived (tools/ids.py). If the English changes, its guid changes, the
patch stops matching, and the row is reported as unknown instead of being silently written with a
translation of a sentence that no longer exists. Position-keyed patches fail silently; that is
the whole argument.

REFUSING TO OVERWRITE IS THE POINT
The default is to skip any row that already has a translation and say so. A batch apply that
quietly replaces reviewed work with a fresh draft is the same class of bug as a rebuild that eats
hand-entered columns, and this repo has been bitten by that before.
"""
import argparse
import csv
import glob
import os
import sys
from msfiles import work_tsvs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
CATALOG = os.path.join(MS, 'CATALOG.tsv')
FIELDS = ('te', 'notes', 'status')


def load(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def save(path, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, list(rows[0].keys()), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def pending(num):
    cat = {r['id']: r for r in load(CATALOG)}
    todo = []
    for path in work_tsvs(WORK):
        sid = os.path.basename(path)[:-4]
        if num and int(cat[sid]['num']) != int(num):
            continue
        for r in load(path):
            if not r['te'].strip():
                todo.append((sid, r))
    if not todo:
        print('nothing pending')
        return
    print(f'{len(todo)} segment(s) pending\n')
    print('guid\tpart\tseq\ten')
    for sid, r in todo:
        print(f"{r['guid']}\t{r['part']}\t{r['seq']}\t{r['en']}")


def apply_patch(path, force):
    patch = {r['guid']: r for r in load(path)}
    if not patch:
        sys.exit('patch is empty')
    applied = skipped = 0
    unknown = set(patch)
    for wpath in work_tsvs(WORK):
        rows = load(wpath)
        dirty = False
        for r in rows:
            p = patch.get(r['guid'])
            if not p:
                continue
            unknown.discard(r['guid'])
            if r['te'].strip() and not force:
                print(f'skip  {r["guid"]}  already translated (use --force to replace)')
                skipped += 1
                continue
            for f in FIELDS:
                v = p.get(f)
                # 'note' is accepted as an alias for 'notes'. A model handed a three-column
                # spec will plausibly emit either, and that difference silently dropping every
                # flag is exactly the failure this project cannot afford — an unflagged guess
                # is indistinguishable from a confident correct answer.
                if v is None and f == 'notes':
                    v = p.get('note')
                if v is not None:
                    r[f] = v
            if not p.get('status'):
                r['status'] = 'draft'
            applied += 1
            dirty = True
        if dirty:
            save(wpath, rows)
    for g in sorted(unknown):
        print(f'UNKNOWN guid not found in any work file: {g}')
    print(f'\napplied {applied}, skipped {skipped}, unknown {len(unknown)}')
    return 1 if unknown else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('patch', nargs='?', help='TSV with guid + te [+ notes, status]')
    ap.add_argument('--pending', metavar='NUM', help='list untranslated segments for a story')
    ap.add_argument('--force', action='store_true', help='overwrite existing translations')
    args = ap.parse_args()
    if args.pending:
        return pending(args.pending)
    if not args.patch:
        ap.error('give a patch file, or --pending NUM')
    return apply_patch(args.patch, args.force)


if __name__ == '__main__':
    sys.exit(main() or 0)
