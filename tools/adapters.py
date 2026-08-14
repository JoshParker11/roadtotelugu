# -*- coding: utf-8 -*-
"""One parser per raw source. Each returns a list of dicts in the canonical shape:

    {telugu, roman, english, pos, source, raw_rom, notes}

`roman` is left empty when the source has Telugu script — build_master derives it from the
script, which is far more reliable than trusting a source's own romanization. Whatever
romanization the source did supply is kept in `raw_rom` so nothing is silently discarded.
"""
import csv, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'sources', 'raw')


def top1000(path=None):
    """Telugu Translation Hub top-1000. Two columns: Telugu script, English gloss.

    Provenance matters for how this is scored downstream: it is an *English* frequency
    list machine-translated into Telugu, not a Telugu frequency list. That shows up as
    English function words rendered as bound suffixes, inflected verbs glossed as
    dictionary headwords, and English words simply respelled in Telugu script.
    """
    path = path or os.path.join(RAW, 'top1000.csv')
    out = []
    with open(path, encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    for rank, r in enumerate(rows[1:], 1):          # row 0 is the header
        if len(r) < 2:
            continue
        te, en = r[0].strip(), r[1].strip()
        if not te or not en:
            continue
        out.append({'telugu': te, 'roman': '', 'english': en, 'pos': '',
                    'source': 'top1000', 'raw_rom': '', 'rank': rank, 'notes': ''})
    return out


def site_words(path=None):
    """Words extracted from the course website by anki/tools/build_csvs.py. They carry
    register cues and worked examples the raw lists do not, so they win on merge.

    Read from a frozen snapshot in sources/raw/, NOT from anki/telugu_words.csv. That file
    is now generated from the master, so pointing here at it would make the pipeline eat its
    own output and re-merge every row on each run."""
    path = path or os.path.join(RAW, 'site_words.csv')
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8')):
        out.append({'telugu': r['TeluguScript'].strip(),
                    'roman': '',                      # re-derived from script for consistency
                    'english': r['English'].strip(),
                    'pos': r.get('Category', '').strip(),
                    'source': 'site',
                    'raw_rom': r['Romanized'].strip(),
                    'example': r.get('Example', '').strip(),
                    'tier': r.get('Tier', '').strip(),
                    'notes': ''})
    return out


def core_gaps(path=None):
    """A short hand-curated list of words the corpus uses but no source supplied.

    Every entry here was surfaced by tools/sequence.py's shopping list — the tokens that appear
    in the sentence master and block sentences from ever unlocking. Most of that list is
    spelling variants and inflections, which belong in the pipeline rather than here; these are
    the residue that are simply absent. `telugu` was top of it, appearing nineteen times in the
    corpus and nowhere in the word master."""
    path = path or os.path.join(RAW, 'core_gaps.tsv')
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding='utf-8'):
        parts = [p.strip() for p in line.rstrip('\n').split('\t')]
        if len(parts) < 3 or not parts[1]:
            continue
        out.append({'telugu': parts[1], 'roman': '', 'english': parts[2], 'pos': '',
                    'source': 'core-gaps', 'raw_rom': parts[0], 'notes': ''})
    return out


def lessons(path=None):
    """Vocabulary from the lesson pages in LEARNING_GUIDE/lessons/.

    Every lesson page already ends in an "Anki word list" table whose columns are exactly the
    five note fields, because it was written to be copied by hand. Parsing it instead closes
    the loop: a word taught on a lesson page reaches the deck without anyone retyping it.

    Before this existed the lesson pages were a dead end — వాయించు was taught in Lesson 7 and
    never appeared in the master. These entries win merges: they are hand-written with a
    register cue and a worked example, which no bulk source supplies.

    Rows are matched structurally on the f-en / f-rom / f-tel / f-ex cell classes, so the
    prose around the table can change freely without breaking the parse.
    """
    import glob, html
    base = path or os.path.join(HERE, '..', 'LEARNING_GUIDE', 'lessons')
    row_re = re.compile(
        r'<td class="f-en">(?P<en>.*?)</td>\s*'
        r'<td class="f-rom">(?P<rom>.*?)</td>\s*'
        r'<td class="f-tel">(?P<tel>.*?)</td>.*?'
        r'(?:<td class="f-ex">(?P<ex>.*?)</td>)?\s*</tr>', re.S)
    strip_tags = re.compile(r'<[^>]+>')

    def clean(s):
        return html.unescape(strip_tags.sub('', s or '')).strip()

    out = []
    for page in sorted(glob.glob(os.path.join(base, 'lesson-*.html'))):
        num = re.search(r'lesson-(\d+)', os.path.basename(page)).group(1)
        text = open(page, encoding='utf-8').read()
        for i, m in enumerate(row_re.finditer(text)):
            en, rom, te = clean(m.group('en')), clean(m.group('rom')), clean(m.group('tel'))
            if not en or not te:
                continue
            # "-aṇḍi", "-ండి": taught as morphemes, real, but not free-standing words.
            bound = te.startswith('-') or rom.startswith('-')
            out.append({'telugu': te.strip('-'), 'roman': '', 'english': en, 'pos': '',
                        'source': 'lesson', 'raw_rom': rom.strip('-'),
                        'example': clean(m.group('ex')),
                        'lesson': num,
                        'extra_flags': 'bound-suffix' if bound else '',
                        'notes': ''})
    return out


def spoken_telugu(path=None):
    """Spoken Telugu book vocabulary. Tab-separated, and the English gloss is split across
    however many tab stops the original PDF happened to use:
        3\tivvu\tTo\tGive
    so everything after the romanization is rejoined. Romanization only, no script."""
    path = path or os.path.join(RAW, 'spoken_telugu_vocab.tsv')
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding='utf-8'):
        parts = [p.strip() for p in line.rstrip('\n').split('\t')]
        parts = [p for p in parts if p]
        if len(parts) < 3:
            continue
        if parts[0].lower().startswith('telugu'):     # header
            continue
        if not re.fullmatch(r'\d+', parts[0]):        # numbered rows only
            continue
        rom, en = parts[1], ' '.join(parts[2:])
        en = re.sub(r'\s+,', ',', en)                 # "To Say , Tell" -> "To Say, Tell"
        out.append({'telugu': '', 'roman': '', 'english': en.lower(),
                    'pos': '', 'source': 'spoken-telugu', 'raw_rom': rom, 'notes': ''})
    return out


def _book(kind, path=None):
    path = path or os.path.join(RAW, 'book1000.tsv')
    if not os.path.exists(path):
        return []
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'):
        if r['kind'] != kind:
            continue
        out.append({'telugu': r['telugu'].strip(), 'roman': '',
                    'english': r['english'].strip(), 'pos': '',
                    'source': 'book1000', 'raw_rom': r['raw_rom'].strip(),
                    'rank': int(r['num']), 'book_flags': r['flags'],
                    'notes': ''})
    return out


def book_words(path=None):
    """225-word collection from the Gokila Agurchand book (see tools/parse_book.py)."""
    return _book('word', path)


def book_sentences(path=None):
    """775-sentence collection from the same book."""
    return _book('sentence', path)


def site_sentences(path=None):
    # frozen snapshot — see the note in site_words()
    path = path or os.path.join(RAW, 'site_sentences.csv')
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8')):
        out.append({'telugu': r['TeluguScript'].strip(), 'roman': '',
                    'english': r['EnglishPrompt'].strip(), 'pos': '',
                    'source': 'site', 'raw_rom': r['Romanization'].strip(),
                    'notes': r.get('Notes', '').strip(),
                    'register': r.get('RegisterCue', '').strip()})
    return out


def _anki(kind, path=None):
    """Notes from the existing Anki collection (see tools/export_anki.py). Three
    generations of note type, already normalised to canonical roles by the exporter."""
    path = path or os.path.join(HERE, '..', 'sources', 'private', 'anki_notes.tsv')
    if not os.path.exists(path):
        return []
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'):
        if r['kind'] != kind or not r['telugu'].strip():
            continue
        out.append({'telugu': r['telugu'].strip(), 'roman': '',
                    'english': r['english'].strip(), 'pos': '',
                    'source': 'anki', 'raw_rom': r['raw_rom'].strip(),
                    'pronunciation': r['pronunciation'].strip(),
                    'island': r['island'].strip(),
                    'rank': int(r['rank']) if r['rank'].strip().isdigit() else '',
                    'example': r['example'].strip(),
                    'notes': r['notes'].strip()})
    return out


def anki_words(path=None):
    return _anki('word', path)


def anki_sentences(path=None):
    return _anki('sentence', path)


ALL = {'top1000': top1000, 'site': site_words, 'spoken-telugu': spoken_telugu,
       'book1000': book_words, 'anki': anki_words, 'lesson': lessons, 'core-gaps': core_gaps}
ALL_SENT = {'site': site_sentences, 'book1000': book_sentences, 'anki': anki_sentences}
