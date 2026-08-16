# -*- coding: utf-8 -*-
"""Diff the Python romanizer against its JavaScript port.

    python3 tools/check_te2rom.py

There are two implementations of one rule: tools/te2rom.py runs in the offline pipeline, and
STUDY/assets/te2rom.js runs in the browser for transcripts that cannot be committed and
therefore cannot be baked. Two implementations drift — silently, and in a way that shows up as
a handful of odd-looking words months later rather than as an error.

So this feeds every distinct Telugu token available (the word master, the sentence master, and
any local transcripts) through both and reports any disagreement. Run it after touching either
file. Needs node.
"""
import csv, glob, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from te2rom import romanize

JS = os.path.join(ROOT, 'STUDY', 'assets', 'te2rom.js')
TELUGU = re.compile(r'[ఀ-౿]')


def tokens():
    seen = set()
    for path, col in ((os.path.join(ROOT, 'data', 'master_words.tsv'), 'telugu'),
                      (os.path.join(ROOT, 'data', 'master_sentences.tsv'), 'telugu')):
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                for t in (r[col] or '').split():
                    if TELUGU.search(t):
                        seen.add(t)
    for p in glob.glob(os.path.join(ROOT, 'sources', 'local', '*.txt')):
        for line in open(p, encoding='utf-8'):
            for t in line.split():
                if TELUGU.search(t):
                    seen.add(t)
    return sorted(seen)


def main():
    toks = tokens()
    if not toks:
        print('no Telugu tokens found'); return
    print(f'{len(toks)} distinct Telugu tokens')

    script = f'''
const {{ romanize }} = (() => {{ {open(JS, encoding='utf-8').read()}
  return Te2Rom; }})();
const toks = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
// NOT toks.map(romanize): map passes (element, index, array), so the index lands in
// romanize's `assimilate` parameter and index 0 silently skips assimilation. That produced
// exactly one bogus disagreement and sent me looking at the port instead of the harness.
console.log(JSON.stringify(toks.map(t => romanize(t))));
'''
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, 'run.js')
        tp = os.path.join(d, 'toks.json')
        open(sp, 'w', encoding='utf-8').write(script)
        json.dump(toks, open(tp, 'w', encoding='utf-8'), ensure_ascii=False)
        try:
            res = subprocess.run(['node', sp, tp], capture_output=True, text=True, check=True)
        except FileNotFoundError:
            print('node not installed — cannot compare'); sys.exit(1)
        except subprocess.CalledProcessError as e:
            print('node failed:\n' + e.stderr); sys.exit(1)
    js = json.loads(res.stdout)

    bad = [(t, romanize(t), j) for t, j in zip(toks, js) if romanize(t) != j]
    if not bad:
        print('  identical output on every token')
        return
    print(f'  {len(bad)} disagreements:')
    for t, py, j in bad[:30]:
        print(f'    {t:<22} py={py:<22} js={j}')
    sys.exit(1)


if __name__ == '__main__':
    main()
