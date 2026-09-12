# -*- coding: utf-8 -*-
"""Bring an outside resource — audio plus transcript — to the point where the reader can serve it.

    python3 tools/import_resource.py new telugu-podcast-01 --title "..." --unit episode
    python3 tools/import_resource.py segment telugu-podcast-01
    python3 tools/import_resource.py align   telugu-podcast-01
    python3 tools/import_resource.py analyze telugu-podcast-01
    python3 tools/import_resource.py status

WHY A GENERIC STAGING AREA AND NOT A THIRD TOP-LEVEL DIRECTORY
The two corpora already here each got their own directory and their own bespoke tooling:
ministories/ with ms_*.py, intensive/ with ic_*.py. Fourteen tools between them, and perhaps
three of those twenty-eight files contain reasoning that is genuinely about Mini Stories or
about the course. The rest is the same pipeline twice — segment, gloss, align, count, build —
diverged by accident. A third copy for the first podcast, a fourth for the second, and the
tooling becomes the project. So: one directory per resource, all of them the same shape, one
tool that walks that shape.

THE SENTENCE IS THE UNIT — the same call ms_segment.py makes, and for its downstream reason
rather than its pedagogical one. An audio timestamp attaches to a sentence; the reader's
click-to-look-up, its rating cursor and its per-sentence word list are all sentence-scoped.
Paragraph-level segments would have to be re-split before any of that worked, and the re-split
is where alignment drifts. (hp_segment.py takes the paragraph instead, because a translator
restructuring English participles into Telugu clauses cannot be held to a sentence count. A
transcript is not being restructured — it is being timestamped.)

WHAT IS COMMITTED AND WHAT IS NOT
imports/<slug>/ holds someone else's audio and someone else's transcript, so it is gitignored,
on the same reasoning as sources/local/ and translate/source/. What gets committed is this
tool, and — once a resource is built — the reader dataset derived from it, which is subject to
the same question every corpus here has had to answer: is the derived form ours to publish?
For our own translation of a permissively-licensed transcript, yes. For a copyrighted podcast,
no: study it locally, serve it from a local checkout, and keep it out of the Pages build. The
`rights` field in meta.json exists to make you answer that before you spend the effort, and
`build` refuses to emit a public dataset while it says `local-only`.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from ids import guid

IMPORTS = os.path.join(ROOT, 'imports')

# Mirrors build_ms_reader.py's TOKEN, which mirrors lex.js. Kept identical on purpose: a word
# the reader would split differently is a word whose count here is a lie.
TOKEN = re.compile(r"[ఀ-౿‌‍]+|[^\W\d_]+(?:['’][^\W\d_]+)*|\d+|[^\w\s]+|\s+")
TELUGU = re.compile(r"[ఀ-౿]")

# Telugu ends sentences with the Latin full stop in practice, and the danda survives in older
# or more formal text. Question and exclamation marks behave as they do in English.
SENT_END = re.compile(r'(?<=[.?!।॥])\s+')

COLS = ['guid', 'idx', 'kind', 'te', 'en', 'start', 'end', 'notes', 'status']

AUDIO_EXT = ('.mp3', '.m4a', '.wav', '.opus', '.ogg', '.flac', '.aac')
CAPTION_EXT = ('.vtt', '.srt')


# ---------------------------------------------------------------- paths and metadata

def res_dir(slug):
    return os.path.join(IMPORTS, slug)


def meta_path(slug):
    return os.path.join(res_dir(slug), 'meta.json')


def load_meta(slug):
    p = meta_path(slug)
    if not os.path.exists(p):
        raise SystemExit(f'no such resource: {slug}\n  expected {os.path.relpath(p, ROOT)}\n'
                         f'  create it with:  python3 tools/import_resource.py new {slug}')
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save_meta(slug, meta):
    with open(meta_path(slug), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')


def find_one(slug, exts, what):
    """The single file in the resource directory with one of these extensions."""
    d = res_dir(slug)
    hits = sorted(n for n in os.listdir(d)
                  if n.lower().endswith(exts) and not n.startswith('.'))
    if not hits:
        return None
    if len(hits) > 1:
        print(f'  note: {len(hits)} {what} files present, using {hits[0]}')
    return os.path.join(d, hits[0])


def segments_path(slug):
    return os.path.join(res_dir(slug), 'segments.tsv')


def read_segments(slug):
    p = segments_path(slug)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def write_segments(slug, rows):
    with open(segments_path(slug), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, COLS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- new

SCAFFOLD = """Drop two files in this directory:

  the audio       {slug}.mp3   (or .m4a/.wav/.opus — any one audio file)
  the transcript  transcript.txt

Optionally, and much better if you can get it:

  captions        {slug}.vtt   (or .srt)

Captions carry real timings, which turns alignment from an estimate into a fact. YouTube's
auto-captions, a podcast's published transcript and anything from a subtitle site all work.
Download them with yt-dlp --write-auto-subs --sub-lang te --skip-download <url>.

Then:

  python3 tools/import_resource.py segment {slug}
  python3 tools/import_resource.py align   {slug}
  python3 tools/import_resource.py analyze {slug}
"""


def cmd_new(args):
    d = res_dir(args.slug)
    if os.path.exists(meta_path(args.slug)) and not args.force:
        raise SystemExit(f'{args.slug} already exists — pass --force to overwrite its meta.json')
    os.makedirs(d, exist_ok=True)
    meta = {
        'slug': args.slug,
        'title': args.title or args.slug,
        'unit': args.unit,
        'kind': args.kind,
        'source': args.source or '',
        # Answered now, not later. See the module docstring.
        'rights': args.rights,
        'lang': 'te',
    }
    save_meta(args.slug, meta)
    with open(os.path.join(d, 'START_HERE.txt'), 'w', encoding='utf-8') as f:
        f.write(SCAFFOLD.format(slug=args.slug))
    print(f'created {os.path.relpath(d, ROOT)}/')
    print(f'  meta.json     title={meta["title"]!r} unit={meta["unit"]} rights={meta["rights"]}')
    print(f'  START_HERE.txt what to drop in next')


# ---------------------------------------------------------------- segment

def sentences_of(text):
    """Transcript -> sentences, keeping blank-line structure as a paragraph break.

    Splitting on sentence enders alone merges a speaker change into the previous sentence when
    the transcript marks it only with a line break, which is how most published transcripts
    mark it. So: paragraphs first, sentences within.
    """
    out = []
    for block in re.split(r'\n\s*\n', text):
        block = ' '.join(block.split())
        if not block:
            continue
        for s in SENT_END.split(block):
            s = s.strip()
            if s:
                out.append(s)
    return out


def build_rows(slug, triples):
    """[(text, start, end)] -> segment rows, carrying hand-entered columns forward by guid.

    The same contract hp_segment.py and build_master.py hold to: a rebuild that eats
    hand-entered work is the most expensive bug in this repo, because nothing looks wrong until
    much later. A timing already on disk wins over a fresh one only when the fresh one is
    absent, so re-aligning can improve timings but re-segmenting cannot lose a translation.
    """
    prior = {r['guid']: r for r in read_segments(slug)}
    rows, seen = [], {}
    for idx, (text, start, end) in enumerate(triples):
        seen[text] = seen.get(text, 0) + 1
        key = text if seen[text] == 1 else f'{text}#{seen[text]}'
        g = guid('R', key if TELUGU.search(key) else '', key)
        old = prior.get(g, {})
        is_te = bool(TELUGU.search(text))
        rows.append({
            'guid': g, 'idx': idx,
            'kind': 'te' if is_te else 'en',
            'te': text if is_te else '',
            'en': old.get('en', '') or ('' if is_te else text),
            'start': f'{start:.2f}' if start not in ('', None) else old.get('start', ''),
            'end': f'{end:.2f}' if end not in ('', None) else old.get('end', ''),
            'notes': old.get('notes', ''), 'status': old.get('status', 'todo'),
        })
    return rows, prior


def warn_undersplit(rows, slug):
    """Say so when the transcript had no sentence punctuation to split on.

    Silence here would be the bad kind: the pipeline runs, the file appears, and the damage —
    three minutes of audio behind one timestamp — only shows up as a reader that feels wrong
    to use.
    """
    te = [r for r in rows if r['kind'] == 'te']
    if not te:
        return
    long_ones = [r for r in te if len(r['te']) > 200]
    unpunctuated = [r for r in te if not re.search(r'[.?!।॥]$', r['te'])]
    if len(unpunctuated) > len(te) * 0.4:
        print(f'  !! {len(unpunctuated)}/{len(te)} segments do not end in sentence punctuation.')
        print('     The transcript has little or none, so these are paragraph blocks, not')
        print('     sentences. If you have captions, re-run with --from-captions: cue timings')
        print('     give real sentence breaks and exact timestamps in one step.')
    elif long_ones:
        print(f'  note: {len(long_ones)} segments are over 200 characters.')


def segment_from_captions(args, meta):
    """Segment and time in one pass, from the caption file."""
    caps = find_one(args.slug, CAPTION_EXT, 'caption')
    if not caps:
        raise SystemExit('no .vtt/.srt in the resource directory.\n'
                         '  yt-dlp --write-auto-subs --sub-lang te --skip-download <url>')
    cues = read_captions(caps)
    if not cues:
        raise SystemExit(f'no cues parsed from {os.path.basename(caps)}')
    triples = segments_from_cues(cues, max_chars=args.max_chars)
    rows, prior = build_rows(args.slug, triples)
    dropped = [g for g, r in prior.items()
               if g not in {x['guid'] for x in rows} and (r.get('en') or r.get('notes'))]
    write_segments(args.slug, rows)
    carried = sum(1 for r in rows if r['en'] and r['kind'] == 'te')
    print(f'{args.slug}: {len(cues)} cues in {os.path.basename(caps)} '
          f'-> {len(rows)} segments, all timed')
    if carried:
        print(f'  {carried} translations carried forward')
    if dropped:
        print(f'  !! {len(dropped)} rows with work no longer match — cue text or --max-chars changed')
    warn_undersplit(rows, args.slug)
    meta['segments'] = len(rows)
    save_meta(args.slug, meta)


def segments_from_cues(cues, max_chars=140):
    """Cue runs -> sentences, with their timings.

    THE BETTER PATH FOR AN AUDIO RESOURCE, and the reason is not subtle: captions already
    record where the speech actually broke. Sentence-final punctuation does not survive most
    real transcripts — auto-captions have none at all, and a transcript typed from audio keeps
    it only when the typist bothered. Splitting such a file on `.?!` under-splits badly: a
    48-sentence stretch with no full stops becomes one segment, and one segment is one
    timestamp, one rating and one click-to-look-up for three minutes of audio.

    Cues break on reading width rather than syntax, so they are merged: accumulate until a
    sentence ender appears, or until max_chars, whichever comes first. Ending on punctuation
    when it exists and on a width budget when it does not degrades gracefully instead of
    failing outright.
    """
    out, buf, start, end = [], [], None, None
    for a, b, text in cues:
        text = ' '.join(text.split())
        if not text:
            continue
        if start is None:
            start = a
        end = b
        buf.append(text)
        joined = ' '.join(buf)
        if re.search(r'[.?!।॥]$', joined) or len(joined) >= max_chars:
            out.append((joined, start, end))
            buf, start, end = [], None, None
    if buf:
        out.append((' '.join(buf), start, end))
    return out


def cmd_segment(args):
    meta = load_meta(args.slug)
    if args.from_captions:
        return segment_from_captions(args, meta)
    tp = os.path.join(res_dir(args.slug), 'transcript.txt')
    if not os.path.exists(tp):
        raise SystemExit(f'no transcript at {os.path.relpath(tp, ROOT)} — see START_HERE.txt')
    raw = open(tp, 'rb').read()
    for enc in ('utf-8', 'utf-8-sig', 'cp1252', 'latin-1'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f'cannot decode {tp}')
    text = unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n'))

    sents = sentences_of(text)
    if not sents:
        raise SystemExit('transcript produced no sentences')

    rows, prior = build_rows(args.slug, [(s, '', '') for s in sents])
    carried = sum(1 for r in rows if r['en'] and r['kind'] == 'te')
    timed = sum(1 for r in rows if r['start'])
    dropped = [g for g, r in prior.items()
               if g not in {x['guid'] for x in rows} and (r.get('en') or r.get('start'))]
    write_segments(args.slug, rows)

    te = sum(1 for r in rows if r['kind'] == 'te')
    print(f'{args.slug}: {len(rows)} segments  ({te} Telugu, {len(rows) - te} other)')
    warn_undersplit(rows, args.slug)
    if carried:
        print(f'  {carried} translations carried forward')
    if timed:
        print(f'  {timed} timings carried forward')
    if dropped:
        print(f'  !! {len(dropped)} rows with work no longer match any sentence — the transcript')
        print(f'     was edited. Recover from git or re-enter; nothing was deleted before this run.')
    meta['segments'] = len(rows)
    save_meta(args.slug, meta)


# ---------------------------------------------------------------- align

def audio_duration(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def parse_timecode(s):
    """00:01:02,345 / 00:01:02.345 / 01:02.345 -> seconds."""
    s = s.strip().replace(',', '.')
    parts = s.split(':')
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


CUE_LINE = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3}|\d{1,2}:\d{2}(?::\d{2})?)'
                      r'\s*-->\s*'
                      r'(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3}|\d{1,2}:\d{2}(?::\d{2})?)')


def read_captions(path):
    """-> [(start, end, text)] for WebVTT or SRT.

    Hand-rolled rather than a dependency: both formats are a timecode line and some text, the
    machine has neither webvtt-py nor srt installed, and a parser this size is easier to trust
    than a pinned wheel.
    """
    raw = open(path, 'rb').read().decode('utf-8-sig', errors='replace')
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    cues, cur = [], None
    for line in raw.split('\n'):
        m = CUE_LINE.search(line)
        if m:
            if cur:
                cues.append(cur)
            cur = [parse_timecode(m.group(1)), parse_timecode(m.group(2)), []]
            continue
        if cur is None:
            continue
        if not line.strip():
            cues.append(cur)
            cur = None
            continue
        # WebVTT inline tags and karaoke timestamps carry no text.
        txt = re.sub(r'<[^>]+>', '', line).strip()
        if txt and not txt.isdigit():
            cur[2].append(txt)
    if cur:
        cues.append(cur)
    return [(a, b, ' '.join(t)) for a, b, t in cues if a is not None and t]


def fold_te(s):
    """Comparison key: Telugu characters only. Captions and transcripts disagree about
    punctuation, spacing and Latin interjections far more often than about the words."""
    return ''.join(TELUGU.findall(s))


def align_from_captions(rows, cues):
    """Give each segment the span of the cues whose text it covers.

    Walks both sequences once, matching on Telugu characters only. A transcript sentence
    usually spans two or three cues (captions break on reading width, not on syntax), so the
    segment takes the first matched cue's start and the last one's end.
    """
    cue_chars = [(a, b, fold_te(t)) for a, b, t in cues]
    ci, hits = 0, 0
    for r in rows:
        want = fold_te(r['te'] or r['en'])
        if not want:
            continue
        got, first, last = '', None, None
        j = ci
        # Tolerate a caption the transcript omits (music stings, station idents) by allowing a
        # small lookahead before giving up on this segment.
        skips = 0
        while j < len(cue_chars) and len(got) < len(want):
            a, b, c = cue_chars[j]
            if not c:
                j += 1
                continue
            if c and c in want[len(got):len(got) + len(c) + 4] or want[len(got):].startswith(c[:6]):
                if first is None:
                    first = a
                last = b
                got += c
                j += 1
            elif first is None and skips < 3:
                j += 1
                skips += 1
            else:
                break
        if first is not None:
            r['start'] = f'{first:.2f}'
            r['end'] = f'{last:.2f}'
            # A measured timing clears the estimate flag. Leaving `est` on a row that now holds
            # a real timestamp is the stale-manifest bug again: a column that says the opposite
            # of what the file contains, discovered months later when it is expensive.
            if r['status'] == 'est':
                r['status'] = 'todo'
            ci = j
            hits += 1
    return hits


def align_proportional(rows, duration):
    """Spread the audio across the segments by character weight.

    An estimate, and labelled one: status becomes `est` so nothing downstream mistakes it for
    a measurement. Speech rate is not constant, so late segments drift — fine for "play this
    sentence" on a five-minute clip, useless on an hour-long episode. It exists because a
    rough timing beats no timing when captions are unavailable, and because it makes the
    reader's play button work on day one.
    """
    weights = [len(fold_te(r['te']) or r['en']) for r in rows]
    total = sum(weights) or 1
    t = 0.0
    for r, w in zip(rows, weights):
        span = duration * w / total
        r['start'] = f'{t:.2f}'
        r['end'] = f'{t + span:.2f}'
        if r['status'] in ('', 'todo'):
            r['status'] = 'est'
        t += span
    return len(rows)


def cmd_align(args):
    load_meta(args.slug)
    rows = read_segments(args.slug)
    if not rows:
        raise SystemExit(f'no segments — run:  python3 tools/import_resource.py segment {args.slug}')

    audio = find_one(args.slug, AUDIO_EXT, 'audio')
    caps = find_one(args.slug, CAPTION_EXT, 'caption')

    if caps and not args.proportional:
        cues = read_captions(caps)
        hits = align_from_captions(rows, cues)
        write_segments(args.slug, rows)
        print(f'{args.slug}: {len(cues)} cues in {os.path.basename(caps)}')
        print(f'  {hits}/{len(rows)} segments timed from captions')
        if hits < len(rows) * 0.8:
            print('  !! under 80% matched. The captions and the transcript are probably different')
            print('     texts (auto-captions vs a cleaned-up transcript). Compare a few lines, or')
            print('     re-run with --proportional to estimate instead.')
        return

    if not audio:
        raise SystemExit('no audio file and no captions — nothing to align against.\n'
                         '  Drop an audio file in, or a .vtt/.srt (much better). See START_HERE.txt')
    dur = audio_duration(audio)
    if dur is None:
        raise SystemExit(f'ffprobe could not read a duration from {os.path.basename(audio)}')
    n = align_proportional(rows, dur)
    write_segments(args.slug, rows)
    print(f'{args.slug}: {os.path.basename(audio)} is {dur / 60:.1f} min')
    print(f'  {n} segments timed by character weight, status=est')
    print('  These are ESTIMATES. For real timings get captions, or install forced alignment:')
    print('    pip install openai-whisper   (then --whisper, ~1.5 GB of model)')


# ---------------------------------------------------------------- analyze

def known_vocab():
    """Every Telugu word form this project already has a definition for.

    Membership in a corpus, not what you personally know — the reader keeps your levels in the
    browser's localStorage, which no script here can read. So "known" below means "already
    glossed somewhere in this project", which is the useful question when deciding whether a
    new resource is reachable: a word with a definition is a word the reader can teach you on
    contact.
    """
    words = {}
    sources = [
        ('ministories', os.path.join(ROOT, 'ministories', 'vocab.tsv'), 'te'),
        ('intensive', os.path.join(ROOT, 'intensive', 'vocab.tsv'), 'te'),
        ('master', os.path.join(ROOT, 'data', 'master_words.tsv'), 'telugu'),
    ]
    for name, path, col in sources:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                te = (r.get(col) or '').strip()
                if te:
                    words.setdefault(te, name)
    return words


def cmd_analyze(args):
    meta = load_meta(args.slug)
    rows = read_segments(args.slug)
    if not rows:
        raise SystemExit(f'no segments — run:  python3 tools/import_resource.py segment {args.slug}')

    counts = Counter()
    for r in rows:
        for piece in TOKEN.findall(r['te'] or ''):
            if TELUGU.search(piece):
                counts[piece] += 1

    known = known_vocab()
    tokens = sum(counts.values())
    types = len(counts)
    if not tokens:
        raise SystemExit('no Telugu tokens found — is the transcript actually Telugu?')

    known_types = [w for w in counts if w in known]
    new_types = [w for w in counts if w not in known]
    known_tokens = sum(counts[w] for w in known_types)

    # The threshold from the study-plan analysis: incidental acquisition wants 8-20 encounters
    # (Nation, Webb). Words below it are worth a definition but will not stick from this
    # resource alone; words above it are the ones this resource can actually teach.
    repeated_new = sorted(((c, w) for w, c in counts.items() if w not in known and c >= 8),
                          reverse=True)

    timed = sum(1 for r in rows if r['start'])
    untranslated = sum(1 for r in rows if r['kind'] == 'te' and not r['en'].strip())

    lines = []
    add = lines.append
    add(f'# {meta.get("title", args.slug)}')
    add('')
    add(f'`imports/{args.slug}` · {meta.get("kind", "?")} · rights: **{meta.get("rights", "?")}**')
    add('')
    add('## Size')
    add('')
    add(f'| | |')
    add(f'|---|---|')
    add(f'| Segments | {len(rows)} |')
    add(f'| Telugu tokens | {tokens:,} |')
    add(f'| Distinct word forms | {types:,} |')
    add(f'| Timed | {timed}/{len(rows)} |')
    add(f'| Awaiting English | {untranslated} |')
    add('')
    add('## Reachability')
    add('')
    add(f'- **{known_tokens / tokens * 100:.1f}% of tokens** are word forms this project already')
    add(f'  glosses ({len(known_types):,} of {types:,} forms). The rest need a definition before')
    add(f'  the reader can teach them on contact.')
    add(f'- **{len(new_types):,} new word forms.**')
    add('')
    add('Coverage is by surface form, not lemma, so it understates: `వచ్చాడు` counts as new even')
    add('when `వచ్చు` is glossed. Treat it as a floor.')
    add('')
    add(f'## The {len(repeated_new)} new words this resource can actually teach')
    add('')
    add('Eight or more encounters, the floor for picking a word up from context alone')
    add('(Nation; Webb). Everything below that count is worth a definition but will not stick')
    add('from this resource by itself — those are the ones to put in a drill.')
    add('')
    if repeated_new:
        add('| × | word |')
        add('|---|---|')
        for c, w in repeated_new[:60]:
            add(f'| {c} | {w} |')
        if len(repeated_new) > 60:
            add('')
            add(f'…and {len(repeated_new) - 60} more.')
    else:
        add('None — every repeated word is already glossed. This resource is for reading, not')
        add('for building vocabulary breadth.')
    add('')

    p = os.path.join(res_dir(args.slug), 'report.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'{args.slug}: {tokens:,} tokens, {types:,} forms')
    print(f'  {known_tokens / tokens * 100:.1f}% of tokens already glossed  '
          f'({len(new_types):,} new forms)')
    print(f'  {len(repeated_new)} new forms occur 8+ times')
    print(f'  wrote {os.path.relpath(p, ROOT)}')


# ---------------------------------------------------------------- status

def cmd_status(args):
    if not os.path.isdir(IMPORTS):
        print('no imports/ directory yet')
        return
    slugs = sorted(n for n in os.listdir(IMPORTS)
                   if os.path.exists(os.path.join(IMPORTS, n, 'meta.json')))
    if not slugs:
        print('no resources yet — create one with:')
        print('  python3 tools/import_resource.py new <slug> --title "..." ')
        return
    print(f'{"slug":22} {"segments":>8} {"timed":>6} {"english":>8}  rights')
    for slug in slugs:
        meta = load_meta(slug)
        rows = read_segments(slug)
        timed = sum(1 for r in rows if r['start'])
        en = sum(1 for r in rows if r['kind'] == 'te' and r['en'].strip())
        te = sum(1 for r in rows if r['kind'] == 'te') or 1
        print(f'{slug:22} {len(rows):>8} {timed:>6} {en:>4}/{te:<4} {meta.get("rights", "?")}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('new', help='scaffold a resource directory')
    p.add_argument('slug')
    p.add_argument('--title', default='')
    p.add_argument('--unit', default='episode', help='what one item is called: episode, chapter…')
    p.add_argument('--kind', default='podcast', help='podcast, audiobook, video, conversation…')
    p.add_argument('--source', default='', help='where it came from (URL, show name)')
    p.add_argument('--rights', default='local-only', choices=['local-only', 'ours', 'open'],
                   help='local-only blocks publishing it to the site')
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser('segment', help='transcript.txt -> segments.tsv')
    p.add_argument('slug')
    p.add_argument('--from-captions', action='store_true',
                   help='segment from the .vtt/.srt instead, which also times every segment')
    p.add_argument('--max-chars', type=int, default=140,
                   help='longest segment when punctuation gives no break (default 140)')
    p.set_defaults(fn=cmd_segment)

    p = sub.add_parser('align', help='give segments timings, from captions or by estimate')
    p.add_argument('slug')
    p.add_argument('--proportional', action='store_true',
                   help='estimate by character weight even if captions exist')
    p.set_defaults(fn=cmd_align)

    p = sub.add_parser('analyze', help='vocabulary coverage report')
    p.add_argument('slug')
    p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser('status', help='every resource and how far along it is')
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
