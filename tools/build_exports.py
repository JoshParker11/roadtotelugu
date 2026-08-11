# -*- coding: utf-8 -*-
"""Generate Anki-ready import files from the masters.

    python3 tools/build_exports.py

The masters are the source of truth; these files are disposable output. Regenerate and
re-import whenever a master changes rather than editing cards in Anki.

WHY THE FILES CARRY #guid
Anki matches an incoming row against an existing note by its **first field**. Our first
field is the English gloss, and that is not unique — వెయ్యి, వేయి and వేల are three real
words all glossed "thousand", and ఈ రోజు / ఈరోజు are two spellings of "today". Importing on
first-field matching silently collapses those into one note and loses the variants.

Declaring `#guid column:1` makes Anki match on the master's stable id (W0001, S0001) instead.
That fixes the collapse and makes the import idempotent: fix a row in the master, re-export,
re-import, and the existing note is updated in place instead of duplicated. It is what stops
this from becoming another restart.

Tab-separated, because the glosses contain commas and quotes.

Rows still awaiting a decision are held out of the export rather than shipped into the deck.
`--include-flagged` overrides that.
"""
import argparse, csv, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
DATA = os.path.join(ROOT, 'data')
ANKI = os.path.join(ROOT, 'anki')

BLOCK_W = {'needs-script', 'no-script', 'kannada-script', 'devanagari-script',
           'bound-suffix', 'english-respelled', 'no-english'}
BLOCK_S = {'needs-script', 'no-english'}

# Field order must match the note type exactly — Anki maps columns positionally.
WORD_NOTETYPE = 'Telugu Production'      # English, Romanized, TeluguScript, Audio, Example
SENT_NOTETYPE = 'Telugu Sentence v3'     # English, EnglishAudio, Romanized, Telugu, Audio, Notes
WORD_DECK = 'Telugu::Vocab'
SENT_DECK = 'Telugu::Sentences'


# surface form -> which paradigm it belongs to, from the Verb Lab (1,184 forms)
_VF = {}
_vfp = os.path.join(HERE, 'verbforms.json')
if os.path.exists(_vfp):
    _VF = json.load(open(_vfp, encoding='utf-8'))

NEGWORDS = {'lēdu', 'kādu', 'vaddu', 'lēru', 'lēvu', 'rādu', 'ledu'}
FORM_LABEL = {'past': 'past', 'future': 'future', 'present': 'present',
              'negPast': 'negative', 'negFuture': 'negative',
              'impPol': 'request', 'impFam': 'request',
              'prohibPol': 'negative', 'prohibFam': 'negative',
              'must': 'must', 'can': 'can', 'hort': 'lets', 'cond': 'if'}


def sentence_forms(r):
    """What grammar a sentence exercises, so you can drill one thing at a time.
    Derived from the Verb Lab paradigm index where a word matches, plus two safe
    surface cues: a question mark, and the standalone negative words."""
    out = set()
    if r['english'].rstrip().endswith('?') or r['roman'].rstrip().endswith('?'):
        out.add('question')
    toks_rom = {t.strip('.,?!').lower() for t in r['roman'].split()}
    if toks_rom & NEGWORDS:
        out.add('negative')
    for t in r['telugu'].split():
        hit = _VF.get(t.strip('.,?!'))
        if hit and hit['form'] in FORM_LABEL:
            out.add(FORM_LABEL[hit['form']])
    return sorted(out)


def length_band(r):
    n = len([t for t in r['roman'].split() if t.strip('.,?!')])
    return '1-3' if n <= 3 else '4-6' if n <= 6 else '7plus'


def read(path):
    return list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))


def tags_for_word(r):
    t = [f'src::{s}' for s in r['source'].split(',') if s]
    if r['pos']:
        t.append('cat::' + re.sub(r'[^a-z0-9]+', '-', r['pos'].lower()).strip('-'))
    if r['island']:
        t.append('topic::' + re.sub(r'[^a-z0-9]+', '-', r['island'].lower()).strip('-'))
    for f in r['flags'].split():
        if f in ('multi-gloss', 'phrase', 'inflected', 'verbform'):
            t.append('flag::' + f)
    return ' '.join(dict.fromkeys(t))


def tags_for_sentence(r):
    t = [f'src::{s}' for s in r['source'].split(',') if s]
    if r['register']:
        t.append('reg::' + r['register'])
    t.append(f'known::{int(r["known_pct"]) // 20 * 20}')
    t.append('len::' + length_band(r))
    t += ['form::' + f for f in sentence_forms(r)]
    for f in r['flags'].split():
        t.append('flag::' + f)
    return ' '.join(dict.fromkeys(x for x in t if x))


def write(path, header, cols, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        for line in header:
            f.write(line + '\n')
        w = csv.writer(f, delimiter='\t', lineterminator='\n',
                       quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow([r.get(c, '') for c in cols])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--include-flagged', action='store_true')
    a = ap.parse_args()

    words, sents = read(os.path.join(DATA, 'master_words.tsv')), read(os.path.join(DATA, 'master_sentences.tsv'))

    wout, wheld = [], 0
    for r in words:
        if not a.include_flagged and (BLOCK_W & set(r['flags'].split())):
            wheld += 1; continue
        eng = r['english'] + (f"  [form of {r['lemma']}]" if r['lemma'] else '')
        wout.append({'guid': r['id'], 'English': eng, 'Romanized': r['roman'],
                     'TeluguScript': r['telugu'], 'Audio': '', 'Example': r['example'],
                     'Tags': tags_for_word(r)})

    sout, sheld = [], 0
    for r in sents:
        if not a.include_flagged and (BLOCK_S & set(r['flags'].split())):
            sheld += 1; continue
        prompt = r['english']
        if r['register'] and not re.search(r'formal|informal|respect|polite', prompt, re.I):
            prompt += f" [{r['register']}]"
        sout.append({'guid': r['id'], 'English': prompt, 'EnglishAudio': '',
                     'Romanized': r['roman'], 'Telugu': r['telugu'], 'Audio': '',
                     'Notes': r['notes'], 'Tags': tags_for_sentence(r)})

    for i, r in enumerate(wout):
        r['Tags'] += f' set::{i // 50 + 1:03d}'
    for i, r in enumerate(sout):
        r['Tags'] += f' set::{i // 50 + 1:03d}'

    wcols = ['guid', 'English', 'Romanized', 'TeluguScript', 'Audio', 'Example', 'Tags']
    scols = ['guid', 'English', 'EnglishAudio', 'Romanized', 'Telugu', 'Audio', 'Notes', 'Tags']

    whdr = ['#separator:tab', '#html:false', f'#notetype:{WORD_NOTETYPE}',
            f'#deck:{WORD_DECK}', '#guid column:1', f'#tags column:{len(wcols)}',
            '#columns:' + '\t'.join(wcols)]
    shdr = ['#separator:tab', '#html:false', f'#notetype:{SENT_NOTETYPE}',
            f'#deck:{SENT_DECK}', '#guid column:1', f'#tags column:{len(scols)}',
            '#columns:' + '\t'.join(scols)]

    wpath = os.path.join(ANKI, 'import_words.txt')
    spath = os.path.join(ANKI, 'import_sentences.txt')
    write(wpath, whdr, wcols, wout)
    write(spath, shdr, scols, sout)
    for p, rows in ((wpath, wout), (spath, sout)):
        print(f'  {os.path.relpath(p, ROOT):<30} {len(rows):>5} rows')
    print(f'  held back pending triage: {wheld} words, {sheld} sentences')
    print(f'\n  target note types: {WORD_NOTETYPE!r} -> {WORD_DECK}')
    print(f'                     {SENT_NOTETYPE!r} -> {SENT_DECK}')


if __name__ == '__main__':
    main()
