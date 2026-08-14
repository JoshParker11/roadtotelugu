# -*- coding: utf-8 -*-
"""Decide what order to learn in, and when each sentence becomes readable.

    python3 tools/sequence.py            # compute, compare orderings, write both masters
    python3 tools/sequence.py --dry      # compare only, write nothing
    python3 tools/sequence.py --day 12   # what unlocks on a given day

THE PROBLEM
The masters were ordered by ingestion — site material, then the old Anki decks, then the book,
then the top-1000 list. That is the order the sources happened to arrive in, and it has nothing
to do with usefulness. Measured against the project's own 2,880-sentence corpus, the first 300
words in ingestion order cover 29.7% of running text; the 300 most frequent cover 54.0%. `nāku`
("to me") is the second most common token in the corpus and sat at position ~1,000.

TWO THINGS COMPUTED HERE, because they are the same question asked twice

1. `study_order` on the word master — the sequence to meet words in.
2. `unlock_day` on the sentence master — the first day every word in a sentence has been seen,
   given a fixed words-per-day rate. Sorting sentences by it turns the corpus into a curriculum:
   each day's sentences are the ones that just became readable.

WHY GREEDY AND NOT JUST FREQUENCY
Frequency ranks a word by how often it appears. What actually matters is how many *sentences* it
finishes — the last unknown word in a sentence is worth far more than a common word in a sentence
with four other unknowns. So the ordering is greedy on marginal unlock: repeatedly take the word
that moves the most sentences to fully-known, breaking ties on frequency. Both orderings are
computed and compared on every run, so the choice stays evidence-based rather than assumed.

THE ORDER IS APPEND-ONLY ONCE SET
A word that already carries a `study_order` keeps it. New words are appended after the highest
existing position, in greedy order among themselves. This is deliberate and it is not an
optimisation: re-sorting the whole list every time vocabulary is added would renumber cards the
learner has already met, and the only way to make Anki honour a new order is to delete and
re-import, which destroys scheduling. Append-only means new material costs one import that adds
cards and touches nothing else.

It also keeps the path linear, which matters for reconstructing it later: "word 312 came on day
21" stays true forever instead of being rewritten by a rebuild six weeks from now.

`--reorder` forces a full recompute. That is correct exactly once, before the first import, and
a mistake after it.

THE FREQUENCY SIGNAL IS WEIGHTED
Two corpora, and they are not equally relevant. The sentence master is course and textbook
material. `sources/private/conversations/` is 513 lines of the learner's own family talking,
which is the actual target register — so it counts for more per occurrence.
"""
import argparse, csv, glob, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
WORDS = os.path.join(ROOT, 'data', 'master_words.tsv')
SENTS = os.path.join(ROOT, 'data', 'master_sentences.tsv')
CONVOS = os.path.join(ROOT, 'sources', 'private', 'conversations', '*.csv')
VERBFORMS = os.path.join(HERE, 'verbforms.json')

WORDS_PER_DAY = 15
FAMILY_WEIGHT = 3          # an occurrence in real family speech is worth three in a textbook

# Held out of the study order entirely — flagged rows never reach the deck anyway.
BLOCK = {'needs-script', 'no-script', 'kannada-script', 'devanagari-script',
         'bound-suffix', 'english-respelled', 'no-english'}

_FOLD = str.maketrans('āīūēōṭḍṇḷṁṣśṛ', 'aiueotdnlmssr')


def fold(s):
    return re.sub(r'[^a-z]', '', (s or '').lower().translate(_FOLD))


def load():
    words = [r for r in csv.DictReader(open(WORDS, encoding='utf-8'), delimiter='\t')]
    sents = [r for r in csv.DictReader(open(SENTS, encoding='utf-8'), delimiter='\t')]
    vf = json.load(open(VERBFORMS, encoding='utf-8')) if os.path.exists(VERBFORMS) else {}
    return words, sents, vf


def family_counts():
    """Token frequency in the learner's own family recordings. Romanized and code-switched, so
    English is filtered out by requiring the token to appear in the word master."""
    c = Counter()
    for path in sorted(glob.glob(CONVOS)):
        for row in csv.DictReader(open(path, encoding='utf-8-sig')):
            for tok in re.split(r'[\s,.;:!?"“”]+', row.get('Telugu') or ''):
                f = fold(tok)
                if f:
                    c[f] += 1
    return c


def build_index(words, vf):
    """token-key -> the study item that covers it.

    Three ways a token is covered: the folded form is a word; the surface form is a Verb Lab
    cell of a verb you know; or a known word is a prefix of it and what remains is short enough
    to be an inflectional ending.

    That last rule needs the length guard. build_sentences uses a flat four-letter prefix, which
    is fine for tagging but far too loose here: it makes `nēnuvrāsānu` count as known the moment
    you learn `nēnu`, so a sentence you cannot read unlocks on day one. Capping the remainder at
    four characters keeps `vaddu -> vaddaṇḍi` while rejecting a whole second word.

    The verb-form route is tied to the headword: knowing `chēyi` covers `chēstānu`, knowing
    nothing does not."""
    by_fold, by_prefix = {}, {}
    for i, w in enumerate(words):
        for piece in (w['roman'] or '').split():
            f = fold(piece)
            if not f:
                continue
            by_fold.setdefault(f, i)
            if len(f) >= 4:
                by_prefix.setdefault(f, i)
    form_owner = {}
    for surface, meta in vf.items():
        owner = by_fold.get(fold(meta.get('root', '')))
        if owner is not None:
            form_owner[surface] = owner
    return by_fold, by_prefix, form_owner


def sentence_requirements(sents, words, index):
    """For each sentence, the set of word indices it needs. Tokens nothing covers are recorded
    as unresolvable — those sentences can never unlock, and the list of what they need is a
    shopping list for the word master."""
    by_fold, by_prefix, form_owner = index
    MAX_ENDING = 4        # longest plausible inflectional tail; beyond that it is a second word

    def cover(f):
        if f in by_fold:
            return by_fold[f]
        for cut in range(len(f) - 1, max(3, len(f) - MAX_ENDING) - 1, -1):
            if f[:cut] in by_prefix:
                return by_prefix[f[:cut]]
        return None
    reqs, missing = [], Counter()
    for s in sents:
        need, gaps = set(), 0
        toks_r = (s['roman'] or '').split()
        toks_t = (s['telugu'] or '').split()
        for j, tok in enumerate(toks_r):
            f = fold(tok)
            if not f:
                continue
            te = toks_t[j].strip('.,?!"') if j < len(toks_t) else ''
            if te in form_owner:
                need.add(form_owner[te]); continue
            hit = cover(f)
            if hit is not None:
                need.add(hit); continue
            gaps += 1
            missing[f] += 1
        reqs.append((need, gaps))
    return reqs, missing


def score_words(words, sents, fam):
    """Blended frequency: corpus occurrences plus family occurrences weighted up."""
    corpus = Counter()
    for s in sents:
        for tok in (s['roman'] or '').split():
            f = fold(tok)
            if f:
                corpus[f] += 1
    out = []
    for i, w in enumerate(words):
        f = fold(w['roman'])
        out.append(corpus.get(f, 0) + FAMILY_WEIGHT * fam.get(f, 0))
    return out


def greedy_order(eligible, reqs, score, k=12):
    """Order by `frequency + k × sentences-this-word-would-finish`, recomputed each step.

    Pure greedy on unlock alone looked better on the headline curve and was badly wrong. A word
    only scores if it *finishes* a sentence, so words appearing solely in sentences that can
    never unlock — 53% of the corpus is blocked by missing vocabulary — score zero forever and
    sink below every rare word that happened to complete one short sentence. It buried `nāku`,
    the second most frequent token in the corpus, at position 727.

    Combining the two fixes it: k is how many occurrences one finished sentence is worth. At
    k=12 a word that completes a sentence outranks a word seen a dozen times, which is about
    right, and high-frequency words can no longer be deferred indefinitely by a corpus artefact.

    Kept tractable by an inverted index from word to the sentences still waiting on it, and by
    only recomputing gain for the words a just-satisfied sentence touched."""
    waiting = defaultdict(set)          # word index -> sentences still needing it
    remaining = {}                      # sentence -> count of its words not yet taken
    for si, (need, gaps) in enumerate(reqs):
        if gaps or not need:
            continue                    # can never unlock, or is trivially empty
        remaining[si] = len(need)
        for wi in need:
            waiting[wi].add(si)

    gain = Counter()                    # word -> sentences it would finish right now
    for si, n in remaining.items():
        if n == 1:
            gain[next(iter(reqs[si][0]))] += 1

    order, taken = [], set()
    pool = set(eligible)
    while pool:
        best = max(pool, key=lambda wi: (score[wi] + k * gain.get(wi, 0), -wi))
        order.append(best); pool.discard(best); taken.add(best)
        for si in list(waiting.get(best, ())):
            remaining[si] -= 1
            if remaining[si] == 1:
                last = next(w for w in reqs[si][0] if w not in taken)
                gain[last] += 1
            elif remaining[si] == 0:
                gain[best] -= 1
        waiting.pop(best, None)
    return order


def curve(order, reqs, points):
    """(day, sentences fully known, sentences at one unknown) at each milestone."""
    pos = {wi: k for k, wi in enumerate(order)}
    out = []
    for n in points:
        known = set(order[:n])
        full = near = 0
        for need, gaps in reqs:
            if not need:
                continue
            unk = gaps + sum(1 for w in need if w not in known)
            if unk == 0:
                full += 1
            elif unk == 1:
                near += 1
        out.append((n, full, near))
    return out


def apply_existing(words, order):
    """Keep every position already assigned; append the rest after the last one."""
    fixed = {i: int(w['study_order']) for i, w in enumerate(words)
             if str(w.get('study_order', '')).isdigit()}
    if not fixed:
        return order, 0
    nxt = max(fixed.values())
    out = [None] * (nxt + 1)
    for i, p in fixed.items():
        if p - 1 < len(out):
            out[p - 1] = i
    appended = 0
    for wi in order:
        if wi in fixed:
            continue
        out.append(wi); appended += 1
    return [wi for wi in out if wi is not None], appended


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='compare orderings, write nothing')
    ap.add_argument('--reorder', action='store_true',
                    help='discard existing positions and re-sort everything. Correct once, '
                         'before the first import; destroys deck order afterwards.')
    ap.add_argument('--rate', type=int, default=WORDS_PER_DAY)
    ap.add_argument('--k', type=int, default=12,
                    help='occurrences one finished sentence is worth')
    ap.add_argument('--day', type=int, help='list what unlocks on this day')
    a = ap.parse_args()

    words, sents, vf = load()
    fam = family_counts()
    index = build_index(words, vf)
    reqs, missing = sentence_requirements(sents, words, index)
    score = score_words(words, sents, fam)

    eligible = [i for i, w in enumerate(words) if not (BLOCK & set(w['flags'].split()))]
    print(f'{len(words)} words ({len(eligible)} eligible), {len(sents)} sentences, '
          f'{len(fam)} distinct tokens in family recordings')

    ingest = eligible
    byfreq = sorted(eligible, key=lambda i: (-score[i], i))
    greedy = greedy_order(eligible, reqs, score, a.k)

    pts = [45, 150, 300, 450, 900, 1500]
    print(f'\n{"words":>6}{"day":>5}   {"ingestion":>16}{"frequency":>16}{"greedy":>16}   (fully known / +1 away)')
    for (n, f0, n0), (_, f1, n1), (_, f2, n2) in zip(
            curve(ingest, reqs, pts), curve(byfreq, reqs, pts), curve(greedy, reqs, pts)):
        print(f'{n:>6}{n // a.rate:>5}   {f0:>7} /{n0:>6}   {f1:>7} /{n1:>6}   {f2:>7} /{n2:>6}')

    best = greedy
    if not a.reorder:
        best, appended = apply_existing(words, greedy)
        if appended:
            print(f'\n  {appended} new words appended after position '
                  f'{len(best) - appended}; existing positions untouched')
        elif any(str(w.get('study_order', '')).isdigit() for w in words):
            print('\n  order unchanged (append-only; use --reorder to re-sort from scratch)')
    if a.day:
        pos = {wi: k for k, wi in enumerate(best)}
        show_day(words, sents, reqs, pos, a.day, a.rate)
        return
    if a.dry:
        return

    write(words, sents, reqs, best, a.rate, missing)


def show_day(words, sents, reqs, pos, day, rate):
    n = day * rate
    known = set(list(pos)[:n]) if False else {wi for wi, k in pos.items() if k < n}
    prev = {wi for wi, k in pos.items() if k < n - rate}
    new = [w for w in words if False]
    print(f'\nday {day}: words {n - rate + 1}–{n}')
    for wi, k in sorted(pos.items(), key=lambda kv: kv[1]):
        if n - rate <= k < n:
            w = words[wi]
            print(f'    {w["roman"]:<16}{w["telugu"]:<14}{w["english"][:44]}')
    fresh = []
    for si, (need, gaps) in enumerate(reqs):
        if gaps or not need:
            continue
        if all(x in known for x in need) and not all(x in prev for x in need):
            fresh.append(sents[si])
    print(f'\n  {len(fresh)} sentences become fully readable today:')
    for s in fresh[:20]:
        print(f'    {s["roman"][:60]:<62}{s["english"][:40]}')


def write(words, sents, reqs, order, rate, missing):
    pos = {wi: k for k, wi in enumerate(order)}
    for i, w in enumerate(words):
        k = pos.get(i)
        w['study_order'] = '' if k is None else k + 1
        w['study_day'] = '' if k is None else k // rate + 1

    for si, s in enumerate(sents):
        need, gaps = reqs[si]
        if gaps or not need:
            s['unlock_day'] = ''
            s['unlock_order'] = ''
            continue
        last = max(pos[w] for w in need if w in pos) if all(w in pos for w in need) else None
        if last is None:
            s['unlock_day'] = ''
            s['unlock_order'] = ''
        else:
            s['unlock_order'] = last + 1
            s['unlock_day'] = last // rate + 1

    for path, rows in ((WORDS, words), (SENTS, sents)):
        cols = list(rows[0].keys())
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', extrasaction='ignore')
            w.writeheader(); w.writerows(rows)

    dated = [s for s in sents if s['unlock_day']]
    print(f'\n  study_order written for {sum(1 for w in words if w["study_order"])} words')
    print(f'  unlock_day written for {len(dated)} of {len(sents)} sentences')
    print(f'  {len(sents) - len(dated)} never unlock — they contain words not in the master')
    if missing:
        print(f'\n  most-wanted missing words (shopping list, {len(missing)} distinct):')
        for tok, n in missing.most_common(12):
            print(f'    {n:>4}  {tok}')


if __name__ == '__main__':
    main()
