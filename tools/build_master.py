# -*- coding: utf-8 -*-
"""Merge every vocabulary source into data/master_words.tsv.

    python3 tools/build_master.py

Rules, in order of importance:

1. Telugu script is the anchor. Where a source has it, romanization is derived from it
   (tools/te2rom.py, ~86% agreement with the hand-written course spellings and faithful to
   the script in essentially every disagreement). A source's own romanization is preserved
   in raw_rom but never used as the canonical form, so the sources cannot drift apart.
2. Merge key is the script, falling back to folded romanization for script-less sources.
3. The site wins on conflict — its glosses carry register cues and worked examples.
4. Nothing is deleted. Suspect rows are flagged so they can be triaged rather than
   silently trusted or silently dropped.

Output is TSV: English glosses contain commas and hand-editing quoted CSV is miserable.
"""
import csv, json, os, re, sys, unicodedata
from collections import defaultdict, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from te2rom import romanize
import adapters

ROOT = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'data', 'master_words.tsv')
VERBFORMS = json.load(open(os.path.join(HERE, 'verbforms.json'), encoding='utf-8'))

# Bound morphemes: real and worth learning, but they are suffixes, not free-standing words.
# A flashcard "in = లో" teaches a preposition Telugu does not have.
BOUND = {'గా','న','తో','కు','కి','లో','ది','ను','నుండి','వరకు','లాగా','పై','చే','యొక్క','కూడా'}

# Inflected endings that mark a finite verb rather than a dictionary headword.
INFLECTED_END = ('ింది','ాడు','ారు','ాను','ావు','ాము','ాయి','ుంది','ండి','తాను','తాడు','న్నాను','న్నారు')


def fold(s):
    """Diacritic- and gemination-insensitive key for matching romanizations across sources."""
    s = (s or '').lower().translate(str.maketrans('āīūēōṭḍṇḷṁṣśṛ', 'aiueotdnlmssr'))
    s = re.sub(r'[^a-z]', '', s)
    for a, b in (('ch','c'), ('nn','n'), ('ll','l'), ('tt','t'), ('dd','d'),
                 ('pp','p'), ('vv','v'), ('cc','c'), ('mm','m'), ('kk','k')):
        s = s.replace(a, b)
    return s


def is_english_respelled(rom, en):
    """సెట్ seṭ = "set" — the Telugu is the English word in Telugu letters, not a translation.
    Some are genuine loanwords Telugu really uses; the flag means 'decide', not 'wrong'."""
    a, b = fold(rom), fold(en)
    if not a or not b:
        return False
    return a == b or (len(b) > 3 and a.startswith(b[:4])) or (len(a) > 3 and b.startswith(a[:4]))


def classify(rec):
    flags = []
    te, rom, en = rec['telugu'], rec['roman'], rec['english']
    if te and te in BOUND:
        flags.append('bound-suffix')
    if te and te.endswith(INFLECTED_END) and te not in BOUND:
        flags.append('inflected')
    if te and te in VERBFORMS:
        vf = VERBFORMS[te]
        flags.append('verbform')
        rec['lemma'] = vf['root']
        rec['notes'] = (rec.get('notes','') + f" {vf['form']} of {vf['root']}").strip()
    if is_english_respelled(rom, en):
        flags.append('english-respelled')
    if not te:
        flags.append('needs-script')
    if ' ' in te.strip():
        flags.append('phrase')
    return flags


def main():
    records = []
    for name in ('site', 'top1000', 'spoken-telugu'):     # site first so it wins merges
        got = adapters.ALL[name]()
        print(f'  {name:<16} {len(got):>5} rows')
        records.extend(got)

    merged = OrderedDict()
    for r in records:
        te = r['telugu'].strip()
        rom = romanize(te) if te else ''
        if not rom and r.get('raw_rom'):
            rom = r['raw_rom'].strip()                     # script-less source, keep as given
        key = te if te else 'rom:' + fold(rom)
        if not key or key == 'rom:':
            continue
        if key in merged:
            m = merged[key]
            if r['source'] not in m['source'].split(','):
                m['source'] += ',' + r['source']
            # keep glosses distinct rather than letting one source overwrite another
            gl = [g.strip() for g in m['english'].split(';')]
            if r['english'] and r['english'].strip().lower() not in [g.lower() for g in gl]:
                m['english'] += '; ' + r['english'].strip()
                m['flags'].add('multi-gloss')
            if not m['pos'] and r.get('pos'):
                m['pos'] = r['pos']
            if not m.get('example') and r.get('example'):
                m['example'] = r['example']
            if r.get('rank') and not m.get('rank'):
                m['rank'] = r['rank']
            continue
        rec = {'telugu': te, 'roman': rom, 'english': r['english'].strip(),
               'pos': r.get('pos',''), 'source': r['source'], 'raw_rom': r.get('raw_rom',''),
               'example': r.get('example',''), 'rank': r.get('rank',''),
               'lemma': '', 'notes': r.get('notes',''), 'flags': set()}
        rec['flags'] = set(classify(rec))
        merged[key] = rec

    rows = list(merged.values())
    # study order: site material first (already sequenced), then by source frequency rank
    rows.sort(key=lambda r: (0 if 'site' in r['source'] else 1,
                             int(r['rank']) if str(r.get('rank','')).isdigit() else 10**6))
    for i, r in enumerate(rows, 1):
        r['id'] = f'W{i:04d}'

    cols = ['id','telugu','roman','english','pos','lemma','example','rank','source','raw_rom','flags','notes']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', extrasaction='ignore',
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            r = dict(r); r['flags'] = ' '.join(sorted(r['flags']))
            w.writerow(r)

    fc = defaultdict(int)
    for r in rows:
        for fl in r['flags']: fc[fl] += 1
        if not r['flags']: fc['clean'] += 1
    print(f'\n  master: {len(rows)} entries -> {os.path.relpath(OUT, ROOT)}')
    for k in sorted(fc, key=lambda k: -fc[k]):
        print(f'    {k:<20} {fc[k]}')


if __name__ == '__main__':
    main()
