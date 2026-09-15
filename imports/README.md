# Importing a new resource

One directory per resource, all the same shape, one tool that walks it:
[`tools/import_resource.py`](../tools/import_resource.py).

This exists for what comes after the Mini Stories — a podcast episode, an audiobook chapter, a
YouTube video, a recorded conversation. Anything that is audio plus a transcript.

## The commands

```bash
python3 tools/import_resource.py new telugu-podcast-01 --title "Show name, ep 1" --unit episode
# drop the audio and the transcript into imports/telugu-podcast-01/
python3 tools/import_resource.py segment telugu-podcast-01 --from-captions
python3 tools/import_resource.py align   telugu-podcast-01      # only without captions
python3 tools/import_resource.py analyze telugu-podcast-01
python3 tools/import_resource.py build   telugu-podcast-01 --audio "media/telugu-podcast-01.m4a"
python3 tools/import_resource.py status
```

`segment --from-captions` does the alignment too, so there is usually no separate `align` step.

## Pick the right segmenter

Three transcript shapes, three readers, and choosing wrong is the difference between 141
readable lines and one unreadable block:

| the transcript looks like | use |
|---|---|
| blank lines between paragraphs, punctuation throughout | `segment` |
| one utterance per line, no blank lines, patchy punctuation | `segment --lines` |
| you have captions instead | `segment --from-captions` |

A generated discussion is almost always the middle case. `segment` warns when it produces
mostly unpunctuated segments, which is the signal to switch.

## Get captions if you possibly can

This is the single thing that decides whether the import is good or merely usable.

| what you have | what you get |
|---|---|
| captions (`.vtt`/`.srt`) | real sentence breaks, exact timestamps |
| transcript, turn per line | real line breaks, timings snapped to detected pauses |
| transcript, punctuated prose | real sentence breaks, timings snapped to detected pauses |
| neither | one long block. Fix the transcript rather than importing this |

```bash
yt-dlp --write-auto-subs --sub-lang te --skip-download <url>
yt-dlp -x --audio-format mp3 <url>
```

Without captions, `align` detects pauses in the audio and snaps segment boundaries to them,
spreading segments over the *speech* by character weight so a long pause no longer pushes
every later segment late. On a turn-per-line transcript this lands close: the chapter-1
discussion gave 147 speech runs and 146 pauses against 141 lines, and every boundary fell on a
real pause. Derived, not measured — but bounded, because a mistake cannot drag the next forty
segments with it.

Two knobs, and the defaults are tuned for generated audio: `--noise -40` because loudness
compression leaves no true digital silence, and `--gap 0.35` because the target is a turn
boundary rather than the stop before a consonant. `--proportional` forces the old flat
character-weight estimate, which drifts and is marked `status=est`. A measured timing always
overwrites an estimate and clears the flag.

One trap, recorded because it cost an hour: ffmpeg's `silencedetect` reports at INFO level, so
running it under `-v error` returns zero gaps on any input and looks exactly like audio with no
pauses in it.

## `align --asr` — the only mode that consults the audio

Everything above estimates timings from the text and never listens. That is a real limit, and
it is worth being precise about how it failed: the chapter-1 discussion, aligned by pause
snapping, was off by a **median 4.33 s**, with **51 of 141 lines a full line or more out of
place**. It measured well at the time because the check — how closely duration tracked
character count — was the aligner's own assumption restated. A number like that can only
confirm itself.

```bash
python3 -m pip install faster-whisper
python3 tools/import_resource.py align <slug> --asr
```

Recognition supplies the missing half. What it hears is wrong in detail — `సాధారనంగా` for
`సాధారణంగా` — but it is wrong at a known second, which is all an anchor has to be. Matching is
at character level because a Telugu word carries its case endings inside it: `వాళ్ళకి` and
`వాళ్ళు` never match as tokens while sharing a stem that matches exactly. Every matched
character gives a position-to-time pair, and each line's boundary is read off the curve fitted
through them.

Notes worth keeping:

- **Model size is not negotiable.** `small` returned 19 Telugu words out of 98 for two and a
  half minutes, the rest nonsense and stray Persian. `large-v3-turbo` returned 138 of 138, at
  roughly real time. Below turbo, Telugu is not worth attempting.
- **Recognitions pool.** Save a second run as `asr_words2.json` and it is used too. Two runs
  mishear different words, so each anchors where the other failed: 84 anchored lines became
  105, and measured accuracy rose from 64% to 70%.
- **The rate ceiling does the real work.** Recognition skips stretches, and the next block it
  matches can sit a tenth of a second after the last while the transcript between them holds
  349 characters. Interpolating across that crushes those lines to nothing. Anchor pairs are
  therefore rejected unless the implied speed stays under `rate_ceiling()` — the recording's
  own average times `--slack` (1.2). Sweeping that ceiling and scoring each result blind: 25
  chars/sec gave 69.6% mean similarity with 5 of 22 lines under 40%; the derived 14.7 gave
  **82.4% with none**.
- **Verify by re-recognising spans, never by counting anchors.** "91 of 141 lines anchored" was
  true while line 110 held 0.4 seconds of audio for forty characters. Cut a span out, recognise
  it blind, compare: that is the only check here that has ever caught anything.

## `annotate` — loading a generated annotation file

If you have a per-line annotation of the transcript (meanings, morphology, translations),
`annotate` loads it into the resource:

```bash
python3 tools/import_resource.py annotate <slug> path/to/annotations.json
```

It fills the `en` column in `segments.tsv` from the per-line translations, and writes a word
registry to `imports/<slug>/vocab.tsv` — one row per sense, commonest sense first, up to three
per form. `build` then prefers that registry over the project-wide tables, because it was
written for these words in these sentences rather than for the form wherever it appears. On the
chapter-1 discussion this took definitions from 305 of 1,022 forms to all 1,022, and English
from none of 141 lines to all of them.

**What it refuses to take.** An annotator of this kind proposes *repairs* — corrected Telugu
where it believes the transcript is wrong, `నిజే` read as `నిజమే`. On this file 45 of 141
translations rested on such a proposed reading rather than on the words actually present.
Writing those back would replace what was said with what a model guessed was meant, which is
the one thing this project does not do with Telugu. The proposals are recorded in the segment's
`notes` column, where they can inform a correction you make deliberately; the transcript is
left alone.

It also refuses an annotation whose lines do not match the segments, since every line number in
it would then point at the wrong words. Every sense lands as `status=draft`, so the reader
prints "not yet checked by a native speaker" beneath it — which the annotation says of itself,
its own verification note reporting contextual analysis with no dictionary check, no audio and
no native review.

## What `analyze` tells you

It writes `report.md` next to the segments:

- **How much of it you can already reach** — the share of tokens whose word form this project
  already glosses. Counted by surface form rather than lemma, so it understates; treat it as a
  floor.
- **The new words the resource can actually teach** — those occurring eight or more times, the
  floor for picking a word up from context alone. Everything under that count needs a drill,
  which is what the vocabulary drill in the reader is for.

That second number is the one to decide on. The study-plan analysis found only 346 of 4,493
words in the existing corpora were met eight or more times — a resource where that number is
small is a reading exercise, not a vocabulary source, and it is better to know which you are
buying before you spend an evening importing it.

## Rights — answer this first

`meta.json` carries a `rights` field, and the reason it is asked at creation rather than at
publish time is that the answer changes whether the work is worth doing at all.

| value | meaning |
|---|---|
| `local-only` | someone else's copyrighted audio. Study it from a local checkout; it never reaches the Pages build |
| `ours` | our own recording, or our own translation of a freely-licensed transcript |
| `open` | public domain or an explicitly permissive licence |

The contents of each resource directory are gitignored regardless — that is third-party audio
and a third-party transcript. Only this README and the tool are committed. The same call the
rest of the repo already makes for `sources/local/`, `ministories/source/` and
`translate/source/`; see the reasoning in [`.gitignore`](../.gitignore).

Worth knowing which way this cuts: GitHub Pages serves only what is committed, so a
`local-only` resource works on this machine and is simply absent on the phone. That is the
intended behaviour, not a bug to work around.

## Where the pieces live

```
imports/<slug>/
  meta.json        title, unit noun, kind, source, rights
  START_HERE.txt   written by `new` — what to drop in
  transcript.txt   you provide
  <slug>.mp3       you provide
  <slug>.vtt       you provide, if you can get it
  segments.tsv     generated — guid, idx, kind, te, en, start, end, notes, status
  report.md        generated by `analyze`
```

`build` writes `reader/data/<slug>.js` and prints the two lines to add — a `<script>` tag in
`reader/index.html` and the global in the `SETS` array in `reader/assets/app.js`. Put the audio
somewhere the reader can request it (`reader/media/<slug>.m4a`) and pass that path as
`--audio`; re-encoding speech to mono 64k first took the chapter-1 file from 30 MB to 7.9 MB.
`build` refuses to write while `rights` is `local-only` unless you pass `--force`.

Word identity is shared across every corpus for free: `ids.guid('W', form)` is the key both
existing corpora already use, so a word you have already rated keeps its level, its SRS date
and its pronunciation clip the moment it turns up in a new resource. Per-word *audio* for new
words is the one thing not available — that needs forced alignment, not pause detection.

`segments.tsv` is the workspace. Re-running `segment` carries the `en`, `notes` and `status`
columns forward by GUID, so re-segmenting cannot eat a translation — the same contract
`hp_segment.py` and `build_master.py` hold to. Editing the transcript *does* invalidate the
segments it changed, deliberately: a GUID is derived from the text, so an edited sentence is a
new segment and its old translation is reported as no longer matching rather than silently
attached to different words.
