# -*- coding: utf-8 -*-
"""Parse "1000 Telugu Words & Sentences" (Gokila Agurchand) into structured records.

    python3 tools/parse_book.py <pdf> [-o sources/raw/book1000.tsv]

The PDF's text layer cannot be read in document order — entries come out interleaved and
some fields land before their own item number. Extraction is therefore positional: tokens
are banded by y coordinate and ordered by x, which reconstructs the visual layout exactly.

Each entry occupies three bands:

    72 ) Ghee          <- item number at x~72, English at x>=110
         Neiyyi        <- romanization
         ನಯ್ಯ           <- Telugu script (Kannada here — a genuine typo in the book)

Everything questionable is flagged rather than dropped. The book has real defects: a few
entries are typeset in Kannada, some are missing a field, and in places the romanization
and the script disagree.
"""
import argparse, csv, re, sys, unicodedata

TELUGU = (0x0C00, 0x0C7F)
KANNADA = (0x0C80, 0x0CFF)
DEVANAGARI = (0x0900, 0x097F)

JUNK = re.compile(r'^(KILA|AGURCHAND|KILAAGURCHAND|Visit|our|channel|YouTube|https?://|Page|by|Gokila|\|)', re.I)
# collection headings sit inside the item flow and otherwise bleed into the previous entry
HEADING = re.compile(r'\b(Words|Sentences)\s*Collection\b.*$', re.I)
NUMTOK = re.compile(r'^(\d{1,4})\)?$')
# a few entries are typeset with no spaces at all: 114)MealsBhojanamభోజనం115)Cloth...
RUNON = re.compile(r'(\d{1,3})\)\s*([A-Za-z()\s]+?)([\u0C00-\u0CFF]+)(?=\d{1,3}\)|$)')


def in_range(ch, rng):
    return rng[0] <= ord(ch) <= rng[1]


def script_of(s):
    t = sum(1 for c in s if in_range(c, TELUGU))
    k = sum(1 for c in s if in_range(c, KANNADA))
    dv = sum(1 for c in s if in_range(c, DEVANAGARI))
    if k > t and k > 0: return 'kannada'
    if dv > t and dv > 0: return 'devanagari'
    if t: return 'telugu'
    return 'latin'


def page_bands(page, ytol=7.0):
    """Tokens -> visual lines. Band by y, order by x; that reverses the interleaving."""
    words = [w for w in page.get_text("words")
             if 55 < w[1] < 735 and not JUNK.match(w[4])]
    words.sort(key=lambda w: w[1])
    bands, cur, cury = [], [], None
    for w in words:
        if cury is None or abs(w[1] - cury) <= ytol:
            cur.append(w); cury = w[1] if cury is None else cury
        else:
            bands.append(cur); cur = [w]; cury = w[1]
    if cur: bands.append(cur)
    out = []
    for b in bands:
        b.sort(key=lambda w: w[0])
        out.append({'y': min(w[1] for w in b),
                    'x0': min(w[0] for w in b),
                    'toks': b,
                    'text': ' '.join(w[4] for w in b)})
    return out


def parse(pdf_path):
    import pymupdf
    doc = pymupdf.open(pdf_path)
    bands = []
    last = len(doc) - 1
    while last > 0 and 'Sentences are used' in (doc[last].get_text() or ''):
        last -= 1                      # trailing pages advertise the author's other books
    for pno in range(last + 1):
        for b in page_bands(doc[pno]):
            b['page'] = pno + 1
            bands.append(b)

    # split run-together bands into their own synthetic bands before locating item starts
    expanded = []
    for b in bands:
        m = list(RUNON.finditer(b['text'].replace(' ', '')))
        if len(m) >= 2:
            for mm in m:
                expanded.append({'y': b['y'], 'x0': 72.0, 'page': b['page'], 'runon': True,
                                 'num': int(mm.group(1)), 'eng': mm.group(2).strip(),
                                 'scr': mm.group(3).strip(), 'toks': [], 'text': mm.group(0)})
        else:
            expanded.append(b)
    bands = expanded

    # an item starts at a band whose leftmost token is a bare number at the left margin
    starts = []
    for i, b in enumerate(bands):
        if b.get('runon'):
            starts.append((i, b['num'])); continue
        if not b['toks']:
            continue
        first = b['toks'][0]
        if first[0] < 100 and NUMTOK.match(first[4]):
            starts.append((i, int(NUMTOK.match(first[4]).group(1))))

    items = []
    for si, (bi, num) in enumerate(starts):
        end = starts[si + 1][0] if si + 1 < len(starts) else len(bands)
        block = bands[bi:end]
        if block[0].get('runon'):
            b0 = block[0]
            # the run-on regex cannot separate English from romanization; keep them together
            items.append({'num': num, 'page': b0['page'], 'english': b0['eng'],
                          'raw_rom': '', 'telugu': b0['scr'],
                          'scripts': script_of(b0['scr'])})
            continue
        # the number's own band may also carry the English gloss
        head = [w[4] for w in block[0]['toks'] if w[0] >= 100 and not NUMTOK.match(w[4]) and w[4] != ')']
        rest = block[1:]
        eng_parts, rom_parts, scr_parts, scripts = list(head), [], [], set()
        for b in rest:
            txt = ' '.join(w[4] for w in b['toks'] if w[4] != ')')
            if not txt.strip():
                continue
            sc = script_of(txt)
            if sc == 'latin':
                (eng_parts if not eng_parts and not rom_parts else rom_parts).append(txt)
            else:
                scripts.add(sc)
                scr_parts.append(txt)
        items.append({
            'num': num, 'page': block[0]['page'],
            'english': HEADING.sub('', ' '.join(eng_parts)).strip(),
            'raw_rom': HEADING.sub('', ' '.join(rom_parts)).strip(),
            'telugu': ' '.join(scr_parts).strip(),
            'scripts': ','.join(sorted(scripts)),
        })
    return items


def sectionise(items):
    """The book restarts numbering per collection: words 1-225, then sentences 1-775.
    Detect the restart rather than trusting the table of contents."""
    out, kind, prev = [], 'word', 0
    switched = False
    for it in items:
        if not switched and it['num'] < prev and it['num'] <= 3 and prev > 100:
            kind, switched = 'sentence', True
        it['kind'] = kind
        prev = it['num']
        out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('-o', '--out', default='sources/raw/book1000.tsv')
    a = ap.parse_args()

    items = sectionise(parse(a.pdf))
    # the book runs 1-225 then 1-775; anything above is a stray number in the back matter
    items = [i for i in items if i['num'] <= (225 if i['kind'] == 'word' else 775)]
    for it in items:
        f = []
        if not it['english']: f.append('no-english')
        if not it['raw_rom']: f.append('no-romanization')
        if not it['telugu']: f.append('no-script')
        if 'kannada' in it['scripts']: f.append('kannada-script')
        if 'devanagari' in it['scripts']: f.append('devanagari-script')
        if it['scripts'].count(',') > 0: f.append('mixed-script')
        it['flags'] = ' '.join(f)

    cols = ['kind', 'num', 'page', 'english', 'raw_rom', 'telugu', 'scripts', 'flags']
    with open(a.out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter='\t', extrasaction='ignore')
        w.writeheader(); w.writerows(items)

    from collections import Counter
    kinds = Counter(i['kind'] for i in items)
    flags = Counter(f for i in items for f in i['flags'].split())
    print(f'parsed {len(items)} items -> {a.out}')
    print('  by kind :', dict(kinds))
    print('  flags   :', dict(flags) or 'none')
    for k in ('word', 'sentence'):
        ns = [i['num'] for i in items if i['kind'] == k]
        if not ns: continue
        missing = sorted(set(range(1, max(ns) + 1)) - set(ns))
        dupes = [n for n, c in Counter(ns).items() if c > 1]
        print(f'  {k}s: 1..{max(ns)}  missing={missing[:12]}{"..." if len(missing)>12 else ""}  dupes={dupes[:8]}')


if __name__ == '__main__':
    main()
