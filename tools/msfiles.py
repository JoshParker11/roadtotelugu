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
