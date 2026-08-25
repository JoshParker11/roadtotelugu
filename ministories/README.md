# LingQ Mini Stories → Telugu

**[BRIEF.md](BRIEF.md) — start here if picking this up cold**, especially for a fresh model or
session. It has the current status, the open questions, and the mistakes a cold start makes by
default. **[PIPELINE.md](PIPELINE.md)** is the operating manual from here to done — the
per-story loop, the word-registry plan, and how deploys reach the phone. **[READER_BRIEF.md](READER_BRIEF.md)**
is the build spec the reader was built to (historical now — the reader exists at `../reader/`).

The 62 LingQ Mini Stories, translated into Telugu and given real audio, read in a personal
reading tool modeled on LingQ (built on the existing `../STUDY/` reader — see BRIEF.md §7, not
Language Reactor — see BRIEF.md §6). This is the comprehensible-input half of the project;
`../translate/` (Harry Potter) is the other half, and the two are deliberately different in
scale and purpose.

## Why this, and why now

Words stick when they arrive in a context worth remembering. The problem at the very beginning is
that nothing is comprehensible yet, so there is no context to arrive in — which is the usual
reason beginners bounce off comprehensible input and conclude it is not for them. The Mini
Stories are the standard answer: sixty short texts built so that the *n*th sentence of part 1
comes back as the *n*th question in part 2 and again re-personed in part 3. The repetition
manufactures the context that the language cannot supply yet.

Sixty-two lessons rather than sixty: story 1 is split into `1a` / `1b` / `1c` on LingQ, because
the first one is where the format has to be taught as well as the content.

## Provenance and what may be committed

LingQ wrote the English Mini Stories and released them for communities to translate into
languages LingQ does not yet support — which is exactly this case, since LingQ has no Telugu.
Thirty-nine-odd languages have been done on that basis, coordinated through a community
spreadsheet (not an official LingQ project). **No formal licence text was found**, only the
consistent practice and LingQ's own encouragement, so treat "public domain" as well-established
custom rather than a document you could point a lawyer at.

The practical split, which is also the cautious one:

| | |
|---|---|
| `source/api/` | Raw JSON pulled from LingQ with a personal account key. **Gitignored** — it is their payload, fetched under someone's login, and nothing here needs it after segmenting |
| `source/paste/` | Hand-pasted English, same reasoning. **Gitignored** |
| `work/*.tsv` | English sentence + our Telugu, side by side. **Committed** — redistributing the translation is the entire point of the community project |
| `CATALOG.tsv`, tooling | Ours. Committed |

If LingQ ever objects, `work/` moves to the gitignore and nothing else changes.

Someone already started Telugu on the community sheet — initial drafts of stories 1, 2 and 3, all
marked as still needing an edit pass, none with audio. Worth a look before doing those three, not
worth waiting for.

## The unit is the sentence — the opposite call from the novel

`../translate/` segments Harry Potter by **paragraph**, because a meaning-for-meaning translation
has to move information between sentences and locking the sentence count would force a
word-for-word rendering.

Here that inverts. A Mini Story is a drill wearing a story as a costume: the story is told, retold
with the person shifted, then interrogated line by line, and that three-way correspondence **is**
the teaching content. The corpus confirms it — across all 62 lessons the story and retell parts
contain **571 sentences each**, exactly one retold line per original line. Translate at paragraph level and the correspondence
dissolves: you get pleasant Telugu that has stopped teaching anything.

Sentence-level is also what the downstream needs — Language Reactor aligns audio to sentence-ish
segments, so the unit we translate is the unit that gets a timestamp and a click-to-look-up.

## The schema

`work/<id>.tsv`, one file per lesson:

| column | |
|---|---|
| `guid` | content-derived from the English sentence (`tools/ids.py`). Editing the English orphans its translation, which is correct — an edited source invalidates what was translated from it |
| `num` | story number, 1–60 |
| `part` | `meta` / `story` / `retell` / `questions` — **the pedagogically load-bearing column**, see below |
| `seq` | position within the part |
| `en` / `te` | source and translation |
| `notes`, `status` | `todo` → `draft` → `query` → `checked` → `done`, same ladder as the novel |

`part` is a column rather than a comment because a translator who cannot see which part a line
belongs to will quietly flatten a question into a statement or drop the person shift in part 3 —
and neither error is visible to a reader who cannot yet read Telugu. As a column, a checker can
assert it.

`meta` is LingQ's own scaffolding — the `Story Twelve:` title and the fixed line introducing the
retell. Those are keyed on their text alone rather than on story number, so the line that opens
the retell in **all 60 combined lessons carries one shared guid**: agree its Telugu once and it
propagates everywhere instead of being re-decided sixty times.

The part boundaries are prose, not fields. There is no `Questions` heading anywhere in the 62
lessons; the section is detected by its ordinal-prefixed restatements (`One:`, `Two:`). Titles
appear as `Story Two:`, `Story 10 -` and `Story Fifty-nine -`, and lesson 21 has no title line at
all — all handled, all learned from the data rather than assumed.

## The pipeline

```bash
export LINGQ_API_KEY=...              # https://www.lingq.com/accounts/apikey/
python3 tools/ms_fetch.py --probe     # one lesson, print its shape, write nothing
python3 tools/ms_fetch.py             # all 62 -> source/api/*.json
python3 tools/ms_segment.py           # -> work/*.tsv
python3 tools/ms_segment.py --report  # coverage: fetched, pasted, segmented, missing
```

`~/.zshrc` is only read by *interactive* shells, so a key exported there is invisible to scripted
runs. Either put it in `~/.zshenv` or `source ~/.zshrc` in the same command.

Two findings about the v3 API, both of which cost a round of guessing:

- `collections/<id>/` is **metadata only** — it reports `lessonsCount: 62` and never lists them.
  The list is at `collections/<id>/lessons/`, paginated.
- A lesson has **no plain-text field**. The text is in `tokenizedText`: paragraphs → sentence
  dicts carrying `text`, `tokens` and a two-element `timestamp` into LingQ's English audio. Those
  timestamps cannot transfer to Telugu TTS, whose sentences will have different durations.

Fetching and parsing are separate on purpose. The v3 API is undocumented — `lingq.com/apidocs`
covers v2 and 404s for the rest — so the field names in `ms_segment.parse_api()` are a guess that
will be wrong at least once. Dumping raw first means a wrong guess costs a re-run over local
files instead of 63 more requests against someone else's rate limiter. Run `--probe` and read the
shape before the full run.

**No key, or the API turns out to be a dead end:** paste each lesson into
`source/paste/<id>.txt` (ids in `CATALOG.tsv`) and run `ms_segment.py`. The parser takes
`## story` / `## questions` / `## retell` headers, or falls back to blank-line-separated blocks in
that order. It strips LingQ's line numbering and splits sentences. This path needs no key and no
cooperation from LingQ.

Re-running the segmenter carries `te` / `notes` / `status` forward by guid. Same contract as
`hp_segment.py`: a rebuild that silently discards hand-entered work is the most expensive bug in
this repo, because nothing looks wrong until much later.

## QC

```bash
python3 tools/ms_names.py --rejected   # rebuild names.tsv; show what was filtered out and why
python3 tools/check_ms.py --num 1      # check one story
python3 tools/check_ms.py --warn       # whole corpus, including advisory findings
```

`check_ms.py` cannot tell you the Telugu is good. It tells you the Telugu is consistent with
itself and with the English, which is a different and much weaker claim — but it is the only one
a script is entitled to make, and it covers the errors you cannot see. Exit code is non-zero on
errors, so it can gate anything.

It checks: status/schema integrity · `query` rows actually carry their question · no Latin script
left in the Telugu · question marks preserved from English · names present in the translation ·
numbers and times preserved · question ordinals contiguous (bar lesson 2) · shared boilerplate
translated identically everywhere · and the one that earns its keep:

**story vs retell divergence.** Sentence *n* of the story and its counterpart in the retell should
differ *only* in person — the pronoun and the verb ending. Anything else that differs is one word
translated two ways, ten lines apart. The first translated story contained exactly that
(`చేసి` in the story, `చేసుకుని` in the retell); a human caught it by luck, which does not scale
to 2,805 segments.

Three things about that check were wrong when first written, and only fault injection found them:

- It paired rows **per file**, so story 1 — split across 1a/1b/1c — was skipped entirely. It is
  the one lesson where the bug actually was. Pair by story number, never by file.
- It paired rows **by position**, which breaks the moment the retell has a different line count
  (story 1 has ten and nine). It now aligns on the English, which both parts carry.
- It inferred "same stem" by chopping a syllable, which cannot distinguish `వంటవాడు`/`వంటవాడిని`
  (a real person shift) from `చేసి`/`చేసుకుని` (a real inconsistency). Person endings are a closed
  list; they are now written out rather than guessed.

Run it against deliberately broken data before trusting it. A checker that reports zero on clean
input has demonstrated nothing.

`ms_names.py` rebuilds `names.tsv` and is worth reading for the same reason: "grep for capitals"
produced 60% noise, and the two tests that fix it (does the word ever appear lowercase; is it
ever not sentence-initial) both fail on Title Case lesson headings, which are therefore excluded.

## The reader

The LingQ-style reading application from [READER_BRIEF.md](READER_BRIEF.md) is built: `../reader/`
(static, no framework, no backend), the primary entry from the site's home page. See
DECISIONS.md #12 for what it shares with the old `../STUDY/` reader and why it is a separate
page rather than a rewrite of that one.

```bash
python3 tools/build_ms_reader.py        # bake translated stories -> reader/data/ministories.js
python3 tools/ms_lr_export.py --num N   # continuous per-story audio the reader seeks within
python3 tools/ms_audio.py --words       # optional: per-word pronunciation clips (Azure key)
python3 tools/serve.py                  # then open http://localhost:8123/reader/
```

Re-run `build_ms_reader.py` after translating a story (and `ms_lr_export.py` after voicing it);
the story appears in the reader automatically. Word status lives in the browser's localStorage,
keyed by the same guids as everything else; the vocabulary queue's backup drawer remains the way
to move marks between devices.

## Still to build

- Translation pass (see `../translate/STYLE.md` — register and dialect carry over unchanged;
  the anchor and stitching conventions deliberately do **not**, see DECISIONS.md #1)
## Audio via HyperTTS

Two ways to get `ministories/audio/<guid>.mp3` — same output layout either way, so nothing
downstream cares which one produced a given file. See DECISIONS.md #8 for why Azure's
`te-IN-ShrutiNeural`/`te-IN-MohanNeural` specifically, and why not NotebookLM, Google Cloud TTS
(no Telugu voices at all), Language Reactor's own TTS, ElevenLabs, or Gemini TTS.

**Direct (`tools/ms_audio.py`).** Your own Azure Speech resource, fully scripted, no manual step.

**Through HyperTTS Pro (`tools/ms_hypertts_export.py` / `ms_hypertts_import.py`).** Uses the
subscription you already pay for — Pro already includes Azure and needs no separate account,
because the whole point of Pro is that Vocab.ai holds the provider credentials, not you. There is
no personal key to extract; that's by design, not a gap. The cost is one manual pass through the
Anki GUI per batch instead of an unattended script:

```bash
python3 tools/ms_hypertts_export.py            # -> ministories/hypertts_export.tsv
```

1. In Anki, **Import File** → the exported TSV → create/target a note type with four fields, in
   this order: `guid`, `telugu`, `audio`, `english`. `guid` and `telugu` are Anki's Front/Back
   equivalents; `audio` stays empty until HyperTTS fills it; `english` just rides along so you can
   see what you're listening to.
2. Open **HyperTTS** → batch generation. Source field `telugu`, target field `audio`, voice a
   Telugu one (`te-IN-ShrutiNeural` or `te-IN-MohanNeural` if Pro exposes Azure's voice names
   directly — confirm which provider Pro is actually routing to before assuming it's Azure). Run
   it on the whole imported batch.
3. **File → Export → Notes in Plain Text**, same note type, all four fields, tab-separated.
4. ```bash
   python3 tools/ms_hypertts_import.py path/to/that/export.txt
   ```
   Copies each `[sound:...]` file out of Anki's `collection.media` into
   `ministories/audio/<guid>.mp3` by matching the `guid` column — Anki's media folder is never
   modified, only read from.

Delete the scratch Anki deck once the audio is copied out; it has served its purpose and the
guid-keyed files in `ministories/audio/` are the thing that matters from here on.

## Language Reactor import

```bash
python3 tools/ms_lr_export.py --num 1     # -> ministories/lr/story_01.{mp3,te.srt,en.srt}
```

One continuous recording per story (title → story → retell-intro → retell → questions, silence
inserted at sentence and section boundaries) plus **three** subtitle files with identical
timestamps: `story_NN.te.srt`, `story_NN.en.srt`, and `story_NN.bilingual.srt` (both languages,
two lines per cue, in one file).

Which one to use depends on what the actual target accepts. Language Reactor's "Media file" tool
was tried directly and takes exactly one subtitle upload — its Study/Native language picker looks
like it drives the tool's *own* translation for a second line, not a slot for a second file, which
would silently replace the checked English with a fresh machine back-translation of the Telugu.
`.bilingual.srt` is the file for that: one upload, both languages, nothing left for the player to
translate itself. If a genuine dual-file importer is found (LR's `My texts` tab is the more likely
candidate — it wasn't verified, since it needs a signed-in account — or elsewhere), use the
separate `.te.srt` / `.en.srt` pair instead.

Refuses to build a story with any segment still missing audio, and lists which guid is missing
rather than producing a silently incomplete recording. See DECISIONS.md #9 for why story one
needed content-based meta classification instead of its `seq` column, and why the concat step
decodes and re-encodes rather than stream-copying.

The same continuous mp3 + cue times are what `../reader/` plays — `build_ms_reader.py` imports
this tool's ordering and gap arithmetic so the two can never disagree about where a sentence
starts.
