# -*- coding: utf-8 -*-
"""Quality control for the translation, for a translator who cannot yet read the target language.

    python3 tools/check_hp.py              # everything
    python3 tools/check_hp.py --ch 1
    python3 tools/check_hp.py --ch 1 --backtranslate   # emit a blind back-translation sheet

WHAT THIS CAN AND CANNOT DO
It cannot tell you whether the Telugu is any good. Nothing automated can. What it can do is catch
the specific failures that are invisible to someone reading a language they are still learning,
and those turn out to be most of the ones that actually happen:

  * a name silently dropped from a paragraph
  * a sentence left in English because it was hard, and then forgotten
  * an anchor term stitched inconsistently — Harry-కి here, Harryకి there
  * the English source edited after it was translated, so the pair no longer matches

The one check that finds meaning errors is the back-translation, and that is a human step. This
script only prepares the sheet for it: --backtranslate writes the Telugu with the English
withheld, so the back-translation is genuinely blind. Comparing the result against the source is
what catches dropped clauses and invented content.
"""
import argparse
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from ids import guid

WORK = os.path.join(ROOT, 'translate', 'work')
GLOSSARY = os.path.join(ROOT, 'translate', 'glossary.tsv')

TELUGU = r'ఀ-౿'
LATIN = re.compile(r"[A-Za-z][A-Za-z'’\.\-]*")

# The closed list from STYLE.md §4. A suffix run may chain these — Dursley-లకి is ల + కి, which
# is correct Telugu for "to the Dursleys". Extend this list deliberately and update STYLE.md at
# the same time; the point of it being closed is that stitching stays uniform across 3,016
# paragraphs.
SUFFIXES = ['నుంచి', 'నుండి', 'లు', 'కి', 'కు', 'ని', 'ను', 'తో', 'లో', 'ల']
SUFFIX_RUN = re.compile(r'^(?:' + '|'.join(SUFFIXES) + r')+$')

STATUSES = ('todo', 'draft', 'query', 'checked', 'done')


def load_glossary():
    """-> [(canonical, [spellings])], longest spelling first so multiword anchors match before
    their parts do."""
    terms = []
    with open(GLOSSARY, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            t = (r.get('term') or '').strip()
            if not t:
                continue
            spellings = [t] + [v.strip() for v in (r.get('variants') or '').split('|') if v.strip()]
            terms.append((t, spellings))
    terms.sort(key=lambda kv: -max(len(s) for s in kv[1]))
    return terms


def strip_anchors(te, terms):
    """Remove every anchor spelling from the Telugu, longest first. Whatever Latin text survives
    is either a stray English word or a name nobody has classified — both worth reporting."""
    for _, spellings in terms:
        for s in sorted(spellings, key=len, reverse=True):
            te = te.replace(s, '\x00')
    return te


def check_row(r, terms):
    """-> list of (severity, message)"""
    out = []
    en, te = r.get('en', ''), (r.get('te') or '').strip()
    status = (r.get('status') or 'todo').strip()

    if status not in STATUSES:
        out.append(('error', f'unknown status {status!r} (expected one of {", ".join(STATUSES)})'))

    # Identical paragraphs ('"What?"') are disambiguated by occurrence, so the key the segmenter
    # hashed was 'en#2', not 'en'. Accept any of those before concluding the source was edited.
    if r['guid'] not in {guid('H', en)} | {guid('H', f'{en}#{k}') for k in range(2, 21)}:
        out.append(('warn', 'guid does not match the English — source edited since segmenting'))

    if not te:
        if status != 'todo':
            out.append(('error', f'status is {status} but there is no translation'))
        return out
    if status == 'todo':
        out.append(('warn', 'has a translation but status is still todo'))

    # 1. Anchors present in the English must survive into the Telugu.
    #
    # This is the one check with an expected false positive: replacing a repeated name with a
    # pronoun is often the more natural Telugu, and English repeats names far more than Telugu
    # does. When that is a deliberate choice, say so in the notes column and move on — the error
    # list is a review queue, not a build gate. Dropping a name by accident is much more common
    # than pronominalising on purpose, so it stays an error rather than a warning.
    for canon, spellings in terms:
        if any(s in en for s in spellings) and canon not in te:
            out.append(('error', f'anchor "{canon}" is in the English but not the Telugu'))

    # 2. Nothing Latin should remain once the anchors are removed.
    rest = strip_anchors(te, terms)
    stray = [m.group().strip(".'’-") for m in LATIN.finditer(rest)]
    stray = [s for s in stray if len(s) > 1]
    if stray:
        out.append(('error', 'untranslated English or unclassified name: ' + ', '.join(sorted(set(stray)))))

    # 3. Latin running straight into Telugu script needs the hyphen (STYLE.md §4).
    for m in re.finditer(rf'[A-Za-z]([{TELUGU}]+)', te):
        out.append(('error', f'missing hyphen before the suffix "{m.group(1)}" — write Name-{m.group(1)}'))

    # 4. And what follows the hyphen has to be a sanctioned suffix, not a whole word.
    for m in re.finditer(rf'[A-Za-z]-([{TELUGU}]+)', te):
        if not SUFFIX_RUN.match(m.group(1)):
            out.append(('error', f'"{m.group(1)}" is hyphenated to an anchor but is not in the '
                                 f'closed suffix list — free words take a space'))
    return out


def backtranslate_sheet(rows, ch):
    """Telugu only, English withheld. A back-translation is worthless if the translator can see
    the source — they reconstruct the English from memory instead of from the Telugu."""
    path = os.path.join(WORK, f'ch{ch:02d}_backtranslate.tsv')
    done = [r for r in rows if (r.get('te') or '').strip() and r.get('status') != 'todo']
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['guid', 'te', 'back_en'])
        for r in done:
            w.writerow([r['guid'], r['te'], ''])
    print(f'  wrote {path} — {len(done)} segments, English withheld')
    print('  Fill back_en from the Telugu alone, then diff it against the en column of the')
    print('  chapter file. Dropped clauses and invented content show up there and nowhere else.')
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ch', type=int)
    ap.add_argument('--backtranslate', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true', help='list every problem, not the first 20')
    args = ap.parse_args()

    terms = load_glossary()
    paths = sorted(glob.glob(os.path.join(WORK, 'ch*.tsv')))
    paths = [p for p in paths if '_backtranslate' not in p]
    if args.ch:
        paths = [p for p in paths if os.path.basename(p) == f'ch{args.ch:02d}.tsv']
        if not paths:
            raise SystemExit(f'no chapter {args.ch} — run tools/hp_segment.py first')

    print(f'{len(terms)} anchors in the glossary\n')
    problems, totals = [], {'segments': 0, 'translated': 0}
    for p in paths:
        ch = int(re.search(r'ch(\d+)', os.path.basename(p)).group(1))
        with open(p, encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        counts = {s: 0 for s in STATUSES}
        for r in rows:
            counts[r.get('status', 'todo')] = counts.get(r.get('status', 'todo'), 0) + 1
            for sev, msg in check_row(r, terms):
                problems.append((sev, ch, r['guid'], msg, (r.get('en') or '')[:52]))
        n = len(rows)
        tr = sum(1 for r in rows if (r.get('te') or '').strip())
        totals['segments'] += n
        totals['translated'] += tr
        bar = '#' * int(24 * tr / n) if n else ''
        state = ' '.join(f'{k}={v}' for k, v in counts.items() if v)
        print(f'  ch{ch:02d}  {tr:4d}/{n:<4d} {bar:<24} {state}')
        if args.backtranslate and args.ch == ch:
            backtranslate_sheet(rows, ch)

    errs = [p for p in problems if p[0] == 'error']
    warns = [p for p in problems if p[0] == 'warn']
    pct = 100 * totals['translated'] / totals['segments'] if totals['segments'] else 0
    print(f'\n{totals["translated"]}/{totals["segments"]} segments translated ({pct:.1f}%)')

    for label, items in (('ERRORS', errs), ('warnings', warns)):
        if not items:
            continue
        print(f'\n{label}: {len(items)}')
        for sev, ch, g, msg, en in (items if args.verbose else items[:20]):
            print(f'  ch{ch:02d} {g}  {msg}')
            print(f'    en: {en}...')
        if not args.verbose and len(items) > 20:
            print(f'  ... and {len(items) - 20} more (-v for all)')

    if not errs and not warns:
        print('\nno problems found')
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
