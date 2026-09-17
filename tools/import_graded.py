# -*- coding: utf-8 -*-
"""Import graded-reader bundles into a reader dataset.

    python3 tools/import_graded.py --src ~/Downloads/telugu-graded-readers
    python3 tools/import_graded.py --src ... --chapters 1,2 --out reader/data/poa.js

WHAT THIS READS
The graded-reader pipeline emits a normalised content graph per scene: sentences with exact
tokens and protected spans, and lexemes -> senses -> forms -> analyses -> occurrences, plus
constructions and a learning block. Its own compatibility note (docs/ROAD_TO_TELUGU.md in that
project) reverse-engineered this reader's format and proposed the mapping; this is that mapping
implemented, with two deliberate departures noted below.

WHY THE OCCURRENCE IS THE NEW UNIT
This reader has always kept one card per surface form, with `sn` holding a list of senses. That
was adequate while a gloss was a property of a spelling. It is not adequate here: the pipeline
stores the contextual gloss, the grammatical role and the aligned English phrase on the
OCCURRENCE — this word, in this sentence — and a form can occur thirty times in three chapters
with a different job each time. Flattening that to one card per spelling would throw away most
of what was authored, and would show a note from some other sentence at the top of the card,
which is exactly the defect their review identified in the existing import.

So a token tuple gains a fourth element: the index of its occurrence. Old datasets have
three-element tuples and are unaffected — the reader treats a missing fourth element as "no
occurrence data, use the form's default", which is precisely the old behaviour.

TWO DEPARTURES FROM THE PROPOSED MAPPING
1. Protected Latin is LEXICAL here. The proposal offered a "current-reader-safe projection"
   that keeps names and incantations as inert text, because the older importer decided
   lexicality by testing for Telugu characters. A token carrying formIds is a word whatever its
   script, so Harry and Hogwarts get real cards. Their ids come from ids.guid('W', '', surface),
   the romanisation fallback that already exists for script-less entries, so nothing pretends
   they are Telugu.
2. Romanisation is CARRIED, not recomputed. The reader romanises Telugu at render time with
   te2rom, which cannot know what this pipeline's pinned profile decided about a loanword or a
   protected name. Each line and each form carries the romanisation the pipeline computed, and
   the reader prefers it when present.

NOTHING HERE IS APPROVED. Every bundle is status=draft by its own manifest: no native review,
no source approval, morphology analyses tentative. Senses land as status=draft so the card says
so, and `reviewerNeeded` parts are flagged rather than presented as settled.
"""
import argparse
import datetime
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from ids import guid

# Token kinds the pipeline emits that are not words.
INERT = {'whitespace', 'punctuation'}
# Words that should never be pushed at you as vocabulary to learn, per the pipeline's own
# learning.vocabulary priority field.
REFERENCE_ONLY = {'reference_only'}


def chapter_dirs(src):
    """-> [(chapter number, revision directory)] for every built chapter, in order."""
    out = []
    base = os.path.join(src, 'books', 'prisoner-of-azkaban', 'output')
    for d in sorted(glob.glob(os.path.join(base, 'ch*-pilot'))):
        cur = os.path.join(d, 'current.json')
        if not os.path.exists(cur):
            continue
        with open(cur, encoding='utf-8') as f:
            rev = json.load(f)['revision']
        rd = os.path.join(d, rev)
        if not os.path.isdir(rd):
            continue
        num = int(os.path.basename(d)[2:5])
        out.append((num, rd))
    return out


def load_chapter(rev_dir):
    """-> (catalog, [(scene id, bundle)]) in catalog order."""
    with open(os.path.join(rev_dir, 'catalog.json'), encoding='utf-8') as f:
        cat = json.load(f)
    scenes = []
    for s in cat['scenes']:
        sid = s['id']
        p = os.path.join(rev_dir, 'bundles', f'{sid}.json')
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8') as f:
            scenes.append((s, json.load(f)))
    return cat, scenes


def word_guid(surface, roman):
    """A form's id. Telugu hashes on its own text; Latin-only forms use the romanisation
    fallback that ids.guid already provides, so a name gets a stable id without being passed
    off as Telugu."""
    has_te = any('ఀ' <= ch <= '౿' for ch in surface)
    return guid('W', surface if has_te else '', '' if has_te else (roman or surface))


class Build:
    def __init__(self):
        self.lex = []
        self.lex_at = {}          # surface -> index
        self.occ = []
        self.cx = []
        self.cx_at = {}           # construction id -> index
        self.stories = []
        self.counts = {}
        self.first_seen = {}

    # ---- constructions ----
    def construction(self, c):
        if c['id'] not in self.cx_at:
            self.cx_at[c['id']] = len(self.cx)
            self.cx.append({'l': c.get('label', ''), 'x': c.get('explanation', ''),
                            'k': c.get('kind', '')})
        return self.cx_at[c['id']]

    # ---- forms ----
    def form(self, surface, roman, story_num):
        """Index of this surface form in the dataset lexicon, creating it if new."""
        if surface in self.lex_at:
            i = self.lex_at[surface]
            self.counts[surface] = self.counts.get(surface, 0) + 1
            return i
        i = len(self.lex)
        self.lex_at[surface] = i
        self.counts[surface] = 1
        self.first_seen[surface] = story_num
        self.lex.append({'te': surface, 'g': word_guid(surface, roman), 'o': i})
        if roman and roman != surface:
            self.lex[i]['r'] = roman
        return i


def parts_of(analysis):
    """Structured morphology: text, plain label, semantic role, and whether it needs review.

    Kept as a list of small arrays rather than the flat [text, label] pairs the older import
    produced, because the pipeline distinguishes a stem from a case marker from a fused
    inflection, and that distinction is the difference between a colour-coded split and an
    explanation. An empty surface (a zero morpheme) is dropped: there is nothing to point at.
    """
    out = []
    for p in (analysis.get('parts') or []):
        surf = (p.get('surface') or {})
        text = (surf.get('text') or '').strip()
        if not text:
            continue
        out.append([text, p.get('label', ''), p.get('category', ''),
                    1 if p.get('reviewerNeeded') else 0])
    return out


def build(src, chapters, book_title, tag, unit):
    b = Build()
    chs = [c for c in chapter_dirs(src) if not chapters or c[0] in chapters]
    if not chs:
        raise SystemExit('no built chapters found')

    story_num = 0
    ch_titles = {}
    for ch_num, rev in chs:
        cat, scenes = load_chapter(rev)
        ch_titles[ch_num] = cat.get('title') or f'Chapter {ch_num}'
        for meta, bundle in scenes:
            story_num += 1
            lexemes = {x['id']: x for x in bundle['lexemes']}
            senses = {x['id']: x for x in bundle['senses']}
            forms = {x['id']: x for x in bundle['forms']}
            analyses = {x['id']: x for x in bundle['analyses']}
            cxs = {x['id']: x for x in bundle['constructions']}
            occ_by_token = {}
            for o in bundle['occurrences']:
                for tid in (o.get('tokenIds') or []):
                    occ_by_token[tid] = o
            # Which lexemes the pipeline says are reference material, not vocabulary.
            priority = {}
            for v in (bundle['learning'].get('vocabulary') or []):
                priority[v.get('lexemeId')] = v.get('priority', '')

            lines = []
            for sn in sorted(bundle['sentences'], key=lambda s: s.get('order', 0)):
                te = (sn.get('telugu') or {}).get('text', '')
                toks = []
                for t in sorted(sn.get('tokens') or [], key=lambda t: t.get('index', 0)):
                    surface = t.get('surface', '')
                    if not surface:
                        continue
                    if t.get('kind') in INERT or not t.get('formIds'):
                        toks.append([surface, 'p', -1])
                        continue
                    fid = t['formIds'][0]
                    fm = forms.get(fid) or {}
                    # romanization is a provenance object — the string lives under .text,
                    # alongside the engine and profile that produced it.
                    li = b.form(surface, (fm.get('romanization') or {}).get('text', ''),
                                story_num)
                    o = occ_by_token.get(t['id'])
                    oi = -1
                    if o:
                        oi = len(b.occ)
                        lx = lexemes.get(o.get('lexemeId')) or {}
                        se = senses.get(o.get('senseId')) or {}
                        an = analyses.get(o.get('analysisId')) or {}
                        ea = o.get('englishAlignment') or {}
                        rec = {'g': o.get('contextualGloss', '')}
                        # `unresolved` is the pipeline's honest "not analysed yet", and it is
                        # 71% of roles. Carrying it would put the word "unresolved" on three
                        # cards in four, which reads as a malfunction rather than as candour.
                        if o.get('roleInSentence') and o['roleInSentence'] != 'unresolved':
                            rec['r'] = o['roleInSentence']
                        # The aligned English, as text. The spans carry it directly, so there is
                        # no offset slicing to get wrong — and "this word means THIS bit of the
                        # English sentence" is the single most useful thing on the card.
                        if ea.get('relation') == 'phrase':
                            txt = ' … '.join(x.get('text', '') for x in (ea.get('spans') or [])
                                             if x.get('text'))
                            if txt:
                                rec['ep'] = txt
                        # `resolution` is 'tentative' for all 6,650 occurrences, so it belongs
                        # once on the dataset, not on every card.
                        ids = [b.construction(cxs[c]) for c in (o.get('constructionIds') or [])
                               if c in cxs]
                        if ids:
                            rec['cx'] = ids
                        b.occ.append(rec)
                        # Enrich the form entry from this occurrence's analysis the first time
                        # we see it. The form-level card is the fallback for list views, where
                        # there is no occurrence in hand.
                        e = b.lex[li]
                        if 'en' not in e and se.get('gloss'):
                            e['en'] = se['gloss']
                        if 'lm' not in e and lx.get('lemmaTelugu'):
                            e['lm'] = {'te': lx.get('lemmaTelugu', ''),
                                       'en': lx.get('lemmaEnglish', ''),
                                       'p': lx.get('pos', '')}
                        if 'pt' not in e:
                            pt = parts_of(an)
                            if len(pt) > 1:
                                e['pt'] = pt
                        if 'sn' not in e and se.get('gloss'):
                            e['sn'] = [{'g': se['gloss'], 'p': lx.get('pos', ''),
                                        'x': se.get('usageNote', ''), 's': 'draft'}]
                        if priority.get(o.get('lexemeId')) in REFERENCE_ONLY:
                            e['ref'] = 1
                    toks.append([surface, 'w', li, oi] if oi >= 0 else [surface, 'w', li])
                line = {'g': guid('S', te) if te else guid('S', '', sn['id']),
                        'p': meta['id'], 't': toks}
                if sn.get('simplifiedEnglish'):
                    line['en'] = sn['simplifiedEnglish']
                rom = (sn.get('romanization') or {}).get('text')
                if rom:
                    line['rom'] = rom
                lines.append(line)

            b.stories.append({
                'num': story_num, 'ch': ch_num,
                'title': {'te': meta.get('titleTe') or '', 'en': meta.get('titleEn') or meta['id']},
                'summary': meta.get('summaryEn') or '',
                'lines': lines,
            })

    for surface, i in b.lex_at.items():
        b.lex[i]['n'] = b.counts[surface]
        b.lex[i]['f'] = b.first_seen[surface]

    return {
        'generated': datetime.date.today().isoformat(),
        'source': book_title,
        'tag': tag,
        'unit': unit,
        'collection': {'en': book_title, 'short': 'Prisoner of Azkaban'},
        'clips': '../poa/audio/words',
        'groups': [{'n': n, 'en': t} for n, t in sorted(ch_titles.items())],
        'status': 'draft',
        'lex': b.lex,
        'occ': b.occ,
        'cx': b.cx,
        'stories': b.stories,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='the telugu-graded-readers project directory')
    ap.add_argument('--chapters', default='', help='e.g. 1,2 — default every built chapter')
    ap.add_argument('--out', default='reader/data/poa.js')
    ap.add_argument('--var', default='POA_DATA')
    ap.add_argument('--tag', default='poa')
    ap.add_argument('--unit', default='section')
    ap.add_argument('--title', default='Harry Potter and the Prisoner of Azkaban')
    args = ap.parse_args()

    chapters = {int(x) for x in args.chapters.split(',') if x.strip()}
    data = build(os.path.expanduser(args.src), chapters, args.title, args.tag, args.unit)

    out = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('/* Generated by tools/import_graded.py. Do not edit. */\n')
        f.write(f'window.{args.var} = ')
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')

    forms = len(data['lex'])
    glossed = sum(1 for l in data['lex'] if l.get('en'))
    with_parts = sum(1 for l in data['lex'] if l.get('pt'))
    with_lemma = sum(1 for l in data['lex'] if l.get('lm'))
    latin = sum(1 for l in data['lex']
                if not any('ఀ' <= c <= '౿' for c in l['te']))
    lines = sum(len(s['lines']) for s in data['stories'])
    size = os.path.getsize(out)
    print(f'{os.path.relpath(out, ROOT)}  {size / 1048576:.1f} MB')
    print(f'  {len(data["stories"])} sections across {len(data["groups"])} chapters, {lines} lines')
    print(f'  {forms:,} word forms — {glossed:,} glossed, {with_lemma:,} with a base word, '
          f'{with_parts:,} with a morphology split')
    print(f'  {latin:,} of those are protected Latin, now clickable rather than inert')
    print(f'  {len(data["occ"]):,} occurrences, {len(data["cx"])} constructions')
    print(f'  window.{args.var}  tag={data["tag"]}  unit={data["unit"]}  status={data["status"]}')


if __name__ == '__main__':
    main()
