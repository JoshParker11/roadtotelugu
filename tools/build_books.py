# -*- coding: utf-8 -*-
"""Bake the book reader's data: books/source/** -> books/data/books.js

    python3 tools/build_books.py

SOURCE LAYOUT
    books/source/grammar.tsv            shared grammar rules (id, title, form, explain)
    books/source/lexicon.tsv            shared word list, one row per Telugu surface form
    books/source/<book>/book.json       id, title, short, te, order
    books/source/<book>/chapter-NN-chunk-NN.md
                                        translation chunks, in the FORMAT.md shape:
                                        **N.** / EN: / RO: / TE: blocks, then a
                                        "## Mined vocab" list

Chunks of the same chapter are merged in chunk order, so a chapter grows by dropping in the
next chunk file and re-running this. Nothing is hand-edited in books/data/.

The lexicon is keyed by surface form, not lemma, because that is what word status is keyed by
in the reader: a word you clicked as అతనికి is the thing you saw. Every Telugu token in every
chunk should have a row; missing ones are listed at the end so they can be added, and the
reader still shows them (as unglossed) rather than failing.
"""
import csv, glob, json, os, re, sys
from datetime import date

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.join(ROOT, 'books', 'source')
OUT = os.path.join(ROOT, 'books', 'data', 'books.js')

TOKEN = re.compile(r'[ఀ-౿‌‍]+(?:-[ఀ-౿‌‍]+)*')
CHUNK_NAME = re.compile(r'chapter-(\d+)-chunk-(\d+)\.md$')
HEAD = re.compile(r'^#\s*Chapter\s+(\d+)\s*"([^"]+)"')
NUM = re.compile(r'^\*\*(\d+)\.\*\*\s*$')
VOCAB = re.compile(r'^\d+\.\s*(.+?)\s*·\s*(.+?)\s*·\s*(.+?)\s*(?:\(([^)]*)\))?\s*$')


def read_tsv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))


def tokenize(te):
    """Split a Telugu line into [text, isWord] runs, keeping every character."""
    out, i = [], 0
    for m in TOKEN.finditer(te):
        if m.start() > i:
            out.append([te[i:m.start()], 0])
        out.append([m.group(0), 1])
        i = m.end()
    if i < len(te):
        out.append([te[i:], 0])
    return out


def parse_chunk(path):
    title, sents, vocab, status = None, [], [], ''
    cur, in_vocab = None, False
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if (m := HEAD.match(line)):
            title = m.group(2)
            continue
        if line.startswith('Status:'):
            status = 'draft' if 'DRAFT' in line.upper() else 'checked'
            continue
        if line.startswith('## '):
            in_vocab = 'vocab' in line.lower()
            continue
        if in_vocab:
            if (m := VOCAB.match(line)):
                vocab.append({'te': m.group(1), 'rom': m.group(2), 'en': m.group(3),
                              'ref': m.group(4) or ''})
            continue
        if (m := NUM.match(line)):
            cur = {'n': int(m.group(1)), 'en': '', 'ro': '', 'te': ''}
            sents.append(cur)
            continue
        if cur:
            for key in ('EN', 'RO', 'TE'):
                if line.startswith(key + ':'):
                    cur[key.lower()] = line[len(key) + 1:].strip()
    return title, sents, vocab, status


def main():
    grammar = {r['id']: {'t': r['title'], 'f': r['form'], 'x': r['explain']}
               for r in read_tsv(os.path.join(SRC, 'grammar.tsv'))}

    lex = {}
    for r in read_tsv(os.path.join(SRC, 'lexicon.tsv')):
        te = r['te'].strip()
        if not te:
            continue
        if te in lex:
            print(f'duplicate lexicon row: {te}', file=sys.stderr)
        parts = []
        for p in filter(None, (s.strip() for s in (r.get('parts') or '').split(' + '))):
            m, _, g = p.partition('=')
            parts.append([m.strip(), g.strip()])
        rules = (r.get('rules') or '').split()
        for rid in rules:
            if rid not in grammar:
                print(f'{te}: unknown grammar rule {rid!r}', file=sys.stderr)
        entry = {'r': r['rom'], 'en': r['en'], 'k': r['kind'] or 'word'}
        if parts: entry['p'] = parts
        if rules: entry['g'] = rules
        if r.get('note'): entry['x'] = r['note']
        lex[te] = entry

    books, missing, used = [], {}, set()
    for meta_path in sorted(glob.glob(os.path.join(SRC, '*', 'book.json'))):
        bdir = os.path.dirname(meta_path)
        meta = json.load(open(meta_path, encoding='utf-8'))
        chapters = {}
        files = sorted(glob.glob(os.path.join(bdir, 'chapter-*-chunk-*.md')),
                       key=lambda p: tuple(map(int, CHUNK_NAME.search(p).groups())))
        for path in files:
            ch, chunk = map(int, CHUNK_NAME.search(path).groups())
            title, sents, vocab, status = parse_chunk(path)
            c = chapters.setdefault(ch, {'n': ch, 'en': title or f'Chapter {ch}',
                                         'status': status, 'chunks': 0, 's': [], 'vocab': []})
            c['chunks'] += 1
            if status == 'draft':
                c['status'] = 'draft'
            for s in sents:
                toks = tokenize(s['te'])
                for t, w in toks:
                    if w:
                        used.add(t)
                        if t not in lex:
                            missing.setdefault(t, f'{meta["id"]} {ch}.{s["n"]}')
                c['s'].append({'n': s['n'], 'en': s['en'], 'ro': s['ro'], 't': toks})
            c['vocab'].extend(vocab)
        for c in chapters.values():
            c['s'].sort(key=lambda s: s['n'])
        meta['chapters'] = [chapters[k] for k in sorted(chapters)]
        books.append(meta)
    books.sort(key=lambda b: b.get('order', 99))

    data = {'generated': date.today().isoformat(), 'grammar': grammar,
            'lex': {k: v for k, v in lex.items() if k in used}, 'books': books}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('/* Generated by tools/build_books.py from books/source/. Do not edit. */\n')
        f.write('window.BOOKS_DATA = ')
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')

    nsent = sum(len(c['s']) for b in books for c in b['chapters'])
    print(f'{len(books)} book(s), {nsent} sentences, {len(used)} distinct words, '
          f'{len(data["lex"])} glossed -> {os.path.relpath(OUT, ROOT)}')
    unused = sorted(set(lex) - used)
    if unused:
        print(f'{len(unused)} lexicon rows not used by any chunk (kept in source, not baked)')
    if missing:
        print(f'{len(missing)} word(s) with no lexicon row:')
        for t, where in missing.items():
            print(f'  {t}\t{where}')


if __name__ == '__main__':
    main()
