# -*- coding: utf-8 -*-
"""Emit a ready-to-paste translation batch: the standing prompt, then the untranslated rows.

    python3 tools/ms_batch.py 6                 # one story
    python3 tools/ms_batch.py 6-10              # a range
    python3 tools/ms_batch.py 6-10 --no-prompt  # rows only, if the prompt is already in context
    python3 tools/ms_batch.py --remaining       # how much is left, and nothing else

Writes ministories/batch_<range>.txt and prints the row count, which is the number the model's
reply must match exactly.

WHY work/*.tsv AND NOT source/api/*.json
The raw LingQ payloads are still on disk (36 MB across 64 files) but they are the wrong input:
unsegmented, wrapped in tokens and timestamps and metadata, and — critically — carrying no guid.
work/*.tsv is the same English already sentence-split and keyed, and the guid is what lets a
reply be applied without trusting that row order survived a copy-paste. Re-fetching from LingQ
would be worse still: it costs an API round trip to arrive at data already sitting here.

WHY BATCHES ARE PER-STORY AND NOT THE WHOLE CORPUS
All 2,514 untranslated rows would fit in a large context window, and doing that is still a bad
idea. A story is the unit the drill is built on — its story/retell/questions triple has to stay
internally consistent, and that consistency is exactly what a model loses first as a batch grows.
More practically: when a reply comes back short, a 47-row batch tells you which story to redo,
where a 2,514-row batch tells you nothing and costs the whole run.

ROW COUNT IS THE CHECK THAT CATCHES THE COMMON FAILURE
Models drop, merge and reorder rows in long tables, silently. The count printed here is the
contract; ms_apply.py then verifies each guid individually and reports any it does not recognise.
Together those catch a truncated or reordered reply before it can corrupt anything.
"""
import argparse
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
CATALOG = os.path.join(MS, 'CATALOG.tsv')
PROMPT = os.path.join(MS, 'TRANSLATION_PROMPT.md')


def rows_for(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def prompt_body():
    """Section 1 of TRANSLATION_PROMPT.md, unquoted.

    The file keeps it as a blockquote so the surrounding document reads as documentation; the
    model should receive it as plain instructions, so the leading '> ' comes off here rather
    than the prompt being maintained in two places.
    """
    if not os.path.exists(PROMPT):
        sys.exit(f'{PROMPT} is missing — it is the guardrail, do not translate without it.')
    text = open(PROMPT, encoding='utf-8').read()
    m = re.search(r'^## 1\..*?$(.*?)^---', text, re.S | re.M)
    if not m:
        sys.exit('Could not find section 1 in TRANSLATION_PROMPT.md — has it been restructured?')
    out = []
    for line in m.group(1).splitlines():
        if line.startswith('> '):
            out.append(line[2:])
        elif line.strip() == '>':
            out.append('')
        elif not line.strip():
            out.append('')
    return '\n'.join(out).strip()


def parse_range(spec):
    m = re.fullmatch(r'(\d+)(?:-(\d+))?', spec.strip())
    if not m:
        sys.exit(f'Not a story number or range: {spec!r} (try "6" or "6-10")')
    lo = int(m.group(1))
    return list(range(lo, int(m.group(2) or lo) + 1))


def collect(nums):
    cat = {r['id']: r for r in rows_for(CATALOG)}
    want = set(nums)
    out = []
    for path in sorted(glob.glob(os.path.join(WORK, '*.tsv'))):
        sid = os.path.basename(path)[:-4]
        if int(cat[sid]['num']) not in want:
            continue
        for r in rows_for(path):
            if not r['te'].strip():
                out.append((int(cat[sid]['num']), r))
    return out


def remaining():
    cat = {r['id']: r for r in rows_for(CATALOG)}
    per = {}
    for path in sorted(glob.glob(os.path.join(WORK, '*.tsv'))):
        sid = os.path.basename(path)[:-4]
        n = int(cat[sid]['num'])
        for r in rows_for(path):
            if not r['te'].strip():
                per[n] = per.get(n, 0) + 1
    if not per:
        print('Nothing untranslated — all sixty stories are done.')
        return
    nums = sorted(per)
    print(f'{sum(per.values())} untranslated segment(s) across {len(nums)} stor(y/ies)')
    print(f'story numbers: {nums[0]}-{nums[-1]}' if nums == list(range(nums[0], nums[-1] + 1))
          else 'story numbers: ' + ', '.join(map(str, nums)))
    print(f'typical story: {sum(per.values()) // len(nums)} segments')
    print('\nSuggested batch size: one story at a time to start, so a bad reply costs one story.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stories', nargs='?', help='story number or range, e.g. 6 or 6-10')
    ap.add_argument('--no-prompt', action='store_true', help='omit the guardrails')
    ap.add_argument('--remaining', action='store_true', help='report what is left, write nothing')
    args = ap.parse_args()

    if args.remaining:
        return remaining()
    if not args.stories:
        ap.error('give a story number or range, or --remaining')

    nums = parse_range(args.stories)
    rows = collect(nums)
    if not rows:
        print(f'Nothing untranslated in stor{"y" if len(nums) == 1 else "ies"} {args.stories}.')
        return

    out_path = os.path.join(MS, f'batch_{args.stories}.txt')
    with open(out_path, 'w', encoding='utf-8') as f:
        if not args.no_prompt:
            f.write(prompt_body())
            f.write('\n\n---\n\n')
        f.write(f'Translate these {len(rows)} rows. Return exactly {len(rows)} rows.\n\n')
        f.write('guid\tpart\tseq\ten\n')
        for _n, r in rows:
            f.write(f"{r['guid']}\t{r['part']}\t{r['seq']}\t{r['en']}\n")

    print(f'{os.path.relpath(out_path, ROOT)}')
    print(f'  {len(rows)} row(s) across stor{"y" if len(nums) == 1 else "ies"} '
          f'{", ".join(map(str, nums))}')
    print(f'  the reply must contain exactly {len(rows)} rows — count before applying')
    print('\nthen:')
    print('  python3 tools/ms_apply.py patch.tsv')
    print(f'  python3 tools/check_ms.py --num {nums[0]} --warn')


if __name__ == '__main__':
    main()
