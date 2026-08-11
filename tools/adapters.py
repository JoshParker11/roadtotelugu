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
    """The words already extracted from the course website. These carry register cues and
    example sentences the raw lists do not, so they win on merge."""
    path = path or os.path.join(HERE, '..', 'anki', 'telugu_words.csv')
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


ALL = {'top1000': top1000, 'site': site_words, 'spoken-telugu': spoken_telugu}
