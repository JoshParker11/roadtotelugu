# -*- coding: utf-8 -*-
"""QC for the Mini Stories translation. Catches what a reader who cannot read Telugu cannot.

    python3 tools/check_ms.py              # every lesson
    python3 tools/check_ms.py --num 1      # one story
    python3 tools/check_ms.py --warn       # include advisory findings, not just errors

WHAT THIS CAN AND CANNOT DO
It cannot tell you the Telugu is good. It can tell you the Telugu is *consistent with itself and
with the English*, which is a different claim and the only one a script is entitled to make.

The distinction matters because of how this project fails. You cannot yet evaluate the output, so
an inconsistency is invisible to you and propagates silently until a native speaker meets it 300
segments later and has to correct the same thing sixty times. Every check below exists to convert
one of those silent failures into a line of output today.

The design precedent is check_hp.py, but the checks differ because the material does. A novel has
no repeating structure to exploit; a Mini Story is almost nothing but repeating structure — the
story is retold in the first person and then interrogated line by line. That redundancy is the
lever: the same content appears two or three times per lesson, so the translation can be checked
against *itself*, which is far stronger than checking it against the English alone.

THE CHECK THAT JUSTIFIES THE FILE
`story vs retell divergence` (G). Sentence n of the story and sentence n of the retell should
differ ONLY in person — the pronoun and the verb ending. Anything else that differs is a word
that was translated two different ways in the same lesson, ten lines apart. The first real run of
this project produced exactly that (చేసి in the story, చేసుకుని in the retell) and it was found
by a human eye by luck, which does not scale to 2,805 segments.

That check pairs rows by STORY NUMBER, never by file, and the distinction is not academic: story
one is split across lessons 1a/1b/1c, so its story lines and its retell lines live in different
files. A per-file version of this check finds nothing in story one — which is precisely where the
bug it was written for occurred. It was written per-file first, and a fault-injection test caught
it doing nothing. Group by `num`.
"""
import argparse
import csv
import glob
import os
import re
import sys
import unicodedata
from msfiles import work_tsvs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
CATALOG = os.path.join(MS, 'CATALOG.tsv')
NAMES = os.path.join(MS, 'names.tsv')

# `native` is a source, not a stage: the row is the native speaker's own translation rather
# than a draft of ours that someone later verified. Worth keeping distinct from `checked` —
# "who wrote this" and "has anyone checked it" are different questions, and after a native
# batch lands the first one is the more useful filter.
STATUSES = ('todo', 'draft', 'query', 'checked', 'done', 'native')
TELUGU = re.compile(r'[ఀ-౿]')
LATIN = re.compile(r'[A-Za-z]')

# LingQ's source skips "Five:" in lesson 2 and nowhere else. Verified against the raw payload:
# 47 lines in, 47 rows out. Without this the checker would report it every run, forever, and a
# checker that cries wolf once a run is a checker nobody reads.
ORDINAL_GAPS_OK = {'02': {'five'}}

ORD_EN = ('one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
          'fifteen').split()
# Acceptable Telugu renderings per English numeral. Several are needed: "one" is ఒకటి when it is
# counting and ఒక/ఒకే when it is an article or "a single", and flagging the latter as a missing
# numeral would bury the real findings.
NUM_TE = {
    'one': ('ఒకటి', 'ఒక', 'ఒకే'), 'two': ('రెండు', 'రెండ'), 'three': ('మూడు', 'మూడ'),
    'four': ('నాలుగు', 'నాలుగ'), 'five': ('ఐదు', 'అయిదు'), 'six': ('ఆరు',),
    'seven': ('ఏడు',), 'eight': ('ఎనిమిది',), 'nine': ('తొమ్మిది',), 'ten': ('పది',),
    'eleven': ('పదకొండు',), 'twelve': ('పన్నెండు',),
}
# Person-marking tokens that are SUPPOSED to differ between the story and its retell. Anything
# else that differs is a finding, not a person shift.
PERSON_PAIRS = [
    ('అతను', 'నేను'), ('ఆమె', 'నేను'), ('తను', 'నేను'),
    ('అతని', 'నా'), ('ఆమె', 'నా'), ('తన', 'నా'), ('అతనికి', 'నాకు'), ('ఆమెకు', 'నాకు'),
]
PERSON_OK = {frozenset(p) for p in PERSON_PAIRS}
FIRST_PERSON = {'నేను', 'నా', 'నాకు', 'నన్ను', 'నాతో', 'నాది'}

# Every pronoun this material uses, in every case form it appears in. A token that is a
# pronoun on one side and a pronoun-or-name on the other is a person shift by definition,
# whatever the surface forms look like. That general rule is what the first version lacked:
# it special-cased a handful of pairs and reported the rest as findings.
PRONOUNS = set('నేను నా నాకు నన్ను నాతో నాది నాలో మేము మా మాకు మమ్మల్ని మాతో మనం మన అతను అతని అతనికి అతనిని అతనితో ఆమె ఆమెకు ఆమెను ఆమెతో ఆమెది తను తన తనకు తనని తనతో వాడు వాళ్ళు వాళ్లు వారు వాళ్ళకు వాళ్లకు వాళ్ళను వాళ్లను వాళ్ళతో వాళ్లతో అది ఇది '
                'వాళ్ళ వాళ్ల వారి వారితో వారికి వారిని మావాళ్ళు వాళ్ళిద్దరూ'.split())
# The second line is what the native translations added. The list was assembled against model
# output, which used a narrower set of forms — genitive వాళ్ళ and instrumental వారితో never
# appeared in it, so both read as findings the first time a human wrote them.

# Case suffixes that attach to a transliterated name. A name in the story becomes a pronoun
# in the retell, and usually carries a case marker on one or both sides (డస్టిన్‌కు / నాకు),
# so comparing bare names was never going to be enough. ZWNJ appears inside names where a
# suffix is joined, and has to be stripped before any comparison.
CASE_SUFFIXES = ('కు', 'కి', 'ను', 'ని', 'తో', 'లో', 'నుంచి', 'నుండి', 'కూ', 'పై', 'మీద')
ZWNJ = '\u200c\u200d'

# Verb and predicate endings that legitimately swap when a third-person line becomes first-person.
# Stated as (third, first) suffix pairs rather than inferred, because inference is what the first
# version tried: it chopped a syllable off each token and compared the stems, which cannot tell
# వంటవాడు/వంటవాడిని (a real person shift, two syllables of difference) from చేసి/చేసుకుని (a
# genuine inconsistency, also two syllables). The difference is not length — it is whether the
# leftover is a person morpheme, and that is a closed list worth writing out.
ENDING_PAIRS = {frozenset(p) for p in [
    ('డు', 'ను'),        # లేస్తాడు / లేస్తాను
    ('ాడు', 'ాను'),      # తాగుతాడు / తాగుతాను
    ('ు', 'ిని'),        # వంటవాడు / వంటవాడిని  (equational predicate)
    ('ుడు', 'ుడిని'),
    ('ాడు', 'ాడిని'),
    ('ది', 'ను'), ('ుంది', 'ాను'),          # ఉంది / ఉన్నాను     3sg fem-neut -> 1sg
    ('ుంది', 'ున్నాను'), ('ి', 'ున్నాను'),
    ('ారు', 'ాము'),                          # చేసుకుంటారు / చేసుకుంటాము  3pl -> 1pl
    ('ారు', 'ాం'), ('తారు', 'తాము'), ('స్తారు', 'స్తాము'),
    ('ుంది', 'ుంటాను'),
    # These are stated as the MINIMAL distinguishing tails, because the pair is matched
    # against what is left after the longest common prefix — which greedily consumes the
    # shared ా, so చేసుకుంటారు/చేసుకుంటాము leaves రు/ము and never ారు/ాము. Writing the
    # fuller forms above and stopping there is why three 3pl->1pl verbs were reported.
    ('రు', 'ము'), ('రు', 'ం'),
    ('ంది', 'న్నాను'), ('ంది', 'ంటాను'), ('ాడు', 'ాను'), ('డు', 'ను'),
    # Past tense, which the model drafts never used and a human translator does throughout:
    # వెళ్ళింది / వెళ్ళాను, ప్రయత్నించింది / ప్రయత్నించాను, పోయింది / పోయాను.
    ('ింది', 'ాను'), ('ది', 'ాను'),
    ('ారు', 'ుతాము'), ('రు', 'ుతాము'),      # నిద్రపుచ్చారు / నిద్రపుచ్చుతాము
    ('ి', 'ిని'),                            # విద్యార్థి / విద్యార్థిని
]}


def rows_for(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def names_map():
    if not os.path.exists(NAMES):
        return {}
    return {r['name']: r['te'] for r in rows_for(NAMES) if r.get('te')}


def strip_final(tok):
    """A token minus its last orthographic syllable, roughly.

    Telugu person endings live in the final syllable (-తాడు vs -తాను). Chopping combining marks
    and one base consonant approximates 'the stem', which is all this needs: we are asking
    whether two tokens plausibly share a stem, not doing real morphology.
    """
    s = tok
    while s and unicodedata.combining(s[-1]):
        s = s[:-1]
    return s[:-1] if s else s


def _strip_case(tok, names_te):
    """If tok is a known name plus a case suffix, return the bare name."""
    t = tok.strip(ZWNJ)
    if t in names_te:
        return t
    for suf in CASE_SUFFIXES:
        if t.endswith(suf):
            stem = t[:-len(suf)].strip(ZWNJ)
            if stem in names_te:
                return stem
    return None


def is_person_token(tok, names_te):
    """A pronoun in any case, or a known name in any case."""
    t = tok.strip(ZWNJ)
    return t in PRONOUNS or _strip_case(t, names_te) is not None


def person_shift_ok(a, b, names_te=()):
    """True if a/b differ only as a person shift would make them differ.

    Three legitimate ways a token can change between the story and its retell:
      1. a pronoun swap            అతను -> నేను
      2. the subject's NAME becomes a first-person pronoun   మైక్ -> నేను
      3. the predicate keeps its stem and swaps a person ending   వంటవాడు -> వంటవాడిని

    Everything else is the same word rendered two different ways, which is the finding.
    """
    if a == b or frozenset((a, b)) in PERSON_OK:
        return True
    # (2) BOTH sides are person-marking — a pronoun or a name, in any case form. This is
    # the general rule: a name-or-pronoun opposite a name-or-pronoun is a person shift
    # whatever the surface forms. It subsumes కారెన్->నేను, డస్టిన్‌కు->నాకు, వాళ్ళు->మేము,
    # జాన్->మా and ఏమీకి->ఆమెకు, every one of which the first version called a finding.
    if is_person_token(a, names_te) and is_person_token(b, names_te):
        return True
    # (3) shared stem + a recognised person-ending swap.
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    if n >= 1 and frozenset((a[n:], b[n:])) in ENDING_PAIRS:
        return True
    return False


def check_lesson(sid, rows, names, warn):
    """Yield (level, sid, row_or_None, message)."""
    out = []
    def err(r, m): out.append(('ERROR', sid, r, m))
    def adv(r, m):
        if warn: out.append(('WARN', sid, r, m))

    seen_guid = {}
    for r in rows:
        te, en, st = r['te'].strip(), r['en'].strip(), r['status'].strip()

        # --- A. schema and status integrity -------------------------------------------------
        if st not in STATUSES:
            err(r, f'status {st!r} is not one of {"/".join(STATUSES)}')
        if not en:
            err(r, 'empty en')
        if te and st == 'todo':
            err(r, 'has a translation but status is still todo')
        if not te and st != 'todo':
            err(r, f'status is {st} but te is empty')
        if st == 'query' and not r['notes'].strip():
            err(r, 'status=query with no note — the open question is lost')
        if r['guid'] in seen_guid:
            err(r, f'duplicate guid within the lesson (also seq {seen_guid[r["guid"]]})')
        seen_guid[r['guid']] = r['seq']

        if not te:
            continue

        # --- B. untranslated source left behind ---------------------------------------------
        if not TELUGU.search(te):
            err(r, 'te contains no Telugu script at all')
        stray = [w for w in LATIN.findall(te)]
        if stray:
            # Names are transliterated in this project (DECISIONS.md #1), so ANY Latin run in
            # the Telugu is either an English word left behind or a name that escaped names.tsv.
            word = re.findall(r'[A-Za-z]+', te)
            err(r, f'Latin script in te: {" ".join(word)!r} — English left untranslated?')

        # --- C. question-mark parity --------------------------------------------------------
        if en.endswith('?') and not te.endswith('?'):
            err(r, 'English is a question, Telugu is not — interrogative flattened')
        if not en.endswith('?') and te.endswith('?'):
            err(r, 'Telugu is a question, English is not')

        # --- D. names present ---------------------------------------------------------------
        for nm, nte in names.items():
            if re.search(rf'\b{re.escape(nm)}\b', en) and nte not in te:
                err(r, f'name {nm} ({nte}) is in the English but missing from the Telugu')

        # --- J. numbers and times preserved -------------------------------------------------
        for num in ORD_EN:
            if re.search(rf'\b{num}\b', en, re.I):
                forms = NUM_TE.get(num, ())
                if forms and not any(f in te for f in forms):
                    adv(r, f'English has "{num}" but te has none of {"/".join(forms)}')

    # --- E. shared boilerplate must agree (handled across lessons by the caller) -------------
    # --- H. ordinal prompts contiguous ------------------------------------------------------
    qrows = [r for r in rows if r['part'] == 'questions']
    got = []
    for r in qrows:
        m = re.match(r'\s*(' + '|'.join(ORD_EN) + r')\s*:', r['en'], re.I)
        if m:
            got.append(m.group(1).lower())
    if got:
        idx = [ORD_EN.index(g) for g in got]
        missing = [ORD_EN[i] for i in range(idx[0], idx[-1] + 1) if i not in idx]
        unexpected = set(missing) - ORDINAL_GAPS_OK.get(sid, set())
        if unexpected:
            out.append(('ERROR', sid, None,
                        f'question ordinals skip {", ".join(sorted(unexpected))} — lines dropped?'))
        if sorted(idx) != idx:
            out.append(('ERROR', sid, None, 'question ordinals are out of order'))

    return out


# Words that differ between a story line and its retell BY DESIGN, and so must not count either
# for or against an alignment.
_PRON = set('i he she it they we you me him her them my his her its their our your the a an'.split())


def _content(en):
    """Content words of an English line, crudely stemmed so make/makes align."""
    ws = re.findall(r"[a-z']+", en.lower())
    return {w[:-1] if len(w) > 3 and w.endswith('s') else w for w in ws if w not in _PRON}


def align_story_retell(story, retell):
    """Pair story lines to retell lines by ENGLISH overlap, monotonically.

    Positional pairing looks obvious and is wrong: the retell does not always have one line per
    story line (story one has ten and nine), and a single missing line at the top would shift
    every later pair by one and turn the whole check into noise. The English is present on both
    sides and is the reliable key, so use it and report what could not be paired.
    """
    pairs, unpaired, j = [], [], 0
    for a in story:
        ca = _content(a['en'])
        best, score = None, 0.0
        for k in range(j, len(retell)):
            cb = _content(retell[k]['en'])
            if not (ca or cb):
                continue
            sc = len(ca & cb) / max(1, len(ca | cb))
            if sc > score:
                score, best = sc, k
        if best is not None and score >= 0.34:
            pairs.append((a, retell[best]))
            j = best + 1
        else:
            unpaired.append(a)
    return pairs, unpaired


def check_story(num, rows, warn, names_te=()):
    """Checks that span a whole story, whatever files its parts happen to live in.

    Story one is split across lessons 1a/1b/1c, so its story and retell lines are in DIFFERENT
    files. Pairing by file would skip it entirely. Pair by story number.
    """
    out = []
    story = [r for r in rows if r['part'] == 'story']
    retell = [r for r in rows if r['part'] == 'retell']
    sid = f'story {num}'
    if not (story and retell):
        return out
    pairs, unpaired = align_story_retell(story, retell)
    if unpaired and warn:
        out.append(('WARN', sid, None,
                    f'{len(unpaired)} story line(s) have no retell counterpart '
                    f'(seq {", ".join(u["seq"] for u in unpaired)}) — normal where LingQ drops '
                    'one, but check nothing was lost in translation'))
    for a, b in pairs:
        if not (a['te'].strip() and b['te'].strip()):
            continue
        ta, tb = a['te'].split(), b['te'].split()
        if len(ta) != len(tb):
            if warn:
                out.append(('WARN', sid, b,
                            f'story/retell {a["seq"]} differ in word count '
                            f'({len(ta)} vs {len(tb)}) — restructured, or a word dropped'))
            continue
        for x, y in zip(ta, tb):
            if x == y or person_shift_ok(x.strip('.,!?"\''), y.strip('.,!?"\''), names_te):
                continue
            out.append(('ERROR', sid, b,
                        f'story/retell line {a["seq"]}: {x!r} vs {y!r} — same word translated '
                        'two ways in one story, and the difference is not a person shift'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', type=int, help='only this story number')
    ap.add_argument('--warn', action='store_true', help='include advisory findings')
    args = ap.parse_args()

    cat = {r['id']: r for r in rows_for(CATALOG)}
    names = names_map()
    findings, meta_te, checked = [], {}, 0
    by_story = {}

    for path in work_tsvs(WORK):
        sid = os.path.basename(path)[:-4]
        if args.num and int(cat[sid]['num']) != args.num:
            continue
        rows = rows_for(path)
        checked += 1
        by_story.setdefault(cat[sid]['num'], []).extend(rows)
        findings += check_lesson(sid, rows, names, args.warn)
        # E. one guid, one translation — the retell boilerplate spans all 60 lessons.
        for r in rows:
            if r['part'] == 'meta' and r['te'].strip():
                prev = meta_te.get(r['guid'])
                if prev and prev[1] != r['te'].strip():
                    findings.append(('ERROR', sid, r,
                                     f'shared boilerplate translated differently here than in '
                                     f'{prev[0]} — one guid must have one translation'))
                meta_te.setdefault(r['guid'], (sid, r['te'].strip()))

    for num, rows in sorted(by_story.items(), key=lambda kv: int(kv[0])):
        findings += check_story(num, rows, args.warn, set(names.values()))

    # names.tsv coverage. Driven by names.tsv itself rather than re-deriving candidates with
    # a regex here: ms_names.py already does that filtering properly, and the second, cruder
    # copy of the logic that used to live here reported Do/First/Her/In/Then/We as names.
    if args.warn and os.path.exists(NAMES):
        allnames = {r['name']: r['te'] for r in rows_for(NAMES)}
        used = set()
        for path in work_tsvs(WORK):
            for r in rows_for(path):
                if r['te'].strip() and r['part'] != 'meta':
                    for w in re.findall(r'\b[A-Z][a-z]+\b', r['en']):
                        if w in allnames and not allnames[w]:
                            used.add(w)
        if used:
            findings.append(('WARN', '-', None,
                             'names used in translated rows but not yet transliterated in '
                             'names.tsv: ' + ' '.join(sorted(used))))

    errs = [f for f in findings if f[0] == 'ERROR']
    for level, sid, r, msg in findings:
        loc = f'{sid} {r["part"]}/{r["seq"]}' if r else sid
        print(f'{level:<5} {loc:<18} {msg}')
        if r and level == 'ERROR':
            print(f'      en: {r["en"]}')
            print(f'      te: {r["te"]}')

    print(f'\n{checked} lesson(s) checked · {len(errs)} error(s) · '
          f'{len(findings) - len(errs)} advisory')
    if not args.warn:
        print('(advisory findings hidden — re-run with --warn)')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
