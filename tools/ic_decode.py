# -*- coding: utf-8 -*-
"""Decipher the lesson PDFs' legacy Telugu font, and decode every lesson with it.

    python3 tools/ic_decode.py --learn      # induce intensive/glyphmap.tsv from the aligned turns
    python3 tools/ic_decode.py --check      # accuracy of the current map, held out honestly
    python3 tools/ic_decode.py              # decode raw/lesson-NN.tsv -> work/NN.tsv

THE PROBLEM
The Telugu in these PDFs is set in a pre-Unicode font with no ToUnicode map, so it extracts as
`A¨ HÑ$sìý?` rather than `అది ఏమిటి?`. The font's own encoding is the only key, and it is not
published. Three facts make recovering it tractable:

  1. The encoding is GLOBAL, not per-file. The subset fonts have meaningless per-file names
     (TT371O00, TT694O00, ...) but preserve the original character codes, so `A¨` is అది
     everywhere — verified in 47 of the 64 files, and the same codes appear across nine
     different subset fonts.
  2. The inventory is small: 209 distinct codes in the whole book, 142 covering 99% of use.
  3. Lessons 1-6 print the same sentences twice — once in the legacy font and once in the
     book's own romanization. ic_rom2te turns that romanization into known-correct Telugu
     (182/182 round-trip clean through te2rom.py), which is a parallel corpus: 859 word pairs
     of (legacy bytes, correct Telugu).

WHY IT IS LEARNED AND NOT HAND-WRITTEN
142 glyphs could be identified by rendering each and reading it, and that is how the
romanization diacritics were settled. It is the wrong tool here. A legacy Telugu glyph is a
*piece* — a bare consonant, a vowel sign, a subscript conjunct — and naming the piece is not
the same as knowing where its codepoints go in the Unicode string. Induction from a parallel
corpus learns the placement and the identity together, and every entry is backed by how many
times it was observed rather than by one reading of one rendering.

THE MODEL
Monotone segmentation: each legacy glyph emits between zero and four Telugu codepoints, in
order. Zero matters — some syllables take two glyphs to write, so one of them must be allowed
to contribute nothing on its own. Trained by EM (forward-backward over the alignment lattice,
then renormalise), which is the standard treatment for exactly this shape of problem and needs
no alignment supervision beyond the word pairing itself.

WHAT THIS IS NOT
Not a general converter for legacy Telugu documents. It is fitted to one book's font, and its
only warrant is the accuracy number --check prints. Anything it decodes below that confidence
is data to be reviewed, not truth.
"""
import argparse
import collections
import csv
import hashlib
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import ic_rom2te
import te2rom

RAW = os.path.join(ROOT, 'intensive', 'raw')
HELDOUT = 0.15       # see is_heldout()
MAPFILE = os.path.join(ROOT, 'intensive', 'glyphmap.tsv')
MAXEMIT = 4          # one unit never spells more than a full CV syllable plus a sign
MAXSRC = 5           # ...and is written with up to five legacy codes. `Ææÿ$` is four of them
                     # and spells రు; capping at three split it and cost ~10% of the words.
PASSTHROUGH = set(" \t.,?!:;'\"()-–/0123456789")


def word_pairs(path):
    """(legacy word, correct Telugu word) from the turns that carry both."""
    out = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            leg, rom = row['legacy'].split(), row['rom'].strip()
            if not rom:
                continue
            tel = ic_rom2te.convert(rom).split()
            # Unequal token counts mean the two columns disagree about where words end;
            # aligning them anyway would teach the model noise. Drop the turn.
            if len(leg) == len(tel):
                out.extend(zip(leg, tel))
    return out


def inline_word_pairs(path):
    """The grammar notes' inline glosses: (legacy word, correct Telugu word).

    Already word-level, so there is no tokenisation to reconcile — but each one is still put
    through the same gate as everything else. If ic_rom2te's output does not come back
    identical through te2rom.py, the romanization was not what this parser thinks it was and
    the pair is dropped rather than taught.
    """
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            leg, rom = row['legacy'].strip(), row['rom'].strip()
            if not leg or not rom:
                continue
            tel = ic_rom2te.convert(rom)
            if ic_rom2te.normalise(te2rom.romanize(tel, assimilate=False)) == rom.lower():
                out.append((leg, tel))
    return out


def is_heldout(legacy):
    """A fixed 15% of word types, chosen by hash of the legacy string.

    Not a random sample and not a slice off the end: hashing means the same words are held out
    on every run regardless of extraction order, so two runs are comparable, and a word can
    never drift between train and test as the corpus grows.

    This matters more than it looks. Until this existed, --check scored the decoder on the very
    pairs it had trained on and reported 84.1%, which measured memorisation. The number below
    is the one that says whether the map generalises to the 58 lessons that have no
    romanization at all — which is the entire purpose of the exercise.
    """
    h = hashlib.sha1(legacy.encode('utf-8')).hexdigest()
    return int(h[:8], 16) % 1000 < HELDOUT * 1000


def em(pairs, iters=14):
    """Forward-backward over the monotone alignment lattice; return P(telugu | glyph)."""
    prob = collections.defaultdict(lambda: collections.defaultdict(float))
    for g, t in pairs:
        # Every segment the unit could be responsible for, ANYWHERE in the word — not just a
        # prefix of it. Seeding prefixes only was the first version and it starved every
        # mid-word segment, so the lattice could not route through them.
        for i in range(len(g)):
            for s_ in range(1, min(MAXSRC, len(g) - i) + 1):
                src = g[i:i + s_]
                for j in range(len(t) + 1):
                    for k in range(min(MAXEMIT, len(t) - j) + 1):
                        prob[src][t[j:j + k]] += 1.0
    for g in prob:
        z = sum(prob[g].values())
        for t in prob[g]:
            prob[g][t] /= z

    for _ in range(iters):
        cnt = collections.defaultdict(lambda: collections.defaultdict(float))
        for L, T in pairs:
            m, n = len(L), len(T)
            # forward
            a = [[0.0] * (n + 1) for _ in range(m + 1)]
            a[0][0] = 1.0
            for i in range(m):
                for j in range(n + 1):
                    if not a[i][j]:
                        continue
                    for s_ in range(1, min(MAXSRC, m - i) + 1):
                        d = prob.get(L[i:i + s_])
                        if not d:
                            continue
                        for k in range(min(MAXEMIT, n - j) + 1):
                            p = d.get(T[j:j + k], 0.0)
                            if p:
                                a[i + s_][j + k] += a[i][j] * p
            if not a[m][n]:
                continue                                  # no path: skip rather than distort
            # backward
            b = [[0.0] * (n + 1) for _ in range(m + 1)]
            b[m][n] = 1.0
            for i in range(m - 1, -1, -1):
                for j in range(n, -1, -1):
                    acc = 0.0
                    for s_ in range(1, min(MAXSRC, m - i) + 1):
                        d = prob.get(L[i:i + s_])
                        if not d:
                            continue
                        for k in range(min(MAXEMIT, n - j) + 1):
                            p = d.get(T[j:j + k], 0.0)
                            if p:
                                acc += p * b[i + s_][j + k]
                    b[i][j] = acc
            z = a[m][n]
            for i in range(m):
                for j in range(n + 1):
                    if not a[i][j]:
                        continue
                    for s_ in range(1, min(MAXSRC, m - i) + 1):
                        src = L[i:i + s_]
                        d = prob.get(src)
                        if not d:
                            continue
                        for k in range(min(MAXEMIT, n - j) + 1):
                            seg = T[j:j + k]
                            p = d.get(seg, 0.0)
                            if p:
                                cnt[src][seg] += a[i][j] * p * b[i + s_][j + k] / z
        prob = collections.defaultdict(lambda: collections.defaultdict(float))
        for g, d in cnt.items():
            z = sum(d.values())
            if z <= 0:
                continue            # a unit no surviving alignment used; drop it
            for t, c in d.items():
                if c / z > 1e-4:
                    prob[g][t] = c / z
    return prob, {g: sum(d.values()) for g, d in cnt.items()}


MINUSE = 1.5    # see best_map()


def best_map(prob, used):
    """The argmax reading of each unit, keeping only units the model genuinely relies on.

    `used` is the expected number of times EM actually routed an alignment through the unit,
    which is not the same as how often its characters co-occur. Units below the threshold are
    almost always a whole word memorised once: they fit that word perfectly, apply to nothing
    else, and — because the decoder scores by log-probability — outrank the short well-attested
    units that would have generalised. Dropping them is what separates 48% on unseen words
    from something usable.
    """
    out = {}
    for g, d in prob.items():
        if used.get(g, 0.0) < MINUSE and len(g) > 1:
            continue
        t, p = max(d.items(), key=lambda kv: kv[1])
        out[g] = (t, p, round(used.get(g, 0.0), 2))
    return out


def load_map(path=MAPFILE):
    m = {}
    if not os.path.exists(path):
        return m
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            p = float(row['confidence']) or 1e-6
            m[row['glyph']] = (row['telugu'], math.log(p))
    return m


def decode_word(w, m, lex=None, beam=24):
    """Beam search over segmentations, not greedy longest-match.

    Longest-match was the first version and it is wrong for a reason worth recording: with
    ~4,000 learned units, a long unit almost always exists at any position, and taking it
    because it is long ignores how well it is attested. Scoring the whole segmentation instead
    — log-probability, plus a mild preference for fewer/longer units to break ties — lets a
    confident short unit beat a spurious long one.

    The lexicon is applied at the END, over finished candidates, never during the search. A
    decode that spells a word this project already knows is almost certainly right, but using
    that to prune mid-word would bias every partial string toward a prefix of some known word.
    """
    n = len(w)
    paths = {0: [(0.0, '')]}
    for i in range(n):
        if i not in paths:
            continue
        for s_ in range(1, min(MAXSRC, n - i) + 1):
            e = m.get(w[i:i + s_])
            if not e:
                continue
            t, lp = e
            for sc, txt in paths[i]:
                nxt = paths.setdefault(i + s_, [])
                nxt.append((sc + lp, txt + t))
        for k in paths:
            if len(paths[k]) > beam:
                paths[k] = sorted(paths[k], key=lambda x: -x[0])[:beam]
    if n not in paths or not paths[n]:
        return w
    cands = sorted(paths[n], key=lambda x: -x[0])[:beam]
    if lex:
        for sc, txt in cands:
            if txt in lex:
                return txt
    return cands[0][1]


def decode(s, m, lex=None):
    """Word by word — punctuation and spaces pass through untouched."""
    out = []
    for tok in re.split(r'(\s+)', s):
        if not tok or tok.isspace():
            out.append(tok); continue
        head = ''
        while tok and tok[0] in PASSTHROUGH:
            head += tok[0]; tok = tok[1:]
        tail = ''
        while tok and tok[-1] in PASSTHROUGH:
            tail = tok[-1] + tail; tok = tok[:-1]
        out.append(head + (decode_word(tok, m, lex) if tok else '') + tail)
    return ''.join(out)


def lexicon():
    """Every Telugu word this project already knows, as a target-side vocabulary.

    2,215 master words plus every word of the 2,880 master sentences. Nothing about these is
    specific to the book — they are simply real Telugu, which is what a decode has to be.
    """
    words = set()
    for fn, col in (('master_words.tsv', 'telugu'), ('master_sentences.tsv', 'telugu')):
        p = os.path.join(ROOT, 'data', fn)
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                for w in (row.get(col) or '').split():
                    w = w.strip('.,?!;:"\'()')
                    if len(w) >= 3:
                        words.add(w)
    return words


def legacy_types():
    """Every distinct legacy word in the book, with how often it occurs."""
    c = collections.Counter()
    for fn in sorted(os.listdir(RAW)):
        if not fn.startswith('lesson-'):
            continue
        with open(os.path.join(RAW, fn), encoding='utf-8') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                for w in row['legacy'].split():
                    w = w.strip('.,?!;:"\'()')
                    if w:
                        c[w] += 1
    return c


def bootstrap(pairs, rounds=4):
    """Self-training: decode the book, keep whatever landed on a real Telugu word, retrain.

    The 182 aligned turns are too thin on their own — 324 distinct word pairs against 141
    glyphs, and EM settles into a local optimum worth about half the words. But a partly-right
    map still decodes plenty of words *exactly*, and a decode that lands on a word already in
    the project's lexicon is almost certainly right: the space of Telugu strings is enormous
    and the space of real Telugu words is not, so agreement is not something a wrong map
    stumbles into. Those become new training pairs, which sharpen the map, which decodes more
    words. Three or four rounds is where it stops moving.

    The seed pairs keep their weight throughout — they are checked ground truth, and the
    bootstrap is only allowed to add to them, never to outvote them.
    """
    lex = lexicon()
    types = legacy_types()
    m = best_map(*em(pairs))
    print(f'  seed          -> {len(m)} units')
    for r in range(rounds):
        gained = []
        for lw, n in types.items():
            d = decode_word(lw, {g: (t, math.log(p or 1e-6)) for g, (t, p, _) in m.items()})
            if len(d) >= 3 and d in lex:
                gained.extend([(lw, d)] * min(n, 3))
        allp = pairs * 3 + gained
        m = best_map(*em(allp))
        print(f'  round {r + 1}: +{len(set(gained))} bootstrapped word types '
              f'({len(allp)} training pairs) -> {len(m)} units')
    return m


def cmd_learn(args):
    pairs = word_pairs(os.path.join(RAW, 'pairs.tsv'))
    inline = inline_word_pairs(os.path.join(RAW, 'inline_pairs.tsv'))
    print(f'{len(pairs)} word pairs from the lessons 1-6 dialogues ({len(set(pairs))} distinct)')
    print(f'{len(inline)} from inline glosses across all 64 lessons ({len(set(inline))} distinct)')
    pairs = pairs + inline * 2
    held = [p for p in pairs if is_heldout(p[0])]
    pairs = [p for p in pairs if not is_heldout(p[0])]
    print(f'{len(set(held))} distinct word types held out of training ({HELDOUT:.0%})')
    m = bootstrap(pairs)
    os.makedirs(os.path.dirname(MAPFILE), exist_ok=True)
    with open(MAPFILE, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['glyph', 'telugu', 'confidence', 'seen'])
        for g, (t, p, n) in sorted(m.items(), key=lambda kv: -kv[1][2]):
            w.writerow([g, t, f'{p:.3f}', n])
    strong = sum(1 for _, (t, p, n) in m.items() if p > 0.9)
    print(f'{len(m)} units kept, {strong} at confidence > 0.90 -> intensive/glyphmap.tsv')
    cmd_check(args)


def cmd_check(args):
    """Decode the legacy side and compare with the romanization the book printed beside it.

    Word accuracy is measured over the FIXED set of word pairs, not over whatever turns
    happened to tokenise evenly — an earlier version recomputed the denominator each run, so
    two runs could not be compared and a change that dropped a hard turn looked like progress.
    """
    m = load_map()
    if not m:
        sys.exit('no glyphmap.tsv — run --learn first')
    lex = lexicon()

    wp = word_pairs(os.path.join(RAW, 'pairs.tsv'))
    wp += inline_word_pairs(os.path.join(RAW, 'inline_pairs.tsv'))
    seen, uniq = set(), []
    for pr in wp:
        if pr not in seen:
            seen.add(pr); uniq.append(pr)
    tr = [p for p in uniq if not is_heldout(p[0])]
    ho = [p for p in uniq if is_heldout(p[0])]
    for label, part in (('HELD OUT (never trained on)', ho), ('seen in training', tr)):
        if not part:
            continue
        ok = sum(1 for lw, gold in part if decode_word(lw, m, lex) == gold)
        print(f'  {label:28} {ok}/{len(part)} words ({ok/len(part):.1%})')

    tot = exact = 0
    misses = []
    with open(os.path.join(RAW, 'pairs.tsv'), encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            gold = row['rom'].strip().lower()
            if not gold:
                continue
            got = ic_rom2te.normalise(te2rom.romanize(decode(row['legacy'], m, lex),
                                                     assimilate=False)).lower()
            tot += 1
            if got == gold:
                exact += 1
            elif len(misses) < 8:
                misses.append((gold, got))
    print(f'turns decoded exactly: {exact}/{tot} ({exact/max(tot,1):.1%})')
    for g, o in misses:
        print(f'\n  book    {g}\n  decoded {o}')


def cmd_apply(args):
    m = load_map()
    if not m:
        sys.exit('no glyphmap.tsv — run --learn first')
    lex = lexicon()
    out = os.path.join(ROOT, 'intensive', 'work')
    os.makedirs(out, exist_ok=True)
    n = rows = 0
    for fn in sorted(os.listdir(RAW)):
        if not fn.startswith('lesson-'):
            continue
        src = os.path.join(RAW, fn)
        with open(src, encoding='utf-8') as f:
            data = list(csv.DictReader(f, delimiter='\t'))
        for r in data:
            r['te'] = decode(r['legacy'], m, lex)
        dst = os.path.join(out, fn.replace('lesson-', ''))
        with open(dst, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, delimiter='\t',
                               fieldnames=['lesson', 'seq', 'speaker', 'en', 'te',
                                           'rom', 'legacy', 'flags'])
            w.writeheader()
            w.writerows(data)
        n += 1; rows += len(data)
    print(f'{n} lessons, {rows} turns decoded -> intensive/work/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--learn', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    (cmd_learn if args.learn else cmd_check if args.check else cmd_apply)(args)


if __name__ == '__main__':
    main()
