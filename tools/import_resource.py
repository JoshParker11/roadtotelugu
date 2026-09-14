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
import difflib
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


def lines_of(text, max_chars=220):
    """One segment per transcript line.

    A third transcript shape, and the commonest one a generated discussion produces: no blank
    lines, no speaker labels, one utterance per line, and sentence-final punctuation on only
    some of them. Neither of the other two readers handles it — sentences_of() sees a single
    paragraph and merges every unpunctuated turn into its neighbour, and there are no cues to
    segment from. The line break is the only structure the file has, so it is the one to trust.

    A long line is still split on sentence enders, because a 200-character turn holding three
    sentences is three things to read.
    """
    out = []
    for raw in text.split('\n'):
        line = ' '.join(raw.split())
        if not line:
            continue
        parts = SENT_END.split(line) if len(line) > max_chars else [line]
        for part in parts:
            part = part.strip()
            if part:
                out.append(part)
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


def warn_undersplit(rows, slug, by_line=False):
    """Say so when the transcript had no sentence punctuation to split on.

    Silence here would be the bad kind: the pipeline runs, the file appears, and the damage —
    three minutes of audio behind one timestamp — only shows up as a reader that feels wrong
    to use.

    Not in --lines mode, though. There the line is the unit by instruction, so a turn ending
    without a full stop is the expected shape and not a symptom of anything. Warning about it
    anyway is how a warning stops being read: it fired on 57 of 141 correct segments and
    recommended captions that do not exist.
    """
    te = [r for r in rows if r['kind'] == 'te']
    if not te:
        return
    long_ones = [r for r in te if len(r['te']) > 200]
    unpunctuated = [r for r in te if not re.search(r'[.?!।॥]$', r['te'])]
    if not by_line and len(unpunctuated) > len(te) * 0.4:
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

    sents = lines_of(text) if args.lines else sentences_of(text)
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
    warn_undersplit(rows, args.slug, by_line=args.lines)
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


SILENCE = re.compile(r'silence_(start|end):\s*(-?[\d.]+)')


def speech_runs(path, noise=-40, gap=0.35):
    """-> ([(start, end)] of speech, total duration)

    ffmpeg's silencedetect reports at INFO level, so it must not be run under `-v error` —
    that returns zero gaps on any input and looks exactly like an audio file with no pauses.
    Cost an hour once; hence this note.

    -40dB rather than the usual -30: generated audio is loudness-compressed and has no true
    digital silence, so a strict threshold finds nothing. 0.35s rather than 0.2 because the
    target is a turn boundary, not the stop before a consonant.
    """
    total = audio_duration(path)
    if total is None:
        return [], None
    out = subprocess.run(
        ['ffmpeg', '-hide_banner', '-i', path, '-af',
         f'silencedetect=noise={noise}dB:d={gap}', '-f', 'null', '-'],
        capture_output=True, text=True)
    marks = SILENCE.findall(out.stderr or '')
    silences, start = [], None
    for kind, val in marks:
        t = float(val)
        if kind == 'start':
            start = t
        elif start is not None:
            silences.append((start, min(t, total)))
            start = None
    if start is not None:
        silences.append((start, total))
    # Invert: everything not silent is speech.
    runs, cursor = [], 0.0
    for a, b in silences:
        if a > cursor:
            runs.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < total:
        runs.append((cursor, total))
    return [r for r in runs if r[1] - r[0] > 0.05], total


MIN_SPAN = 0.35

# ---------------------------------------------------------------- alignment from ASR

ASR_MODEL = 'large-v3-turbo'


def asr_words(slug, audio, model=ASR_MODEL, force=False):
    """Recognise the audio, cached. -> [(word, start, end)]

    WHY RECOGNITION AT ALL, WHEN WE ALREADY HAVE THE TRANSCRIPT
    Because the transcript says WHAT is spoken and never WHEN. Every timing before this was
    derived from character counts and then judged by how well duration tracked character
    count — a measurement of its own assumption, which cannot detect being two turns out. The
    audio has to be consulted, and consulting it means recognising it.

    The recognition is wrong in detail and that is fine. It heard సాధారనంగా where the
    transcript reads సాధారణంగా, పద్ధదిలో for పద్ధతిలో. An anchor does not need the spelling to
    be right; it needs to be wrong at a known second.

    Model choice is not incidental: `small` returned 19 Telugu words out of 98 for two and a
    half minutes, the rest nonsense and stray Persian, while large-v3-turbo returned 138 of 138
    at roughly real time. Below turbo, Telugu is not worth attempting.
    """
    cache = os.path.join(res_dir(slug), 'asr_words.json')
    if os.path.exists(cache) and not force:
        with open(cache, encoding='utf-8') as f:
            return [(w['w'], w['s'], w['e']) for w in json.load(f)]
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit(
            'ASR alignment needs faster-whisper, which is not installed:\n'
            '    python3 -m pip install faster-whisper\n'
            f'  Then re-run. The recognised words are cached in {os.path.relpath(cache, ROOT)},\n'
            '  so this cost is paid once per resource.')
    print(f'  recognising with {model} — roughly real time, so ~{"?" } minutes')
    m = WhisperModel(model, device='cpu', compute_type='int8')
    segs, _info = m.transcribe(audio, language='te', word_timestamps=True,
                               vad_filter=True, beam_size=1)
    out = []
    for seg in segs:
        for w in (seg.words or []):
            out.append({'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3)})
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    return [(w['w'], w['s'], w['e']) for w in out]


def extra_runs(slug):
    """Additional recognitions of the same audio, if any were saved.

    asr_words2.json, asr_words3.json … Pooling independent runs densifies the anchors: two
    recognitions mis-hear different words, so each matches the transcript where the other
    failed, and the chain picks the best of both wherever they compete.
    """
    out = []
    for i in range(2, 6):
        p = os.path.join(res_dir(slug), f'asr_words{i}.json')
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                out.append([(w['w'], w['s'], w['e']) for w in json.load(f)])
    return out


def _char_timeline(words):
    """[(word, start, end)] -> (Telugu-only string, a time for each character)

    A word's characters are spread evenly inside its own span. Sub-word precision is not real,
    but an anchor only has to name the right second.
    """
    chars, times = [], []
    for w, st, en in words:
        te = [c for c in w if TELUGU.match(c)]
        if not te:
            continue
        span = max(en - st, 0.01)
        for i, c in enumerate(te):
            chars.append(c)
            times.append(st + span * (i + 0.5) / len(te))
    return ''.join(chars), times


def _line_chars(rows):
    chars, lines = [], []
    for i, r in enumerate(rows):
        for c in r['te']:
            if TELUGU.match(c):
                chars.append(c)
                lines.append(i)
    return ''.join(chars), lines


def _lis(pairs):
    """Longest non-decreasing-in-time subsequence of (line, time), by patience sorting.

    Anchors come from difflib's matching blocks, which are already monotonic — but a block can
    still be a coincidence, and Telugu's common syllables make short coincidences frequent. A
    greedy "drop anything earlier than the last kept" pass is at the mercy of its first
    survivor: one early stray time near the end of the file silently rejects everything after
    it. Keeping the longest consistent chain instead discards the stray and not the file.
    """
    if not pairs:
        return []
    import bisect
    tails, back, idx = [], [-1] * len(pairs), []
    for i, (_line, t) in enumerate(pairs):
        j = bisect.bisect_right(tails, t)
        if j == len(tails):
            tails.append(t)
            idx.append(i)
        else:
            tails[j] = t
            idx[j] = i
        back[i] = idx[j - 1] if j else -1
    out, k = [], idx[len(tails) - 1]
    while k != -1:
        out.append(pairs[k])
        k = back[k]
    out.reverse()
    return out


# The fastest speech worth believing, in Telugu characters per second. The measured median for
# this material is about 12.7, so 25 is roughly double — - generous for an excited speaker and
# still nowhere near the impossible.
# How much faster than its own average this material is ever allowed to be, between two
# anchors. Derived per resource rather than fixed: the ceiling that matters is relative to how
# fast the speaker actually talks, and a number tuned on one recording is a number wrong on the
# next. 1.2 was chosen by measurement — see rate_ceiling().
RATE_SLACK = 1.2


def rate_ceiling(rows, total, slack=RATE_SLACK):
    """The fastest plausible characters-per-second for THIS recording.

    Transcript characters over audio seconds is the average rate, and it needs no alignment to
    compute — it is a property of the two inputs. The ceiling is that average times a little
    slack, because a real stretch of speech runs somewhat above average and nothing runs far
    above it.

    Measured, not guessed. Sweeping the ceiling and scoring each result by cutting 22 spans out
    of the audio and recognising them blind: a ceiling of 25 c/s scored 69.6% mean similarity
    with 5 of 22 lines under 40%, while 15 c/s scored 82.4% with none. This recording averages
    12.3 c/s, so the winning ceiling was 1.2x its average — generous enough for fast speech,
    tight enough to reject the anchor pairs that ask 349 characters to be spoken in a tenth of
    a second.
    """
    chars = sum(len(''.join(c for c in r['te'] if TELUGU.match(c))) for r in rows)
    if not total or not chars:
        return 25.0
    return max(6.0, chars / total * slack)


def plausible_chain(blocks, max_cps):
    """Keep the largest set of match blocks that could describe real speech.

    Blocks are (transcript position, size, start time, end time) — normalised, so blocks found
    by DIFFERENT recognitions of the same audio can be pooled and competed against each other.
    Two runs disagree about spelling in different places, so their anchors land in different
    places, and the union covers more of the transcript than either alone. Where they overlap
    the chain simply cannot take both, since it requires the next block to begin after the
    previous one ends.

    THE FAILURE THIS EXISTS TO STOP
    Recognition skips things — it loses the thread, and the next block it matches sits almost
    at the same second as the last one while the transcript between them holds hundreds of
    characters. Interpolating across that pair asks 349 characters to be spoken in 0.11
    seconds, and the lines between collapse to nothing. Eight such pairs in this one recording,
    and they caused all 24 of the zero-length spans.

    Being monotone is not enough to be possible, which is why an ordering filter missed this.
    The constraint is a rate: characters between two blocks over seconds between them must stay
    under MAX_CPS. Blocks are chosen to maximise matched characters subject to it — a
    longest-path walk, so dropping one bad block never costs the rest of the file.
    """
    blocks = sorted(blocks, key=lambda b: (b[0], b[2]))
    n = len(blocks)
    if not n:
        return []
    best = [0] * n
    prev = [-1] * n

    def ok(i, j):
        bi, si, _tsi, tei = blocks[i]
        bj, _sj, tsj, _tej = blocks[j]
        if bj < bi + si:                       # overlapping transcript positions
            return False
        gap_chars = bj - (bi + si)
        gap_time = tsj - tei
        if gap_time < -0.05:
            return False
        return gap_time >= gap_chars / max_cps - 0.25

    for j in range(n):
        best[j] = blocks[j][1]
        for i in range(j):
            if best[i] + blocks[j][1] > best[j] and ok(i, j):
                best[j] = best[i] + blocks[j][1]
                prev[j] = i
    tail = max(range(n), key=lambda i: best[i])
    chain = []
    while tail != -1:
        chain.append(blocks[tail])
        tail = prev[tail]
    chain.reverse()
    return chain


def blocks_of(words, tr_c, min_block):
    """One recognition -> normalised match blocks against the transcript characters."""
    asr_c, asr_t = _char_timeline(words)
    if not asr_c:
        return []
    sm = difflib.SequenceMatcher(None, asr_c, tr_c, autojunk=False)
    out = []
    for a, b, size in sm.get_matching_blocks():
        if size >= min_block:
            out.append((b, size, asr_t[a], asr_t[a + size - 1]))
    return out


def align_from_asr(rows, runs, total, min_block=6, slack=RATE_SLACK):
    """Time every line by matching recognised characters against transcript characters.

    Character level, not word level: a Telugu word carries its postpositions and case endings
    inside it, so వాళ్ళకి and వాళ్ళు never match as tokens while sharing a stem that matches
    exactly. autojunk must be off — it discards any character occurring in over 1% of a long
    sequence, which in Telugu is most of the alphabet.

    THE MAPPING IS POSITION -> TIME, NOT LINE -> TIME
    Every matched character supplies a pair: this far into the transcript, that second of
    audio. Fitting a monotone curve through those pairs and reading each line's boundary off
    it uses all the evidence and needs no per-line bookkeeping.

    The first attempt did keep that bookkeeping — a line's start became its first matched
    character and its end its last — and it was wrong in a way that looked right. A line
    anchored by a single six-character match collapsed to the width of the MATCH rather than
    the width of the LINE: line 110 was given 0.4 seconds for forty characters. "91 of 141
    lines anchored" was true and told you nothing, because it counted anchors rather than
    checking the spans they produced. Cutting the audio at each span and recognising it again
    is what caught it.
    """
    tr_c, tr_line = _line_chars(rows)
    max_cps = rate_ceiling(rows, total, slack)
    blocks = []
    for words in runs:
        blocks += blocks_of(words, tr_c, min_block)
    if not blocks:
        return None, 'no matching character runs'
    chain = plausible_chain(blocks, max_cps)
    # A block's characters are spread evenly across its own span; the block is contiguous in
    # both sequences, so this is exact up to the recognition's own word timing.
    pts = []
    for b, size, ts, te in chain:
        step = (te - ts) / max(size - 1, 1)
        for k in range(size):
            pts.append((b + k, ts + step * k))
    if len(pts) < 20:
        return None, f'only {len(pts)} matched characters survived the rate check'

    # Where each line begins, measured in transcript characters.
    at = [0]
    for r in rows:
        at.append(at[-1] + len(''.join(c for c in r['te'] if TELUGU.match(c))))

    def time_at(pos):
        """Monotone piecewise-linear read-off, extrapolating at both ends."""
        lo, hi = 0, len(pts) - 1
        if pos <= pts[0][0]:
            p0, p1 = pts[0], pts[min(1, hi)]
            if p1[0] == p0[0]:
                return p0[1]
            rate = (p1[1] - p0[1]) / (p1[0] - p0[0])
            return max(0.0, p0[1] - (p0[0] - pos) * rate)
        if pos >= pts[hi][0]:
            p0, p1 = pts[max(hi - 1, 0)], pts[hi]
            if p1[0] == p0[0]:
                return p1[1]
            rate = (p1[1] - p0[1]) / (p1[0] - p0[0])
            return min(total, p1[1] + (pos - p1[0]) * rate)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if pts[mid][0] <= pos:
                lo = mid
            else:
                hi = mid
        p0, p1 = pts[lo], pts[hi]
        if p1[0] == p0[0]:
            return p0[1]
        f = (pos - p0[0]) / (p1[0] - p0[0])
        return p0[1] + f * (p1[1] - p0[1])

    bounds = [time_at(p) for p in at]
    bounds[0] = min(bounds[0], bounds[1] if len(bounds) > 1 else 0.0)
    bounds[-1] = total
    for i in range(1, len(bounds)):
        if bounds[i] < bounds[i - 1]:
            bounds[i] = bounds[i - 1]

    # A minimum span is a constraint on the SHARED boundary, not on one row's end. Three times
    # now the same bug: widen row i's end past row i+1's start and the timeline overlaps, because
    # both read the same number. Push the boundary itself forward and let it cascade; 141 lines
    # at 0.35 s is 49 seconds against 946, so the cascade cannot run out of room.
    for i in range(1, len(bounds)):
        if bounds[i] < bounds[i - 1] + MIN_SPAN:
            bounds[i] = min(bounds[i - 1] + MIN_SPAN, total)
    for i in range(len(rows)):
        rows[i]['start'], rows[i]['end'] = f'{bounds[i]:.2f}', f'{bounds[i + 1]:.2f}'
        if rows[i]['status'] in ('', 'todo', 'est'):
            rows[i]['status'] = 'timed'
    hit = len({tr_line[p] for p, _ in pts})
    return (hit, max_cps), None


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

    if args.asr:
        if not audio:
            raise SystemExit('no audio file to recognise')
        total = audio_duration(audio)
        runs = [asr_words(args.slug, audio, model=args.model, force=args.reasr)]
        runs += extra_runs(args.slug)
        got, err = align_from_asr(rows, runs, total, min_block=args.min_block,
                                  slack=args.slack)
        if err:
            raise SystemExit(f'ASR alignment failed: {err}')
        hit, max_cps = got
        write_segments(args.slug, rows)
        print(f'{args.slug}: {sum(len(r) for r in runs)} words recognised '
              f'across {len(runs)} recognition{"" if len(runs) == 1 else "s"}')
        print(f'  {hit}/{len(rows)} lines have characters matched in the audio; the rest are')
        print(f'  interpolated between the nearest matches, by character count.')
        print(f'  rate ceiling {max_cps:.1f} chars/sec ({args.slack}x this recording\'s average)')
        print('  Anchored lines rest on evidence. Verify before trusting the whole file:')
        print('  cut a few spans out and recognise them again — counting anchors proved nothing.')
        return

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

    if not args.proportional:
        runs, total = speech_runs(audio, noise=args.noise, gap=args.gap)
        if len(runs) >= max(4, len(rows) // 4):
            mids = []
            for (a1, b1), (a2, _b2) in zip(runs, runs[1:]):
                mids.append((b1 + a2) / 2)
            n = align_anchored(rows, runs, mids)
            write_segments(args.slug, rows)
            speech = sum(b - a for a, b in runs)
            print(f'{args.slug}: {os.path.basename(audio)} is {dur / 60:.1f} min')
            print(f'  {len(runs)} speech runs, {len(mids)} pauses, '
                  f'{speech / dur * 100:.0f}% speech')
            print(f'  {n} segments spread over the speech and snapped to pauses '
                  f'({len(rows)} segments vs {len(mids)} pauses)')
            print('  Still derived, not measured — good to the nearest pause, which for a')
            print('  turn-per-line transcript is usually the right one.')
            return
        print(f'  only {len(runs)} speech runs found — falling back to plain character weight')

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


# ---------------------------------------------------------------- build

def gloss_table():
    """Telugu surface form -> (gloss, pos), from every source in the project that has one."""
    out = {}
    def take(path, te_col, gloss_col, pos_col):
        if not os.path.exists(path):
            return
        with open(path, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                te = (r.get(te_col) or '').strip()
                g = (r.get(gloss_col) or '').strip()
                if te and g and te not in out:
                    out[te] = (g, (r.get(pos_col) or '').strip())
    take(os.path.join(ROOT, 'ministories', 'vocab.tsv'), 'te', 'gloss', 'pos')
    take(os.path.join(ROOT, 'intensive', 'vocab.tsv'), 'te', 'gloss', 'pos')
    take(os.path.join(ROOT, 'data', 'master_words.tsv'), 'telugu', 'english', 'pos')
    return out


def cmd_build(args):
    """segments.tsv -> reader/data/<slug>.js, in the shape the reader already consumes.

    Word identity is the whole reason this is short. ids.guid('W', form) is what both existing
    corpora already key their lexicons by, so a word met here mints the guid it already has —
    which means the level you gave it in a mini story, its SRS date and its pronunciation clip
    all carry over with no mapping table. A corpus-local id would have thrown that away and
    presented every familiar word as new.
    """
    meta = load_meta(args.slug)
    rows = [r for r in read_segments(args.slug) if r['kind'] == 'te' and r['te'].strip()]
    if not rows:
        raise SystemExit(f'nothing to build — run segment first')
    if meta.get('rights') == 'local-only' and not args.force:
        raise SystemExit(
            f'meta.json says rights=local-only, so this dataset is not built for the site.\n'
            f'  reader/data/ is committed and GitHub Pages serves what is committed.\n'
            f'  If the recording really is yours to publish, set "rights" and re-run;\n'
            f'  to build it anyway for local use only, pass --force.')

    glosses = gloss_table()
    # First pass: count every Telugu form so the lexicon can carry an occurrence count.
    counts = Counter()
    for r in rows:
        for tok in TOKEN.findall(r['te']):
            if TELUGU.search(tok):
                counts[tok] += 1

    lex, idx_of = [], {}
    for form in counts:
        g, pos = glosses.get(form, ('', ''))
        idx_of[form] = len(lex)
        entry = {'te': form, 'g': guid('W', form), 'n': counts[form],
                 'f': 1, 'o': len(lex)}
        if g:
            entry['en'] = g
        if pos:
            entry['p'] = pos
        lex.append(entry)

    lines = []
    for r in rows:
        toks = []
        for tok in TOKEN.findall(r['te']):
            if TELUGU.search(tok):
                toks.append([tok, 'w', idx_of[tok]])
            else:
                toks.append([tok, 'p', -1])
        line = {'g': r['guid'], 'p': 'discussion', 't': toks}
        if r['en'].strip():
            line['en'] = r['en'].strip()
        if r['start']:
            line['s'] = round(float(r['start']), 2)
        if r['end']:
            line['e'] = round(float(r['end']), 2)
        lines.append(line)

    audio_rel = ''
    if args.audio:
        audio_rel = args.audio
    else:
        found = find_one(args.slug, AUDIO_EXT, 'audio')
        if found:
            audio_rel = f'../{os.path.relpath(found, ROOT)}'

    story = {'num': 1, 'title': {'te': meta.get('title', args.slug),
                                 'en': meta.get('title_en', meta.get('title', args.slug))},
             'lines': lines}
    if audio_rel:
        story['audio'] = audio_rel
        dur = None
        f2 = find_one(args.slug, AUDIO_EXT, 'audio')
        if f2:
            dur = audio_duration(f2)
        if dur:
            story['dur'] = round(dur, 2)

    data = {
        'generated': __import__('datetime').date.today().isoformat(),
        'source': meta.get('title', args.slug),
        'tag': meta.get('tag') or args.slug.replace('-', '')[:6],
        'unit': meta.get('unit', 'episode'),
        'lex': lex,
        'stories': [story],
    }
    var = args.var or (re.sub(r'[^A-Za-z0-9]', '_', args.slug).upper() + '_DATA')
    out = os.path.join(ROOT, 'reader', 'data', f'{args.slug}.js')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f'/* Generated by tools/import_resource.py. Do not edit. */\n')
        f.write(f'window.{var} = ')
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')

    glossed = sum(1 for l in lex if l.get('en'))
    tokens = sum(counts.values())
    known_tok = sum(c for w, c in counts.items() if w in glosses)
    print(f'{args.slug}: wrote {os.path.relpath(out, ROOT)}')
    print(f'  {len(lines)} lines, {tokens:,} tokens, {len(lex):,} word forms')
    print(f'  {glossed:,} forms have a definition ({known_tok / tokens * 100:.1f}% of tokens)')
    print(f'  window.{var}  tag={data["tag"]}  unit={data["unit"]}')
    if audio_rel:
        print(f'  audio {audio_rel}')
    print()
    print('  Add to reader/index.html, before assets/app.js:')
    print(f'    <script src="data/{args.slug}.js"></script>')
    print(f'  and to the SETS line in reader/assets/app.js:  window.{var}')


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
    p.add_argument('--lines', action='store_true',
                   help='one segment per transcript line — for a turn-per-line transcript '
                        'with no blank lines and patchy punctuation')
    p.add_argument('--max-chars', type=int, default=140,
                   help='longest segment when punctuation gives no break (default 140)')
    p.set_defaults(fn=cmd_segment)

    p = sub.add_parser('align', help='give segments timings, from captions or by estimate')
    p.add_argument('slug')
    p.add_argument('--proportional', action='store_true',
                   help='plain character weight — skip captions and pause snapping')
    p.add_argument('--noise', type=int, default=-40, help='silence threshold in dB')
    p.add_argument('--gap', type=float, default=0.35, help='shortest gap counted as a pause')
    p.add_argument('--asr', action='store_true',
                   help='recognise the audio and align the transcript to it — the only mode '
                        'that consults the audio rather than estimating from text')
    p.add_argument('--model', default=ASR_MODEL, help='faster-whisper model')
    p.add_argument('--reasr', action='store_true', help='re-recognise, ignoring the cache')
    p.add_argument('--min-block', type=int, default=6,
                   help='shortest matching character run treated as an anchor')
    p.add_argument('--slack', type=float, default=RATE_SLACK,
                   help='how far above its own average rate the audio may run between two '
                        'anchors (1.2 measured best; raise for uneven speech)')
    p.set_defaults(fn=cmd_align)

    p = sub.add_parser('analyze', help='vocabulary coverage report')
    p.add_argument('slug')
    p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser('build', help='segments.tsv -> reader/data/<slug>.js')
    p.add_argument('slug')
    p.add_argument('--var', default='', help='window global to assign (default <SLUG>_DATA)')
    p.add_argument('--audio', default='', help='audio path as the reader should request it')
    p.add_argument('--force', action='store_true',
                   help='build even though rights=local-only (for local use)')
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser('status', help='every resource and how far along it is')
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
