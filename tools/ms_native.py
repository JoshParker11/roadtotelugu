# -*- coding: utf-8 -*-
"""Turn the native speaker's returned sheet into a patch for tools/ms_apply.py.

    python3 tools/ms_native.py --report                  # what would change, nothing written
    python3 tools/ms_native.py ~/Downloads/"mini stories.xlsx"
    python3 tools/ms_apply.py ministories/native_patch.tsv --force

Reads the returned English/Telugu sheet plus ministories/native_review_map.json (the rejoin map
written when the sheet was sent out, English -> guids), applies the correction table below, and
writes ministories/native_patch.tsv.

THE STANDING RULE HERE IS "INDEX ON THE NATIVE SPEAKER"
Their Telugu is the product. An AI review of it was supplied alongside, and most of what it
flags is style — register, loanword density, whether `want` should have been ఇష్టపడు — which is
exactly the translator's call to make and not ours to overrule. Those are reported, never
applied.

EVERY CORRECTION BELOW IS SOURCED FROM THE TRANSLATOR'S OWN TEXT
Not from the review's suggestions, and not from this project. Where a row is blank, broken, or
contradicts itself, the same sentence almost always appears elsewhere in the sheet done
correctly, and that is what gets used:

    row 217  blank              <- row 219, minus its "అవును, "
    row 258  answer overwrote   <- row 227, prefixed "ఏడు: "
    row 254  చేశాడు for Jane    <- చేసింది, rows 226 and 257
    row 174  సైన్స్ for history  <- హిస్టరీ, rows 144 and 154
    row  86  "I decided"        <- నిర్ణయించుకున్నాడు, row 56, the same sentence in 3rd person
    row 206  నాకు for Jon       <- జోన్ కి, row 183

That discipline is the whole reason this is safe to apply unreviewed: no Telugu is composed
here, only moved from a row where the translator already wrote it.

ROWS 160 AND 161 ARE A SWAP, NOT TWO ERRORS
160 is the statement "Two: The daughter likes school" and carries a question; 161 is the
question "Does the daughter like school?" and carries text copied from row 144. The question
form the translator wrote at 160 is exactly what 161 needs. So 161 takes it, and 160 keeps the
same words with the interrogative clitic dropped.

WHAT THE REVIEW GOT WRONG
Three flags do not survive checking against the cell they point at — 30, 40 and 48 describe
sentences that are not on those rows (the review's prose drifted; its row numbers are right,
its explanations are not always). They are reported as spurious rather than acted on.
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
MAP = os.path.join(MS, 'native_review_map.json')
OUT = os.path.join(MS, 'native_patch.tsv')
DEFAULT_SHEET = os.path.join(MS, 'native_review.tsv')

# (row, English prefix to verify against, find, replace) — find='' means replace the whole cell.
# The English check is not decoration: a patch keyed on row number against a sheet that has been
# re-sorted is how you silently translate the wrong sentence.
CORRECTIONS = [
    # --- typographic ---
    (103, 'But my food does not taste good', 'కాను', 'కానీ'),
    (144, 'My daughter likes English and History', 'ఇంగ్షీషు', 'ఇంగ్లీషు'),
    (269, 'Some customers are friendly to James', 'జేమ్స్త తో', 'జేమ్స్ తో'),
    (118, 'Yes, Karen wants a new hobby', '?', ''),
    (333, 'No, Lisa does not try a pair of red shoes', '?', ''),
    (344, 'Yes, the black shoes are expensive', '?', ''),
    # Found by check_ms, not by the review. The review DID describe both of these — its flags
    # 30 and 48 name these exact sentences — but attached them to rows 30 and 48, which hold
    # something else. Its row numbers were wrong where its observations were right, so both
    # were dismissed as spurious on the first pass and the checker caught them afterwards.
    (29, 'Yes, Mike drives his car to work', '?', ''),
    # the question clitic split off as its own word
    (164, 'Is the daughter a bad student', 'విద్యార్థిని నా ?', 'విద్యార్థినా?'),
    (196, 'Is Jon a high school student', 'విద్యార్థి నా?', 'విద్యార్థా?'),
    (202, 'Is Clare a high school student', 'విద్యార్థిని నా ?', 'విద్యార్థినా?'),
    # Interrogative ending on a declarative answer, plus the subject written twice.
    (46, 'Yes, Mike feels happy when he talks to the customers',
     'మైక్ తన కస్టమర్లతో మాట్లాడేటప్పుడు మైక్ చాలా సంతోషపడుతాడా?',
     'మైక్ తన కస్టమర్లతో మాట్లాడేటప్పుడు చాలా సంతోషపడుతాడు'),
    # --- content, moved from the translator's own rows ---
    (217, 'Eight: Clare makes Jon do his homework', '',
     'ఎనిమిది: క్లేర్ ఎల్లప్పుడూ జోన్ చేత అతని హోంవర్క్ చేయిస్తూ ఉంటుంది'),
    (258, 'Seven: Fred has a shower and brushes his teeth', '',
     'ఏడు: ఫ్రెడ్ స్నానం చేసి, పళ్ళు తోముకున్నాడు'),
    (254, 'Six: Jane has a hot bath', 'చేశాడు', 'చేసింది'),
    (174, 'Does Amy like English and history', 'సైన్స్', 'హిస్టరీ'),
    (160, 'Two: The daughter likes school', 'ఇష్టమా?', 'ఇష్టం'),
    (161, 'Does the daughter like school', '', 'కూతురికి స్కూల్ అంటే ఇష్టమా?'),
    (113, 'Two: Karen does the same thing every day', 'చేస్తుందా?', 'చేస్తుంది'),
    # --- agreement, one morpheme, attested in the sheet ---
    (86, 'Eight: Dustin decides to stay home', 'నిర్ణయించుకున్నాను', 'నిర్ణయించుకున్నాడు'),
    (88, 'Yes, he decides to stay home', 'నిర్ణయించుకున్నాను', 'నిర్ణయించుకున్నాడు'),
    (179, 'Jon is in high school', 'ఉంది', 'ఉన్నాడు'),
    (206, 'Does Jon like playing on his computer', 'నాకు', 'జోన్ కి'),
    (207, 'Yes, Jon likes playing on his computer', 'నాకు', 'జోన్ కి'),
]

# Flags whose row number does not match what they describe. 30 and 48 turned out to describe
# real problems on OTHER rows (29 and 46, both corrected above) — the review's prose was right
# and its row numbers were not, which is worth knowing before dismissing anything it says.
SPURIOUS = {30: 'points at a row with no question mark; the sentence it describes is row 29',
            40: 'describes a different sentence',
            48: 'points at the wrong row; the sentence it describes is row 46'}


def load_sheet(path):
    """The returned sheet, as [(row number in the file, english, telugu)]."""
    if path.lower().endswith(('.xlsx', '.xlsm')):
        try:
            import openpyxl
        except ImportError:
            sys.exit('openpyxl is needed to read .xlsx: pip3 install openpyxl')
        ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
    else:
        with open(path, encoding='utf-8') as f:
            rows = [tuple(r) for r in csv.reader(f, delimiter='\t')]
    return [(i + 1, (r[0] or '').strip(), (r[1] or '').strip() if len(r) > 1 else '')
            for i, r in enumerate(rows)][1:]          # drop the header


def apply_corrections(sheet):
    by_row = {n: (en, te) for n, en, te in sheet}
    applied, failed = [], []
    for n, en_check, find, repl in CORRECTIONS:
        if n not in by_row:
            failed.append((n, 'no such row')); continue
        en, te = by_row[n]
        if not en.lower().startswith(en_check.lower()):
            failed.append((n, f'English does not match: {en[:50]!r}')); continue
        if find and find not in te:
            failed.append((n, f'{find!r} not present in {te[:50]!r}')); continue
        new = te.replace(find, repl).strip() if find else repl
        if new == te:
            failed.append((n, 'no change')); continue
        applied.append((n, en, te, new))
        by_row[n] = (en, new)
    return by_row, applied, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet', nargs='?', default=DEFAULT_SHEET)
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(args.sheet):
        sys.exit(f'no sheet at {args.sheet}')
    if not os.path.exists(MAP):
        sys.exit(f'no rejoin map at {MAP} — it is written when the sheet is sent out')

    sheet = load_sheet(args.sheet)
    by_row, applied, failed = apply_corrections(sheet)
    with open(MAP, encoding='utf-8') as f:
        gmap = json.load(f)

    print(f'{len(sheet)} rows returned · {len(applied)} corrections applied')
    for n, en, old, new in applied:
        print(f'  row {n:>3}  {en[:52]}')
        print(f'           - {old[:70]}')
        print(f'           + {new[:70]}')
    if failed:
        print(f'\n{len(failed)} corrections did NOT apply — the sheet has changed under them:')
        for n, why in failed:
            print(f'  row {n}: {why}')
    if SPURIOUS:
        print(f'\n{len(SPURIOUS)} review flags judged spurious and left alone:')
        for n, why in sorted(SPURIOUS.items()):
            print(f'  row {n}: {why}')

    rows, unmapped = [], []
    for n, (en, te) in sorted(by_row.items()):
        if not te:
            continue
        guids = gmap.get(en)
        if not guids:
            unmapped.append((n, en)); continue
        for g in guids:
            rows.append({'guid': g, 'te': te, 'status': 'native'})

    print(f'\n{len(rows)} patch rows over {len({r["guid"] for r in rows})} segments')
    if unmapped:
        print(f'{len(unmapped)} sheet rows have no guid in the rejoin map:')
        for n, en in unmapped[:6]:
            print(f'  row {n}: {en[:66]}')
    if args.report:
        print('\n--report: nothing written')
        return
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, delimiter='\t', fieldnames=['guid', 'te', 'status'])
        w.writeheader(); w.writerows(rows)
    print(f'\n-> {os.path.relpath(OUT, ROOT)}')
    print(f'   apply with: python3 tools/ms_apply.py {os.path.relpath(OUT, ROOT)} --force')


if __name__ == '__main__':
    main()
