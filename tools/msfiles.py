# -*- coding: utf-8 -*-
"""One place that knows which files in ministories/work/ are real.

WHY THIS EXISTS
This repo lives under ~/Documents, which macOS syncs to iCloud, and a sync race during a bulk
write leaves byte-identical duplicates beside the originals: "01b 2.tsv" next to "01b.tsv". It
has happened twice — 165 duplicated word clips once, and 28 duplicated work TSVs during a single
translation apply.

The .gitignore rule keeps them out of commits, and that is the trap. Ignored is not absent: git
stops mentioning them while every tool that globs `work/*.tsv` still reads them. The failure is
silent double-counting — a status tally read 589 native rows when the truth was 423 — or a loud
crash on a filename the catalogue has never heard of, which is the lucky case.

A conflict copy always has a space before the digit and a real work id never contains a space,
so that is the whole test.
"""
import glob
import os
import re

CONFLICT = re.compile(r' \d+(\.[A-Za-z0-9]+)?$')


def is_conflict_copy(path):
    return bool(CONFLICT.search(os.path.splitext(os.path.basename(path))[0] +
                                os.path.splitext(path)[1]))


def work_tsvs(work_dir):
    """Every real work TSV, sorted, with iCloud conflict copies left out."""
    return sorted(p for p in glob.glob(os.path.join(work_dir, '*.tsv'))
                  if ' ' not in os.path.basename(p))


def sweep(root='.'):
    """Find every iCloud conflict copy under root — files and directories both.

    Directories were the gap: the file patterns never matched `intensive/work 2/`, and four of
    them had appeared. Empty is the harmless case. A populated one is read by whatever walks
    the directory, which is how a status tally came back 40% too high.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        if '.git' in dirpath.split(os.sep):
            continue
        for n in list(dirnames) + filenames:
            if CONFLICT.search(os.path.splitext(n)[0]):
                out.append(os.path.join(dirpath, n))
    return sorted(out)


if __name__ == '__main__':
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    hits = sweep(root)
    if not hits:
        print('no conflict copies')
        raise SystemExit(0)
    # Grouped, because one sweep found 165 and printing every path buries the point.
    import collections as _c
    by_dir = _c.Counter(os.path.relpath(os.path.dirname(h), root) for h in hits)
    for d, n in sorted(by_dir.items(), key=lambda kv: -kv[1]):
        print(f'{n:>5}  {d}')
    print(f'{len(hits)} conflict copies in {len(by_dir)} director'
          f'{"y" if len(by_dir) == 1 else "ies"}')
