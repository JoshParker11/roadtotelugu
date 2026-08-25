# -*- coding: utf-8 -*-
"""The word registry — one real definition card per word, baked offline.

    python3 tools/ms_vocab.py --pending            # words with no definition yet, + their context
    python3 tools/ms_vocab.py --pending --limit 40 # a workable batch
    python3 tools/ms_vocab.py patch.tsv            # apply definitions
    python3 tools/ms_vocab.py --stats              # coverage

`ministories/vocab.tsv` is the term glossary DECISIONS.md #7 said was missing, with the reader as
its consumer. One row per (word, sense):

    guid  te  sense_no  gloss  pos  explain  context_guid  status

WHY A PATCH FILE AND NOT A LIVE API CALL
Same reasoning as ms_apply.py, and the same shape deliberately. Definitions can be produced two
ways — worked out in a chat session (which is where the judgment currently lives, and what the
subscription pays for) or generated in bulk through the Batch API for the remaining 55 stories.
Both write the same TSV. Keeping the tool ignorant of *how* a definition was produced is what
lets the cheap path and the careful path coexist without a second code path.

THE ACCUMULATION RULE
When a later story uses an already-registered word in a genuinely new sense or construction,
APPEND a new sense_no — never overwrite sense 1. First occurrence wins row 1; the registry only
grows. A word's card shows every sense, first-met first. This is why the key is (guid, sense_no)
and not guid alone, and why applying a patch for a guid that already has senses is an append
rather than a replace unless --force says otherwise.

WHY MOST OF THE WORK IS MORPHOLOGY, NOT LEXICOGRAPHY
Of the 151 unresolved words in stories 1-5, the overwhelming majority are inflected forms of
stems the master already glosses — గంటలకు is గంట + లకు, కారులో is కారు + లో, లేస్తాడు is లే- with
a third-person-masculine habitual ending. The card that helps is not a dictionary equivalent
invented from scratch; it is "here is the dictionary form, here is what each suffix is doing."
--pending therefore emits the master's own gloss for any stem it can find, so whoever writes the
definition is correcting and extending checked facts rather than recalling them.

NOTHING CHECKS AN EXPLANATION'S CORRECTNESS
There is no check_ms.py for this. status stays `draft` until a native speaker reads it, and that
is the honest state — BRIEF.md §8's warning about a confidently wrong grammatical explanation
applies here more than anywhere else in the project.
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from ids import guid as make_guid

MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
VOCAB = os.path.join(MS, 'vocab.tsv')
MANIFEST = os.path.join(MS, 'word_audio.tsv')
MASTER = os.path.join(ROOT, 'data', 'master_words.tsv')
VERBFORMS = os.path.join(HERE, 'verbforms.json')

COLS = ['guid', 'te', 'sense_no', 'gloss', 'pos', 'explain', 'context_guid', 'status']
ZW = '‌‍'


def rows_for(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def bare(s):
    return (s or '').strip().replace('‌', '').replace('‍', '')


def load_master():
    by_te = {}
    for r in rows_for(MASTER):
        te = bare(r.get('telugu'))
        if te:
            by_te.setdefault(te, r)
    return by_te


def load_suffixes(by_te):
    """Bound suffixes the master itself glosses, longest first — same rule as build_ms_reader."""
    out = []
    for r in rows_for(MASTER):
        if 'bound-suffix' in (r.get('flags') or ''):
            te = bare(r.get('telugu'))
            if te:
                out.append((te, r))
    out.sort(key=lambda x: -len(x[0]))
    return out


def first_occurrences():
    """word script -> (context_guid, telugu sentence, english sentence).

    First occurrence in story order, which is what the card quotes. Uses the same ordering the
    reader shows, so 'the sentence you met it in' means the same thing in both places.
    """
    seen = {}
    for path in sorted(os.listdir(WORK)):
        if not path.endswith('.tsv'):
            continue
        for r in rows_for(os.path.join(WORK, path)):
            te = r.get('te', '').strip()
            if not te:
                continue
            for tok in te.split():
                k = bare(tok.strip('.,!?:;"“”'))
                if k and k not in seen:
                    seen[k] = (r['guid'], te, r['en'])
    return seen


def decompose(te, by_te, suffixes):
    """Known stem + known bound suffix, one layer deep. Returns (stem_row, suffix_row) or None."""
    for suf, srow in suffixes:
        if not te.endswith(suf) or len(te) - len(suf) < 2:
            continue
        stem = by_te.get(te[:-len(suf)])
        if stem:
            return stem, srow
    return None


def load_vocab():
    rows = rows_for(VOCAB)
    by_guid = {}
    for r in rows:
        by_guid.setdefault(r['guid'], []).append(r)
    return rows, by_guid


def save_vocab(rows):
    rows.sort(key=lambda r: (r['te'], int(r.get('sense_no') or 1)))
    with open(VOCAB, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, COLS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def cmd_pending(limit):
    words = rows_for(MANIFEST)
    if not words:
        sys.exit('No word manifest — run: python3 tools/build_ms_reader.py')
    _, have = load_vocab()
    by_te = load_master()
    suffixes = load_suffixes(by_te)
    vf = json.load(open(VERBFORMS, encoding='utf-8')) if os.path.exists(VERBFORMS) else {}
    ctx = first_occurrences()

    pending = [w for w in words if w['guid'] not in have]
    if not pending:
        print('Every word in the manifest has at least one sense. Nothing pending.')
        return
    shown = pending[:limit] if limit else pending
    print(f'# {len(pending)} word(s) with no definition yet; showing {len(shown)}')
    print('# For each: what is already known from checked sources, then its first sentence.')
    print('# Write a patch TSV with columns: ' + '  '.join(COLS))
    print()
    for w in shown:
        te = bare(w['te'])
        print(f"=== {w['te']}   [{w['guid']}]")
        m = by_te.get(te)
        if m:
            print(f"    master: {m.get('roman','')} — {m.get('english','')}")
        elif te in vf:
            meta = vf[te]
            print(f"    verblab: form={meta.get('form','')} root={meta.get('root','')}")
        else:
            d = decompose(te, by_te, suffixes)
            if d:
                stem, suf = d
                print(f"    stem:   {stem.get('telugu','')} — {stem.get('english','')}")
                print(f"    suffix: {suf.get('telugu','')} — {suf.get('english','')}")
            else:
                print('    (no checked source — needs full analysis)')
        c = ctx.get(te)
        if c:
            print(f"    context [{c[0]}]: {c[1]}")
            print(f"    english:          {c[2]}")
        print()


def cmd_apply(path, force):
    patch = rows_for(path)
    if not patch:
        sys.exit('patch is empty')
    rows, by_guid = load_vocab()
    manifest = {r['guid']: r['te'] for r in rows_for(MANIFEST)}

    added = replaced = unknown = 0
    for p in patch:
        g = (p.get('guid') or '').strip()
        if not g:
            continue
        if g not in manifest:
            print(f'UNKNOWN  {g} is not in word_audio.tsv — stale patch, or a typo')
            unknown += 1
            continue
        sense = str(p.get('sense_no') or '').strip() or str(len(by_guid.get(g, [])) + 1)
        existing = [r for r in by_guid.get(g, []) if str(r['sense_no']) == sense]
        if existing and not force:
            print(f'skip     {g} sense {sense} already exists (use --force to replace)')
            continue
        new = {
            'guid': g,
            'te': p.get('te') or manifest[g],
            'sense_no': sense,
            'gloss': p.get('gloss', ''),
            'pos': p.get('pos', ''),
            'explain': p.get('explain', ''),
            'context_guid': p.get('context_guid', ''),
            'status': p.get('status') or 'draft',
        }
        if existing:
            rows = [r for r in rows if not (r['guid'] == g and str(r['sense_no']) == sense)]
            replaced += 1
        else:
            added += 1
        rows.append(new)
        by_guid.setdefault(g, []).append(new)

    save_vocab(rows)
    print(f'\nadded {added}, replaced {replaced}, unknown {unknown} -> {VOCAB}')
    return 1 if unknown else 0


def cmd_stats():
    words = rows_for(MANIFEST)
    rows, by_guid = load_vocab()
    covered = sum(1 for w in words if w['guid'] in by_guid)
    senses = len(rows)
    drafts = sum(1 for r in rows if r['status'] == 'draft')
    print(f'manifest words   {len(words)}')
    print(f'  with a card    {covered}  ({covered * 100 // max(1, len(words))}%)')
    print(f'  no card yet    {len(words) - covered}')
    print(f'senses total     {senses}   ({drafts} draft, {senses - drafts} checked or better)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('patch', nargs='?', help='TSV of definitions to apply')
    ap.add_argument('--pending', action='store_true', help='list words with no definition yet')
    ap.add_argument('--limit', type=int, default=0, help='cap how many --pending shows')
    ap.add_argument('--stats', action='store_true')
    ap.add_argument('--force', action='store_true', help='replace an existing sense')
    args = ap.parse_args()

    if args.stats:
        return cmd_stats()
    if args.pending:
        return cmd_pending(args.limit)
    if not args.patch:
        ap.error('give a patch file, or --pending / --stats')
    return cmd_apply(args.patch, args.force)


if __name__ == '__main__':
    sys.exit(main() or 0)
