# -*- coding: utf-8 -*-
"""Merge sentence sources into data/master_sentences.tsv.

    python3 tools/build_sentences.py

Same rules as the word master: Telugu script anchors the romanization, the site wins
conflicts, nothing is deleted. Two things are computed here that the word list does not need:

  register   derived from the grammar, not guessed — mīru/mī/gāru, the -ṇḍi endings and
             -nnārā/-āru mark respect; nuvvu/nī/vāḍu mark the familiar.
  known_pct  share of the sentence's words that appear in the word master. This is what
             lets the deck be ordered by what you already know instead of by source, which
             is the difference between a pile of sentences and a curriculum.
"""
import csv, os, re, sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from te2rom import romanize
import adapters, glosses, ids, overrides

ROOT = os.path.normpath(os.path.join(HERE, '..'))
SOURCE_RANK = {'site': 0, 'anki': 1, 'book1000': 2}
OUT = os.path.join(ROOT, 'data', 'master_sentences.tsv')
WORDS = os.path.join(ROOT, 'data', 'master_words.tsv')


def fold(s):
    s = (s or '').lower().translate(str.maketrans('āīūēōṭḍṇḷṁṣśṛ', 'aiueotdnlmssr'))
    return re.sub(r'[^a-z]', '', s)


def register_of(rom):
    toks = [t.strip('.,?!').lower() for t in rom.split()]
    if any(t in ('nuvvu', 'nī', 'nīku', 'vāḍu', 'vāḍi', 'vīḍu') for t in toks):
        return 'informal'
    if any(t in ('mīru', 'mī', 'gāru') for t in toks):
        return 'respectful'
    for t in toks:
        if t.endswith('ṇḍi'):
            return 'respectful'
        if t.endswith('andi') and len(t) >= 7:      # vaddandi yes, mandi no
            return 'respectful'
        if t.endswith(('nnārā', 'chēsāru', 'unnāru')):
            return 'respectful'
    return ''


def load_known():
    """A token counts as known if you have met the word, not only that exact inflection.
    Three ways in: the folded form is in the word master; the surface form is a cell of a
    Verb Lab paradigm; or a known word is a stem of it (vaddu -> vaddaṇḍi)."""
    exact, stems = set(), set()
    if os.path.exists(WORDS):
        for r in csv.DictReader(open(WORDS, encoding='utf-8'), delimiter='\t'):
            for piece in (r['roman'] or '').split():
                f = fold(piece)
                if f:
                    exact.add(f)
                    if len(f) >= 4:
                        stems.add(f[:4])
    verbforms = set()
    vf = os.path.join(HERE, 'verbforms.json')
    if os.path.exists(vf):
        import json
        verbforms = set(json.load(open(vf, encoding='utf-8')).keys())
    return exact, stems, verbforms


def is_known(tok_rom, tok_te, known):
    exact, stems, verbforms = known
    f = fold(tok_rom)
    if not f:
        return True                      # punctuation
    if f in exact or tok_te in verbforms:
        return True
    return len(f) >= 4 and f[:4] in stems


def main():
    known = load_known()
    records = []
    for name in ('site', 'anki', 'book1000'):
        got = adapters.ALL_SENT[name]()
        print(f'  {name:<12} {len(got):>5} rows')
        records.extend(got)

    merged = OrderedDict()
    for r in records:
        te = r['telugu'].strip()
        rom = romanize(te) if te else (r.get('raw_rom') or '').strip()
        key = fold(rom) or te
        if not key:
            continue
        if key in merged:
            m = merged[key]
            if r['source'] not in m['source'].split(','):
                m['source'] += ',' + r['source']
            if r['english']:
                m['gloss_list'].append((SOURCE_RANK.get(r['source'], 9), r['english'].strip()))
            for extra in ('pronunciation', 'island'):
                if not m.get(extra) and r.get(extra):
                    m[extra] = r[extra]
            continue
        merged[key] = {'telugu': te, 'roman': rom, 'english': r['english'].strip(),
                       'gloss_list': [(SOURCE_RANK.get(r['source'], 9), r['english'].strip())],
                       'register': r.get('register') or register_of(rom),
                       'source': r['source'], 'raw_rom': r.get('raw_rom', ''),
                       'rank': r.get('rank', ''), 'notes': r.get('notes', ''),
                       'pronunciation': r.get('pronunciation', ''),
                       'island': r.get('island', ''), 'flags': set()}

    for m in merged.values():
        # one prompt per card: a sentence has one meaning, however many ways it was typed
        front, extras = glosses.resolve(m.pop('gloss_list', []), max_senses=1)
        # the course pages annotate their examples with the grammar point being demonstrated
        # — "(neutral — u→i)". That belongs on the back, not in the production prompt.
        ann = re.search(r'\s*\(([^)]*[—\u2192-][^)]*)\)\s*$', front)
        if ann and len(ann.group(1)) > 3:
            front = front[:ann.start()].strip()
            extras.insert(0, ann.group(1).strip())
        if front:
            m['english'] = front
        if extras:
            m['notes'] = (m['notes'] + ' · also: ' + '; '.join(extras[:3])).strip(' ·')

    for m in merged.values():
        toks = [t for t in re.split(r'\s+', m['roman']) if t.strip('.,?!')]
        tets = re.split(r'\s+', m['telugu']) if m['telugu'] else []
        pairs = list(zip(toks, tets + [''] * max(0, len(toks) - len(tets))))
        hit = sum(1 for tr, tt in pairs if is_known(tr, tt, known))
        m['known_pct'] = round(100 * hit / len(pairs)) if pairs else 0
        m['new_words'] = ' '.join(tr.strip('.,?!') for tr, tt in pairs
                                  if not is_known(tr, tt, known))[:120]
        if not m['telugu']:
            m['flags'].add('needs-script')
        if not m['english']:
            m['flags'].add('no-english')
        if len(toks) > 12:
            m['flags'].add('long')

    rows = list(merged.values())
    # site material first (already sequenced), then easiest-first by known-word coverage
    rows.sort(key=lambda r: (0 if 'site' in r['source'] else 1, -r['known_pct'],
                             int(r['rank']) if str(r.get('rank', '')).isdigit() else 10**6))
    for i, r in enumerate(rows, 1):
        r['id'] = f'S{i:04d}'

    ovp = os.path.join(ROOT, 'data', 'overrides_sentences.tsv')
    overrides.template(ovp)
    ed, dr, unmatched = overrides.apply(rows, ovp, 'sentence')
    if ed or dr:
        print(f'  overrides: {ed} edited, {dr} dropped')
    for i, r in enumerate(rows, 1):
        r['id'] = f'S{i:04d}'

    ids.assign(rows, 'S')

    cols = ['id', 'guid', 'telugu', 'roman', 'english', 'pronunciation', 'register', 'known_pct',
            'new_words', 'island', 'rank', 'source', 'raw_rom', 'flags', 'notes']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        for r in rows:
            r = dict(r); r['flags'] = ' '.join(sorted(r['flags']))
            w.writerow(r)

    fc = defaultdict(int)
    for r in rows:
        for fl in r['flags']: fc[fl] += 1
    band = defaultdict(int)
    for r in rows:
        band[min(100, (r['known_pct'] // 20) * 20)] += 1
    print(f'\n  master: {len(rows)} sentences -> {os.path.relpath(OUT, ROOT)}')
    print('    flags     :', dict(fc) or 'none')
    print('    known-word coverage:', {f'{k}-{k+19}%': v for k, v in sorted(band.items())})


if __name__ == '__main__':
    main()
