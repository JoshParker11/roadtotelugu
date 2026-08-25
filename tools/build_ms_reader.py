# -*- coding: utf-8 -*-
"""Bake the translated Mini Stories into the LingQ-style reader.

    python3 tools/build_ms_reader.py

Writes:
    reader/data/ministories.js      window.MS_DATA — every fully-translated story, resolved
    ministories/word_audio.tsv      guid<TAB>telugu for every distinct word, the manifest
                                    ms_audio.py --words reads to synthesize per-word clips

WHAT IS DELIBERATELY REUSED, AND FROM WHERE
Everything load-bearing here already exists somewhere in this repo, and this file imports it
rather than re-deriving it:

  - Play order and audio cue times come from ms_lr_export (sort_key / gap_before / duration),
    so the baked seek offsets match lr/story_NN.mp3 exactly — same functions, same constants,
    byte-identical arithmetic. If ms_lr_export changes its gaps, re-run this.
  - Word identity is ids.guid('W', script) — the same content hash the word master uses, which
    is what makes a word marked known in the novel's reader show as known here for free.
    Where a surface form IS a master word, the master's own guid is used (they agree anyway;
    verified 2207/2207 on the current master).
  - Gloss resolution reuses build_reader.load_lexicon / decompose and the Verb Lab's
    verbforms.json, the same resolution order the existing reader was built on.

CANONICAL DATA IS TELUGU SCRIPT, ALWAYS
No romanization is baked. The reader romanizes at render time (Te2Rom or Colloquial, both
already in the repo), because script is the unambiguous form and romanization is a display
preference. The only Latin here is the English gloss/translation columns.

ZERO-WIDTH JOINERS
Surface forms keep ZWNJ/ZWJ (స్కూల్‌కి is one word); keys and guids strip them, the same
rule lex.js already applies, so a word written with the joiner and one written without share
an identity. Master lookups go through a stripped index for the same reason.
"""
import csv
import glob
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from ids import guid
from ms_segment import RETELL
from ms_lr_export import story_rows, sort_key, gap_before, duration
from build_reader import load_lexicon

MS = os.path.join(ROOT, 'ministories')
CATALOG = os.path.join(MS, 'CATALOG.tsv')
AUDIO = os.path.join(MS, 'audio')
LR = os.path.join(MS, 'lr')
OUT_JS = os.path.join(ROOT, 'reader', 'data', 'ministories.js')
OUT_MANIFEST = os.path.join(MS, 'word_audio.tsv')
VOCAB = os.path.join(MS, 'vocab.tsv')
VERBFORMS = os.path.join(HERE, 'verbforms.json')

# Mirrors lex.js TOKEN exactly: the Telugu run includes ZWNJ/ZWJ because they sit *inside*
# words (మైక్‌కి), and build_reader.py's own regex, which predates the Mini Stories, does not
# include them — using it here would split every joiner-carrying name+case form in two.
TOKEN = re.compile(r"[ఀ-౿‌‍]+|[^\W\d_]+(?:['’][^\W\d_]+)*|\d+|[^\w\s]+|\s+")
TELUGU = re.compile(r"[ఀ-౿]")
ZERO_WIDTH = re.compile(r"[​-‍﻿]")

bare = lambda s: ZERO_WIDTH.sub('', s or '').strip()


def load_verbforms_meta(by_te_bare):
    """surface -> (form, lemma, head_row|None). Unlike build_reader.load_verbforms, the lemma
    id is kept — the reader's Forms tab uses it to open the verb's actual paradigm in the
    Verb Lab instead of re-deriving it."""
    if not os.path.exists(VERBFORMS):
        return {}
    vf = json.load(open(VERBFORMS, encoding='utf-8'))
    out = {}
    for surface, meta in vf.items():
        head = by_te_bare.get(bare(meta.get('root', '')))
        out[bare(surface)] = (meta.get('form', ''), meta.get('lemma', ''), head)
    return out


def load_suffixes(by_te_bare):
    """Bound suffixes the master glosses, longest first — same rule as build_reader."""
    out = []
    for te, r in by_te_bare.items():
        if 'bound-suffix' not in (r.get('flags') or ''):
            continue
        t = te.strip('-').strip()
        if t:
            out.append((t, r))
    return sorted(out, key=lambda x: -len(x[0]))


def decompose(te, by_te_bare, suffixes):
    """Known stem + known bound suffix, one layer deep — build_reader's rule, on script keys."""
    for suf, srow in suffixes:
        if len(te) <= len(suf) or not te.endswith(suf):
            continue
        stem = te[:-len(suf)]
        if len(stem) < 2:
            continue
        row = by_te_bare.get(stem)
        if row is None:
            continue
        return row, [[row['roman'], row['english'][:60]],
                     ['-' + srow['roman'].lstrip('-'), srow['english'][:60]]]
    return None


def load_vocab():
    """guid -> [sense, ...] from ministories/vocab.tsv, in sense order.

    The registry is optional: it may not exist yet, and it will always cover fewer words than the
    corpus contains while it is being filled in. A missing file or a missing word means the card
    falls back to whatever the resolver already worked out (master gloss, Verb Lab form, or
    stem+suffix), which is exactly the behaviour before this existed.

    Keys are shortened for the baked JSON because every byte here ships to the browser on every
    page load: g=gloss, p=pos, x=explain, c=context segment guid, s=status. Status rides along so
    the reader can mark a card as unreviewed — nothing checks an explanation's correctness, and
    the card should not imply otherwise.
    """
    if not os.path.exists(VOCAB):
        return {}
    out = {}
    with open(VOCAB, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if not (r.get('guid') or '').strip():
                continue
            n = str(r.get('sense_no') or '1')
            out.setdefault(r['guid'], []).append({
                'n': int(n) if n.isdigit() else 1,
                'g': r.get('gloss', ''), 'p': r.get('pos', ''), 'x': r.get('explain', ''),
                'c': r.get('context_guid', ''), 's': r.get('status', 'draft')})
    # Sense 1 is the first-met sense and must render first (DECISIONS.md: the registry only ever
    # appends). ms_vocab.py already writes the file in that order, but a hand-edited or
    # concatenated file should not be able to silently reorder a word's card.
    for senses in out.values():
        senses.sort(key=lambda d: d['n'])
    return out


class Resolver:
    def __init__(self):
        _, _, by_te = load_lexicon()
        # A stripped-script index. The master contains both joiner and joiner-free spellings;
        # keying on the stripped form lets either match either.
        self.by_te = {}
        for te, row in by_te.items():
            self.by_te.setdefault(bare(te), row)
        self.verbforms = load_verbforms_meta(self.by_te)
        self.suffixes = load_suffixes(self.by_te)
        self.lex = []          # global across all stories
        self.lexidx = {}       # guid -> index

    def slot(self, g, entry):
        if g not in self.lexidx:
            self.lexidx[g] = len(self.lex)
            entry['g'] = g
            self.lex.append(entry)
        return self.lexidx[g]

    def resolve_line(self, text):
        out = []
        for piece in TOKEN.findall(text):
            if not TELUGU.search(piece):
                out.append([piece, 'p', -1])
                continue
            b = bare(piece)
            hit = self.by_te.get(b)
            if hit is not None:
                li = self.slot(hit['guid'], {
                    'te': b, 'r': hit['roman'], 'en': hit['english'],
                    'o': int(hit['study_order']) if str(hit['study_order']).isdigit() else 0})
                out.append([piece, 't', li])
                continue
            g = guid('W', b)
            vf = self.verbforms.get(b)
            if vf is not None:
                form, lemma, head = vf
                e = {'te': b, 'en': '', 'o': 0, 'form': form, 'lemma': lemma}
                if head is not None:
                    e['head'] = [head['roman'], head['english'][:60]]
                out.append([piece, 'v', self.slot(g, e)])
                continue
            got = decompose(b, self.by_te, self.suffixes)
            if got is not None:
                row, parts = got
                e = {'te': b, 'en': ' + '.join(f'{a} ({x})' for a, x in parts),
                     'o': 0, 'p': parts}
                out.append([piece, 's', self.slot(g, e)])
                continue
            out.append([piece, 'w', self.slot(g, {'te': b, 'en': '', 'o': 0})])
        return out


def part_tag(r):
    if r['part'] != 'meta':
        return r['part']
    return 'retell-intro' if RETELL.match(r['en']) else 'title'


def bake_story(num, cat, rs):
    rows = story_rows(num, cat)
    if not rows or any(not r['te'].strip() for r in rows):
        return None                                # untranslated (or partially) — skip

    have_audio = all(os.path.exists(os.path.join(AUDIO, r['guid'] + '.mp3')) for r in rows)
    lr_mp3 = os.path.join(LR, f'story_{int(num):02d}.mp3')
    have_audio = have_audio and os.path.exists(lr_mp3)

    lines, t, prev = [], 0.0, None
    title = {'te': '', 'en': ''}
    for r in rows:
        tag = part_tag(r)
        ln = {'g': r['guid'], 'p': tag,
              't': rs.resolve_line(r['te']), 'en': r['en']}
        if have_audio:
            t += gap_before(prev, r)
            d = duration(os.path.join(AUDIO, r['guid'] + '.mp3'))
            ln['s'] = round(t, 2)
            ln['e'] = round(t + d, 2)
            t += d
        if tag == 'title' and not title['te']:
            title = {'te': r['te'], 'en': r['en']}
        prev = r
        lines.append(ln)

    return {'num': int(num), 'title': title,
            'audio': f'../ministories/lr/story_{int(num):02d}.mp3' if have_audio else '',
            'dur': round(t, 2) if have_audio else 0,
            'lines': lines}


def main():
    with open(CATALOG, encoding='utf-8') as f:
        cat = {r['id']: r for r in csv.DictReader(f, delimiter='\t')}
    nums = sorted({int(r['num']) for r in cat.values()})

    rs = Resolver()
    stories = []
    for n in nums:
        s = bake_story(n, cat, rs)
        if s:
            stories.append(s)

    # Frequency and first-story-of-occurrence, over the whole baked corpus. The vocabulary
    # list sorts on both.
    freq, first = {}, {}
    for s in stories:
        for ln in s['lines']:
            for tok in ln['t']:
                if tok[2] >= 0:
                    freq[tok[2]] = freq.get(tok[2], 0) + 1
                    first.setdefault(tok[2], s['num'])
    for i, l in enumerate(rs.lex):
        l['n'] = freq.get(i, 0)
        l['f'] = first.get(i, 0)

    # Merge the word registry. This is additive: a word with no row keeps exactly the card it
    # had before, so the reader degrades gracefully while vocab.tsv is still being filled in.
    vocab = load_vocab()
    carded = 0
    for l in rs.lex:
        senses = vocab.get(l['g'])
        if senses:
            l['sn'] = senses
            carded += 1

    data = {'generated': date.today().isoformat(),
            'source': 'LingQ Mini Stories',
            'lex': rs.lex, 'stories': stories}

    os.makedirs(os.path.dirname(OUT_JS), exist_ok=True)
    with open(OUT_JS, 'w', encoding='utf-8') as f:
        f.write('/* Generated by tools/build_ms_reader.py. Do not edit. */\n')
        f.write('window.MS_DATA = ' +
                json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')

    with open(OUT_MANIFEST, 'w', encoding='utf-8') as f:
        f.write('guid\tte\n')
        for l in rs.lex:
            f.write(f"{l['g']}\t{l['te']}\n")

    voiced = sum(1 for s in stories if s['audio'])
    print(f'{os.path.relpath(OUT_JS, ROOT)}  {os.path.getsize(OUT_JS)/1024:.0f} KB')
    print(f'  {len(stories)} stories baked ({voiced} with audio), '
          f'{len(rs.lex)} distinct words')
    kinds = {}
    for s in stories:
        for ln in s['lines']:
            for tok in ln['t']:
                if tok[1] != 'p':
                    kinds[tok[1]] = kinds.get(tok[1], 0) + 1
    tot = sum(kinds.values())
    for k, label in (('t', 'master word'), ('v', 'Verb Lab form'),
                     ('s', 'stem + suffix'), ('w', 'unresolved')):
        n = kinds.get(k, 0)
        print(f'    {label:<16}{n:>6}  {n/tot*100:>4.0f}%' if tot else '')
    pct = carded * 100 // max(1, len(rs.lex))
    print(f'    registry card   {carded:>6}  {pct:>4}%  (ministories/vocab.tsv)')
    print(f'{os.path.relpath(OUT_MANIFEST, ROOT)}  {len(rs.lex)} rows '
          f'(feed to ms_audio.py --words for per-word clips)')


if __name__ == '__main__':
    main()
