# -*- coding: utf-8 -*-
"""Bake a text into a readable, markable page — the LingQ mechanic, offline.

    python3 tools/build_reader.py --list
    python3 tools/build_reader.py conversations
    python3 tools/build_reader.py --all

WHY OFFLINE AND BAKED
Resolving a Telugu token needs the word master, the fold logic and a 235k-word English
dictionary. Doing that in the browser means shipping all three; doing it here means shipping a
resolved text. The site stays static, works from file://, and needs no backend — the same
constraint every other page here is built to.

THE MATCHING PROBLEM, WHICH IS THE WHOLE FEATURE
The family transcripts are written in the romanization Telugu speakers actually type — adhi,
kooda, aayana, vaallu — while the master uses the project's diacritic scheme: adi, kūḍā,
āyana, vāḷḷu. Folding diacritics alone matched 19% of tokens. The two conventions disagree
about long vowels (doubled letters vs macrons) and about dentals (dh/th vs d/t), so `loose()`
collapses both to the same skeleton.

ORDER OF RESOLUTION MATTERS MORE THAN THE FOLD
Exact, then English, then loose. Putting English last matched "the" to ṭī and "was" to vāṣ,
which is worse than no match at all: a wrong gloss is trusted, a missing one is looked up. For
the same reason multi-word phrase rows are kept out of the index — they made half the loose
matches ambiguous — and loose matches are marked `~` so the page can show them as guesses.

Measured on the 513 family lines: 19% exact, 13% approximate, 39% English or names,
27% genuinely unknown. That last 27% is not a failure, it is the point — those are the
words to mine. On the public textbook text, where the romanization already matches the
master's, it is 87% exact.

PRIVACY
`sources/private/` is gitignored because the recordings contain relatives' names, health and
money talk, and nobody in them agreed to be published. Sources marked private emit to
STUDY/data/reader/private-*.js, which is gitignored too. Nothing derived from them is ever
committed.
"""
import argparse, csv, glob, json, os, re, sys
from collections import Counter, defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
WORDS = os.path.join(ROOT, 'data', 'master_words.tsv')
SENTS = os.path.join(ROOT, 'data', 'master_sentences.tsv')
OUTDIR = os.path.join(ROOT, 'STUDY', 'data', 'reader')
SYSDICT = '/usr/share/dict/words'

sys.path.insert(0, HERE)
from te2rom import romanize

_F = str.maketrans('āīūēōṭḍṇḷṁṣśṛ', 'aiueotdnlmssr')

# In the master and unambiguously Telugu, but also present in an English dictionary. Without
# this they would be resolved as English and never glossed.
NOT_ENGLISH = {'aa', 'ee', 'oo', 'na', 'ni', 'ma', 'mi', 'anna', 'akka', 'ela', 'ide', 'ade'}


def fold(s):
    return re.sub(r'[^a-z]', '', (s or '').lower().translate(_F))


def loose(s):
    """Collapse either romanization convention onto one skeleton.

    Doubled letters go to single (kooda/kūḍā), dh/th lose the h (adhi/adi) because chat
    spelling uses them for the dentals English ears hear as d/t, and the two commonly confused
    vowel pairs merge: e/i and o/u. Aggressive on purpose — precision is recovered by trying
    this only after an exact match and an English check have both failed.
    """
    t = re.sub(r'[^a-z]', '', (s or '').lower().translate(_F))
    t = t.replace('chh', 'c').replace('ch', 'c')
    t = re.sub(r'dh|th', lambda m: m.group(0)[0], t)
    t = re.sub(r'(.)\1', r'\1', t)
    t = t.replace('w', 'v')
    t = re.sub(r'[ei]+', 'I', t)
    t = re.sub(r'[ou]+', 'U', t)
    t = re.sub(r'a+', 'a', t)
    return t


def load_verbforms(exact_by_te):
    """Every conjugated cell the Verb Lab generates, keyed by its Telugu surface.

    The Lab already produces ~2,900 of these and the reader was ignoring all of them, so
    `untadi`, `chēstunnāru` and their kin fell through to "unknown" even though the headword
    is in the deck and the paradigm is on another page of this same site. verbforms.json maps
    surface -> {lemma, root, form}; the root is the headword's script, which the master can
    gloss."""
    path = os.path.join(HERE, 'verbforms.json')
    if not os.path.exists(path):
        return {}
    vf = json.load(open(path, encoding='utf-8'))
    out = {}
    for surface, meta in vf.items():
        head = exact_by_te.get((meta.get('root') or '').strip())
        if head:
            out[surface] = (head, meta.get('form', ''))
    return out


def load_suffixes(exact_by_te):
    """The bound suffixes the master already glosses — -ki, -lō, -tō, -lu, -gā and friends.

    Telugu is agglutinative, so matching whole surface forms against a headword list misses
    most of a real transcript. Decomposing is not stripping: the word on the page is untouched
    and both halves get shown, which for a case ending is the more useful half of the lesson.

    Longest first, or -lu would win over -lugā."""
    out = []
    for te, r in exact_by_te.items():
        if 'bound-suffix' not in r['flags']:
            continue
        t = te.strip('-').strip()
        if len(t) >= 1:
            out.append((t, r))
    return sorted(out, key=lambda x: -len(x[0]))


def load_lexicon():
    exact, approx = {}, defaultdict(list)
    with open(WORDS, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            rom = (r['roman'] or '').strip()
            # Single words only. Phrase rows ("mīru eṭla unnāru?") fold to whatever their first
            # word folds to and made half the loose matches ambiguous.
            if not rom or ' ' in rom:
                continue
            k = fold(rom)
            if not k:
                continue
            exact.setdefault(k, r)
            approx[loose(rom)].append(r)
    for k in approx:
        approx[k].sort(key=lambda r: int(r['study_order']) if str(r['study_order']).isdigit() else 99999)

    by_te = {}
    with open(WORDS, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            te = (r['telugu'] or '').strip()
            if te:
                by_te.setdefault(te, r)
    return exact, approx, by_te


def load_english():
    if not os.path.exists(SYSDICT):
        print('  note: no /usr/share/dict/words — English words will show as unknown')
        return set()
    with open(SYSDICT, encoding='utf-8', errors='ignore') as f:
        return {w.strip().lower() for w in f} - NOT_ENGLISH


# ---------------------------------------------------------------- sources

def src_conversations():
    """The learner's own family, recorded at home. PRIVATE — see the module docstring."""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'sources', 'private', 'conversations', '*.csv'))):
        rows = list(csv.DictReader(open(p, encoding='utf-8-sig')))
        out.append({'title': os.path.basename(p).replace('.csv', ''),
                    'lines': [(r.get('Telugu', ''), r.get('English', '')) for r in rows
                              if (r.get('Telugu') or '').strip()]})
    return out


TS = re.compile(r'^(\d{2}):(\d{2}):(\d{2})\.(\d+)\s+(.*)$')


def src_podcast():
    """Raw Talks #139 — 1h16m, Telugu script with a start time on every line.

    BAKED LOCALLY, NEVER COMMITTED. The output goes to a gitignored local-*.js, because the
    transcript is the whole of a copyrighted episode. Baking it anyway is worth doing: it makes
    the episode a permanent entry in the reader rather than something to re-load by hand each
    session, and the offline resolver is simply better than the in-browser one — it has the
    English dictionary, the loose chat-romanization fold, and name detection, none of which
    can ship to a page at a sane size.

    The browser can still parse this exact format, which is what any machine without the file
    uses; the two paths agree because the client-side parser mirrors the merge rule below.

    Consecutive lines are merged up to a sentence-ish length. The transcript is auto-generated
    caption chunks of two or three words each, and reading 2,595 fragments is nothing like
    reading; but the *first* chunk's timestamp is kept so audio still seeks to the right place.
    """
    path = os.path.join(ROOT, 'sources', 'local', 'podcast-rawtalks-139.txt')
    if not os.path.exists(path):
        return []
    raw = []
    for line in open(path, encoding='utf-8'):
        # tactiq writes the source URL in a header comment; take the id from there rather than
        # hard-coding it, so the next transcript needs no code change
        if line.startswith('#') and 'youtube.com' in line:
            m2 = re.search(r'(?:watch/|watch\?v=|youtu\.be/)([\w-]{11})', line)
            if m2:
                SOURCES['podcast']['youtube'] = m2.group(1)
        m = TS.match(line.rstrip('\n'))
        if not m:
            continue
        h, mi, sec, ms, txt = m.groups()
        t = int(h) * 3600 + int(mi) * 60 + int(sec) + int(ms) / 1000
        if txt.strip():
            raw.append((t, txt.strip()))

    merged, buf, t0 = [], [], None
    for t, txt in raw:
        if t0 is None:
            t0 = t
        buf.append(txt)
        if sum(len(x) for x in buf) >= 90:
            merged.append((t0, ' '.join(buf)))
            buf, t0 = [], None
    if buf:
        merged.append((t0, ' '.join(buf)))

    # Sections of roughly five minutes, so the picker is navigable.
    out, cur, start = [], [], merged[0][0] if merged else 0
    for t, txt in merged:
        if t - start > 300 and cur:
            out.append({'title': stamp(start), 'lines': cur})
            cur, start = [], t
        cur.append((txt, '', t))
    if cur:
        out.append({'title': stamp(start), 'lines': cur})
    return out


def stamp(sec):
    return f'{int(sec // 60):d}:{int(sec % 60):02d}'


def src_textbook():
    """Public proxy: sentences already in the repo, so the live site has something to read."""
    with open(SENTS, encoding='utf-8', newline='') as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t')
                if str(r['unlock_day']).isdigit() and r['telugu'].strip()]
    rows.sort(key=lambda r: int(r['unlock_order']))
    out, size = [], 60
    for i in range(0, min(len(rows), 600), size):
        chunk = rows[i:i + size]
        out.append({'title': f'Sentences {i + 1}–{i + len(chunk)}',
                    'lines': [(r['roman'], r['english']) for r in chunk]})
    return out


SOURCES = {
    'podcast': {'fn': src_podcast, 'private': True, 'prefix': 'local-',
                'audio': 'audio/podcast-rawtalks-139.mp3',
                'title': 'Raw Talks #139',
                'blurb': 'Naga Vamsi on Raw Talks with VK — 1h16m of unscripted Telugu, with a '
                         'lot of English written in Telugu script. Real speech, and hard.'},
    'conversations': {'fn': src_conversations, 'private': True,
                      'title': 'Family conversations',
                      'blurb': 'Recorded at home. Code-switched, Hyderabad register, and the '
                               'closest thing here to the language you actually need.'},
    'textbook':      {'fn': src_textbook, 'private': False,
                      'title': 'Textbook sentences',
                      'blurb': 'Corpus sentences in unlock order — a stand-in until real '
                               'content is ingested.'},
}


# ---------------------------------------------------------------- tokenise

# The Telugu block goes first and is matched as a run, because its vowel signs and virama are
# combining marks (category Mn) which \w does not match — a plain \w+ shatters చేస్తాను into
# nine graphemes. The second branch is Unicode-letter, not [A-Za-z]: an ASCII-only class split
# āyana into "ā" + "yana" and then resolved the fragment "yana" against an English dictionary.
# Contractions stay whole. Splitting "I'll" gave a token "ll", which is in no dictionary, so
# every contraction in the transcripts turned into a word to mine.
TOKEN = re.compile(r"[ఀ-౿]+|[^\W\d_]+(?:['’][^\W\d_]+)*|\d+|[^\w\s]+|\s+")
TELUGU = re.compile(r"[ఀ-౿]")


def token_key(piece):
    """Fold to the matching key. Script is romanized first — fold() strips everything outside
    [a-z], so handing it Telugu returns the empty string and the token looks like punctuation."""
    if TELUGU.search(piece):
        return fold(romanize(piece))
    return fold(piece)


def bare(k, piece, lex, lexidx):
    """A lexicon slot for a token the master does not know.

    Every non-punctuation token needs one, even English words and names. The slot is what
    carries the *key*, and without a key a token cannot be marked — the panel would offer
    "ignore" on a name and silently do nothing."""
    if k not in lexidx:
        lexidx[k] = len(lex)
        lex.append({'k': k, 'r': piece.lower(), 'te': '', 'en': '', 'o': 0, 'g': ''})
    return lexidx[k]


def resolve_line(text, LX, lex, lexidx):
    """-> [surface, kind, lexIndex, roman?]

    kind: t=exact ~=approx e=english n=name w=unknown p=punct

    Script tokens carry a fourth element: their romanization, from the same te2rom the whole
    pipeline uses. The reader shows that instead of the script — the learner cannot read Telugu
    letters yet, and a page of them is not reading practice, it is a wall. The script is kept
    on the token so the word panel can show both and the display can be flipped later.
    """
    out = []
    seen_word = False
    for piece in TOKEN.findall(text):
        k = token_key(piece)
        if not k:
            out.append([piece, 'p', -1])
            continue
        # Capitalised, not sentence-initial, and nothing recognises it: almost always a person
        # or place. These are a large share of the unknown tokens in real conversation, and
        # every one of them would otherwise land in the list of words to look up.
        is_name = (seen_word and piece[:1].isupper() and not TELUGU.search(piece)
                   and k not in LX['exact'] and k not in LX['english']
                   and not LX['approx'].get(loose(k)))
        seen_word = True
        rom = romanize(piece) if TELUGU.search(piece) else None
        # The script form without trailing punctuation — what the verb-form and suffix indexes
        # are keyed on, since both were built from clean master entries.
        bare_te = piece.strip('.,?!;:"“”\'') if TELUGU.search(piece) else ''

        if is_name:
            out.append(tok_row(piece, 'n', bare(k, piece, lex, lexidx), rom))
            continue
        hit = LX['exact'].get(k)
        kind = 't'
        parts = None

        # A conjugated cell the Verb Lab already generates. High confidence: the surface came
        # out of the audited engine, and the headword is in the deck.
        vform = ''
        if hit is None and bare_te in LX['verbforms']:
            hit, vform = LX['verbforms'][bare_te]
            kind = 'v'

        # Stem + a bound suffix the master glosses. Telugu is agglutinative; without this,
        # sinimāki misses even though both halves are known.
        if hit is None and bare_te:
            got = decompose(bare_te, LX)
            if got:
                hit, parts = got
                kind = 's'

        if hit is None and k in LX['english']:
            out.append(tok_row(piece, 'e', bare(k, piece, lex, lexidx), rom))
            continue
        if hit is None:
            cands = LX['approx'].get(loose(k))
            if cands:
                hit, kind = cands[0], '~'
        if hit is None:
            out.append(tok_row(piece, 'w', bare(k, piece, lex, lexidx), rom))
            continue
        # Decomposed words key on their own surface, not the stem's guid: marking sinimāki
        # known must not silently mark every other form of sinimā known too.
        gk = ('s:' + k) if parts else (('v:' + k) if kind == 'v' else hit['guid'])
        if gk not in lexidx:
            lexidx[gk] = len(lex)
            e = {'k': k, 'r': hit['roman'], 'te': hit['telugu'], 'en': hit['english'],
                 'o': int(hit['study_order']) if str(hit['study_order']).isdigit() else 0,
                 'g': '' if (parts or kind == 'v') else hit['guid']}
            if kind == 'v':
                # The form you clicked, plus the headword it belongs to — the headword alone
                # would answer a question you did not ask.
                e['r'] = rom or hit['roman']
                e['te'] = bare_te
                e['head'] = [hit['roman'], hit['english'][:60]]
                e['form'] = vform
            if parts:
                e['p'] = parts
                e['r'] = rom or hit['roman']
                e['te'] = bare_te
                e['en'] = ' + '.join(f'{a} ({b})' for a, b in parts)
            lex.append(e)
        out.append(tok_row(piece, kind, lexidx[gk], rom))
    return out


def decompose(te, LX):
    """Split a Telugu surface into a known stem plus a known bound suffix.

    Returns (stem_row, [[roman, gloss], ...]) or None. Only one suffix deep — two-suffix
    stacks exist but each extra layer multiplies the chance of a wrong split, and one layer
    already covers the case endings that do the damage."""
    for suf, srow in LX['suffixes']:
        if len(te) <= len(suf) or not te.endswith(suf):
            continue
        stem = te[:-len(suf)]
        if len(stem) < 2:
            continue
        row = LX['by_te'].get(stem)
        if row is None:
            row = LX['exact'].get(fold(romanize(stem)))
        if row is None:
            continue
        return row, [[row['roman'], row['english'][:60]],
                     ['-' + srow['roman'].lstrip('-'), srow['english'][:60]]]
    return None


def tok_row(surface, kind, li, rom):
    return [surface, kind, li, rom] if rom else [surface, kind, li]


def build(name, LX):
    spec = SOURCES[name]
    parts = spec['fn']()
    if not parts:
        print(f'  {name}: no source material found, skipped')
        return None

    lex, lexidx, sections = [], {}, []
    counts = Counter()
    for part in parts:
        lines = []
        for row in part['lines']:
            te, en = row[0], row[1]
            t0 = row[2] if len(row) > 2 else None
            toks = resolve_line(te, LX, lex, lexidx)
            for t in toks:
                if t[1] != 'p':
                    counts[t[1]] += 1
            ln = {'t': toks, 'en': en}
            if t0 is not None:
                ln['s'] = round(t0, 2)          # seek offset in seconds
            lines.append(ln)
        sections.append({'title': part['title'], 'lines': lines})

    # How often each word occurs in this text. The mining list is only useful sorted by it —
    # a word said forty times is worth a decision, a hapax is not.
    freq = Counter()
    for sec in sections:
        for ln in sec['lines']:
            for t in ln['t']:
                if t[1] != 'p' and t[2] >= 0:
                    freq[t[2]] += 1
    for i, l in enumerate(lex):
        l['n'] = freq.get(i, 0)

    has_script = any(len(t) > 3 for sec in sections for ln in sec['lines'] for t in ln['t'])

    data = {'slug': name, 'title': spec['title'], 'blurb': spec['blurb'],
            'script': has_script, 'youtube': spec.get('youtube', ''),
            'private': spec['private'], 'audio': spec.get('audio', ''),
            'generated': date.today().isoformat(),
            'counts': dict(counts), 'lex': lex, 'sections': sections}

    prefix = spec.get('prefix', 'private-' if spec['private'] else '')
    out = os.path.join(OUTDIR, f'{prefix}{name}.js')
    os.makedirs(OUTDIR, exist_ok=True)
    var = 'READER_' + re.sub(r'[^A-Z0-9]', '', name.upper())
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f'/* Generated by tools/build_reader.py. Do not edit.\n'
                f' * {"PRIVATE — derived from family recordings, never commit." if spec["private"] else "Public."}\n */\n')
        f.write(f'window.READER_TEXTS = window.READER_TEXTS || {{}};\n')
        f.write(f'window.READER_TEXTS["{name}"] = ' +
                json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')

    tot = sum(counts.values())
    print(f'  {os.path.relpath(out, ROOT)}  {os.path.getsize(out)/1024:.0f} KB'
          f'{"   [PRIVATE — gitignored]" if spec["private"] else ""}')
    print(f'    {len(sections)} sections, {tot} words, {len(lex)} distinct')
    if tot:
        for kind, label in (('t', 'matched exactly'), ('v', 'a Verb Lab form'),
                            ('s', 'stem + suffix'), ('~', 'matched approximately'),
                            ('e', 'English'), ('n', 'a name'), ('w', 'unknown — to mine')):
            n = counts.get(kind, 0)
            print(f'      {label:<24}{n:>6}  {n/tot*100:>4.0f}%')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', nargs='?', help='which source to bake')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    if a.list or not (a.source or a.all):
        print('sources:')
        for k, v in SOURCES.items():
            avail = 'available' if v['fn']() else 'no material'
            print(f"  {k:<16}{'PRIVATE  ' if v['private'] else '         '}{avail}")
        return

    exact, approx, by_te = load_lexicon()
    LX = {'exact': exact, 'approx': approx, 'by_te': by_te,
          'english': load_english(),
          'verbforms': load_verbforms(by_te),
          'suffixes': load_suffixes(by_te)}
    print(f"lexicon: {len(exact)} words, {len(LX['verbforms'])} verb forms, "
          f"{len(LX['suffixes'])} bound suffixes, {len(LX['english'])} English words\n")

    names = list(SOURCES) if a.all else [a.source]
    for n in names:
        if n not in SOURCES:
            print(f'unknown source: {n}'); sys.exit(1)
        build(n, LX)


if __name__ == '__main__':
    main()
