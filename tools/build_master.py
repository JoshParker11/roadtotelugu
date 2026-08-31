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
import adapters, glosses, ids, overrides

ROOT = os.path.normpath(os.path.join(HERE, '..'))
# lower is better: hand-written material carries register cues and examples the bulk lists lack,
# and the lesson pages are the most recent and most carefully checked of it
SOURCE_RANK = {'lesson': 0, 'core-gaps': 0, 'site': 1, 'anki': 2, 'book1000': 3, 'spoken-telugu': 4, 'top1000': 5}
OUT = os.path.join(ROOT, 'data', 'master_words.tsv')
VERBFORMS = json.load(open(os.path.join(HERE, 'verbforms.json'), encoding='utf-8'))

# Bound morphemes: real and worth learning, but they are suffixes, not free-standing words.
# A flashcard "in = లో" teaches a preposition Telugu does not have.
BOUND = {'గా','న','తో','కు','కి','లో','ది','ను','నుండి','వరకు','లాగా','పై','చే','యొక్క','కూడా',
         'ండి','డం','తున్నా','లు','బోతున్నాను',
         # Telugu stacks case on number, and these two are what the stack needs: the oblique
         # plural -ల that -లు becomes before another suffix, and the -ని the accusative takes
         # after some stems. Without them గంటలకు (గంట + ల + కు) and ఆహారాన్ని decompose to
         # nothing and the reader shows a wall of words with no meaning at all.
         'ల','ని'}

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


GLOSS_STRIP = re.compile(r'\([^)]*\)|\[[^\]]*\]')


def gloss_terms(en):
    """Comparable meaning units: 'to eat' -> {eat}, 'How Much ?' -> {how much},
    'you (informal — close friends only); you' -> {you}."""
    out = set()
    for part in re.split(r'[;,/]', GLOSS_STRIP.sub('', en or '')):
        t = re.sub(r'[^a-z ]', '', part.lower()).strip()
        t = re.sub(r'^to\s+', '', t).strip()
        if t:
            out.add(t)
    return out


# Suffixes that change the word rather than misspell it. పెద్ద "big" vs పెద్దది "the big
# one", వెళ్ళి "having gone" vs వెళ్ళండి "please go" — same gloss, different words.
MEANINGFUL_SUFFIX = ('ది', 'ండి', 'కు', 'కి', 'లో', 'తో', 'ని', 'ను', 'లు', 'గా')


def _edit(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _same_word(short, long_):
    """True only for an orthographic slip, not a real morphological difference."""
    strip = lambda x: re.sub(r'[\s?!.,]', '', x)
    if strip(short) == strip(long_):
        return True                                   # ఎంత? / ఎంత, ఈరోజు / ఈ రోజు
    if _edit(short, long_) > 1:
        return False                                  # too far apart to be a slip
    return not long_.endswith(MEANINGFUL_SUFFIX)      # నువ్వ/నువ్వు yes, పెద్ద/పెద్దది no


def reconcile_typos(merged):
    """Fold single-source entries that are a misprint of a well-attested one.

    The book's very first entry prints "You / Nuvu / నువ్వ" — the script is missing its
    final vowel sign, so నువ్వ (nuvva, not a word) never merges with నువ్వు (nuvvu) and
    survives as its own card.

    Edit distance alone cannot find these: Telugu is full of real minimal pairs, and a
    similarity scan over romanization flags తాగు/ఆగు and పాడు/పడు, which are different
    words. So a candidate needs a shared gloss term AND near-identical script — and even
    then it is only merged when the difference is an orthographic slip. Anything else is
    left alone and flagged for a human, because merging is destructive."""
    import difflib
    attested = [m for m in merged.values() if len(m['source'].split(',')) > 1]
    drop, flagged = [], []
    for key, m in merged.items():
        if len(m['source'].split(',')) > 1 or not m['telugu']:
            continue
        terms = gloss_terms(m['english'])
        if not terms:
            continue
        for a in attested:
            if not a['telugu'] or a is m or not (terms & gloss_terms(a['english'])):
                continue
            if difflib.SequenceMatcher(None, m['telugu'], a['telugu']).ratio() < 0.80:
                continue
            pair = sorted((m['telugu'], a['telugu']), key=len)
            if _same_word(*pair):
                for src in m['source'].split(','):
                    if src not in a['source'].split(','):
                        a['source'] += ',' + src
                a['notes'] = (a['notes'] + f" · {m['source']} prints this as {m['telugu']}"
                              f" ({m['roman']}) — treated as a misprint").strip(' ·')
                a['flags'].add('merged-misprint')
                drop.append((key, m, a))
            else:
                m['flags'].add('possible-misprint')
                m['notes'] = (m['notes'] + f" · close to {a['telugu']} ({a['roman']}) "
                              f"[{a['source']}] — confirm these are different words").strip(' ·')
                flagged.append((m, a))
            break
    for key, _, _ in drop:
        del merged[key]
    return drop, flagged


def classify(rec):
    flags = []
    te, rom, en = rec['telugu'], rec['roman'], rec['english']
    # A leading hyphen is how the old decks wrote a suffix (-లో, -ండి). Strip it before the
    # lookup, or those rows read as free-standing words — which let the sentence respacer split
    # tīsukōṇḍi into "tīsukō ṇḍi".
    te = te.lstrip('-')
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


def carry_sequencing(rows):
    """Copy study_order / study_day from the master being replaced, matched on guid.

    THIS IS LOAD-BEARING. This script regenerates the master from the adapters, and until
    this existed it wrote a fresh file without the two sequencing columns — so the documented
    way to fix a gloss ("edit data/overrides_words.tsv, re-run build_master.py") silently
    erased the study order for all 2,103 positioned words.

    That is not a recoverable inconvenience. The order is append-only precisely because Anki
    cannot be told to renumber: `sequence.py` reads the existing positions and keeps them, so
    with them gone it would re-sort from scratch, and honouring a new order in Anki means
    delete-and-reimport, which destroys every card's scheduling. One rebuild after the first
    import would have cost the whole review history.

    Matching on guid rather than row id is what makes this safe: the guid is a hash of the
    Telugu script (tools/ids.py), so it survives rows being added, dropped or reordered, which
    is exactly what a rebuild does. Entries that are genuinely new get no position here and
    are appended by sequence.py, in greedy order among themselves.
    """
    if not os.path.exists(OUT):
        return 0
    prev = {}
    with open(OUT, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if str(r.get('study_order', '')).strip().isdigit():
                prev[r['guid']] = (r['study_order'], r.get('study_day', ''))
    if not prev:
        return 0

    hit = 0
    for r in rows:
        got = prev.get(r.get('guid', ''))
        r['study_order'], r['study_day'] = got if got else ('', '')
        if got:
            hit += 1

    lost = len(prev) - hit
    if lost:
        # A positioned word vanishing means an override dropped it or a source changed its
        # script. Either is a real decision, but it must not happen by accident.
        print(f'  WARNING: {lost} words had a study position and are no longer in the master')
    return hit


def main():
    records = []
    for name in ('lesson', 'core-gaps', 'site', 'anki', 'book1000', 'top1000', 'spoken-telugu'):  # earlier wins
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
            if r['english']:
                m['gloss_list'].append((SOURCE_RANK.get(r['source'], 9), r['english'].strip()))
            if not m['pos'] and r.get('pos'):
                m['pos'] = r['pos']
            if not m.get('example') and r.get('example'):
                m['example'] = r['example']
            if not m.get('lesson') and r.get('lesson'):
                m['lesson'] = r['lesson']
            if r.get('extra_flags'):
                m['flags'] |= set(r['extra_flags'].split())
            # keep whichever source supplied these, regardless of merge order
            for extra in ('pronunciation', 'island'):
                if not m.get(extra) and r.get(extra):
                    m[extra] = r[extra]
            if r.get('rank') and not m.get('rank'):
                m['rank'] = r['rank']
            continue
        rec = {'telugu': te, 'roman': rom, 'english': r['english'].strip(),
               'gloss_list': [(SOURCE_RANK.get(r['source'], 9), r['english'].strip())],
               'pos': r.get('pos',''), 'source': r['source'], 'raw_rom': r.get('raw_rom',''),
               'example': r.get('example',''), 'rank': r.get('rank',''),
               'pronunciation': r.get('pronunciation',''), 'island': r.get('island',''),
               'lesson': r.get('lesson',''),
               'lemma': '', 'notes': r.get('notes',''), 'flags': set()}
        rec['flags'] = set(classify(rec))
        for extra in ('book_flags', 'extra_flags'):
            if r.get(extra):
                rec['flags'] |= set(r[extra].split())
        merged[key] = rec

    for m in merged.values():
        front, extras = glosses.resolve(m.pop('gloss_list', []), prefer_detail=True)
        if front:
            m['english'] = front
        if extras:
            m['notes'] = (m['notes'] + ' · also: ' + '; '.join(extras[:4])).strip(' ·')
            m['flags'].add('multi-gloss')

    dropped, flagged = reconcile_typos(merged)
    if flagged:
        print(f'\n  {len(flagged)} look close but differ by a real suffix — left alone, flagged:')
        for m, a in flagged[:8]:
            print(f"    {m['telugu']:<14}{m['roman']:<12}vs {a['telugu']} {a['roman']}")
    if dropped:
        print(f'\n  folded {len(dropped)} misprints into their attested spelling:')
        for _, m, a in dropped:
            print(f"    {m['telugu']:<14}{m['roman']:<12}\"{m['english'][:26]}\" [{m['source']}]"
                  f"  ->  {a['telugu']} {a['roman']}")

    rows = list(merged.values())
    # Study order: what a lesson actually taught, in lesson order, then the rest of the
    # sequenced site material, then everything else by source frequency rank. Note this only
    # affects the readable W#### id and the order of the file — the Anki guid is content-derived
    # (tools/ids.py), so reordering here can no longer disturb an existing deck.
    rows.sort(key=lambda r: (0 if r.get('lesson') else (1 if 'site' in r['source'] else 2),
                             int(r['lesson']) if str(r.get('lesson','')).isdigit() else 0,
                             int(r['rank']) if str(r.get('rank','')).isdigit() else 10**6))
    for i, r in enumerate(rows, 1):
        r['id'] = f'W{i:04d}'

    ovp = os.path.join(ROOT, 'data', 'overrides_words.tsv')
    overrides.template(ovp)
    ed, dr, unmatched = overrides.apply(rows, ovp, 'word')
    if ed or dr:
        print(f'  overrides: {ed} edited, {dr} dropped')
    if unmatched:
        print(f'  overrides with no matching entry: {unmatched[:6]}')
    for i, r in enumerate(rows, 1):
        r['id'] = f'W{i:04d}'

    ids.assign(rows, 'W')

    carried = carry_sequencing(rows)

    cols = ['id','guid','telugu','roman','english','pronunciation','pos','island','lemma',
            'example','lesson','rank','source','raw_rom','flags','notes',
            'study_order','study_day']
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
    if carried:
        print(f'  carried {carried} existing study positions forward')
    for k in sorted(fc, key=lambda k: -fc[k]):
        print(f'    {k:<20} {fc[k]}')


if __name__ == '__main__':
    main()
