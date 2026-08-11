# -*- coding: utf-8 -*-
"""Generate the Anki import files from the masters.

    python3 tools/build_exports.py

The masters are the source of truth; these two CSVs are disposable output. Regenerate and
re-import whenever a master changes rather than editing cards in Anki.

Rows still awaiting a decision (no script, Kannada typeset, an English word merely respelled
in Telugu letters, a bound suffix dressed up as a word) are held back from the export rather
than shipped into the deck. `--include-flagged` overrides that.
"""
import argparse, csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
DATA = os.path.join(ROOT, 'data')
ANKI = os.path.join(ROOT, 'anki')

# flags that mean "not ready for a deck"
BLOCK_W = {'needs-script', 'no-script', 'kannada-script', 'devanagari-script',
           'bound-suffix', 'english-respelled', 'no-english'}
BLOCK_S = {'needs-script', 'no-english'}


def read(path):
    return list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))


def tags_for_word(r):
    t = [f"src::{s}" for s in r['source'].split(',') if s]
    if r['pos']:
        t.append('cat::' + re.sub(r'[^a-z0-9]+', '-', r['pos'].lower()).strip('-'))
    if r['lemma']:
        t.append('flag::inflected')
    for f in r['flags'].split():
        if f in ('multi-gloss', 'phrase', 'inflected', 'verbform'):
            t.append('flag::' + f)
    return ' '.join(dict.fromkeys(t))


def tags_for_sentence(r):
    t = [f"src::{s}" for s in r['source'].split(',') if s]
    if r['register']:
        t.append('reg::' + r['register'])
    band = int(r['known_pct']) // 20 * 20
    t.append(f'known::{band}')
    for f in r['flags'].split():
        t.append('flag::' + f)
    return ' '.join(dict.fromkeys(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--include-flagged', action='store_true')
    a = ap.parse_args()

    words = read(os.path.join(DATA, 'master_words.tsv'))
    sents = read(os.path.join(DATA, 'master_sentences.tsv'))

    wout, wheld = [], 0
    for r in words:
        if not a.include_flagged and (BLOCK_W & set(r['flags'].split())):
            wheld += 1; continue
        eng = r['english']
        if r['lemma']:
            eng += f"  [form of {r['lemma']}]"
        wout.append({'English': eng, 'Romanized': r['roman'], 'TeluguScript': r['telugu'],
                     'Audio': '', 'Example': r['example'], 'Tags': tags_for_word(r),
                     'ID': r['id']})

    sout, sheld = [], 0
    for r in sents:
        if not a.include_flagged and (BLOCK_S & set(r['flags'].split())):
            sheld += 1; continue
        prompt = r['english']
        if r['register'] and not re.search(r'formal|informal|respect|polite', prompt, re.I):
            prompt += f" [{r['register']}]"
        sout.append({'EnglishPrompt': prompt, 'EnglishAudio': '', 'TeluguScript': r['telugu'],
                     'Romanization': r['roman'], 'TeluguAudio': '', 'Notes': r['notes'],
                     'Tags': tags_for_sentence(r), 'ID': r['id']})

    wcols = ['English', 'Romanized', 'TeluguScript', 'Audio', 'Example', 'Tags', 'ID']
    scols = ['EnglishPrompt', 'EnglishAudio', 'TeluguScript', 'Romanization', 'TeluguAudio',
             'Notes', 'Tags', 'ID']
    for path, cols, rows in ((os.path.join(ANKI, 'telugu_words.csv'), wcols, wout),
                             (os.path.join(ANKI, 'telugu_sentences.csv'), scols, sout)):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            w.writeheader(); w.writerows(rows)
        print(f'  {os.path.relpath(path, ROOT):<32} {len(rows):>5} rows')
    print(f'  held back pending triage: {wheld} words, {sheld} sentences')


if __name__ == '__main__':
    main()
