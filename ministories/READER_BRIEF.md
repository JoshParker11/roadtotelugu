# Reader build brief — for Fable 5

**This is a kickoff prompt, meant to be pasted as the first message of a fresh session.** It is
the build spec for a bespoke personal reading tool — this project's own version of LingQ — for
the Mini Stories. It is not the whole context on its own: **read `ministories/BRIEF.md`,
`ministories/DECISIONS.md`, and `ministories/README.md` first, in that order, before writing any
code.** They cover the translation pipeline, the audio pipeline, and every decision already made
about register, names, and segmentation. This document does not repeat any of that — it is the
part that is new: the reading application itself.

Also read, before designing anything: `STUDY/assets/reader.js`, `progress.js`, `lex.js`, and
`tools/build_reader.py`. **A working, guid-keyed reading engine with audio sync and known-word
tracking already exists in this repo, built for a different text (the Harry Potter translation
in `../translate/`).** The task here is to extend and repoint that machinery at the Mini Stories
and toward a LingQ-shaped UI, not to build a reader from zero. Where this brief's requirements
conflict with what already exists, say so explicitly and propose a resolution — do not silently
build a second, parallel system.

---

## 1. The goal

A personal, offline, LingQ-style reader for the 60 translated Mini Stories: real sentence-audio
playback, click-a-word lookup, a six-level known-word scale with keyboard-driven review, word
lists, and a stats view — all as a static site, no backend, no server-side dependency, matching
how every other part of this repo is built.

**The existing site nav should hide the current Harry Potter reader in favor of this**, for now.
Do not delete `STUDY/`'s pages or break them — just stop surfacing them as the primary entry
point from `index.html`. The underlying data and tooling stay, and ideally the new reader's
word-status store stays compatible with the old one (see §4) so marking a word known in either
place is reflected in both.

## 2. Reference screenshots

Three screenshots of LingQ's actual reader were captured directly and should be treated as the
concrete spec for layout, not just a general description:

- **Top bar**: a daily-goal ring (e.g. "27/50"), a language flag plus a running total known-word
  count (e.g. "238").
- **Reading pane**: lesson title + cover thumbnail + source line, a progress bar across the top of
  the pane, sentences rendered as separate lines, with two distinct highlight colors for words at
  different status levels (LingQ uses yellow for one status band, a lighter blue for another). A
  checkmark to mark the lesson read. A "Sentence View" toggle.
- **Audio bar** (bottom): play, ±5s skip, a loop toggle, playback speed, a scrubber with elapsed
  and total time, and a captions/transcript toggle.
- **Right panel**: the dictionary card for whichever word was just clicked (headword + gloss, a
  numbered badge for its status level), and — reached via a menu — **Review Page**, **Review
  Due**, **Review Lesson**, **Vocabulary List**, and **Manage LingQs**, plus a three-way tab
  switcher at the bottom of that panel: **LingQs / New Words / All Words**.

Reproduce this shape; it is real, observed reference material, not a rough sketch.

## 3. Content and script model

**Canonical stored data is Telugu script, always** — never romanization. Romanization is a
*display* transform applied at render time, because script is what a real dictionary lookup or
an AI API call needs to work correctly; a romanized string is ambiguous in ways the script isn't.

**Default view is romanized, not script**, with a toggle between two schemes — and **both already
exist as working code, do not design a third**:

- `STUDY/assets/te2rom.js` (`Te2Rom.romanize(text)`) — the literary/project scheme (ā ī ū ē ō,
  ṭ ḍ ṇ ḷ, ṣ ś, ṁ) already used across the site, the pipeline (`tools/te2rom.py`), and the Chrome
  extension. One-to-one with the script; the deck and every other page already assume it.
- `chrome-extension/src/colloquial.js` (`Colloquial.romanize(text)`) — the informal scheme, built
  for exactly this purpose already: how Telugu speakers actually type casually (long vowels
  doubled, dentals taking an `h`, retroflexes left plain). Deliberately lossy — cannot be
  round-tripped to script — which is fine, because script stays the canonical stored form
  regardless of which romanization is on screen.

Both are plain JS with a single `.romanize(text)` entry point; port them in directly (the same
way the Chrome extension keeps its own copy of `te2rom.js` byte-identical to the site's, checked
by `tools/check_te2rom.py`) rather than writing new transliteration logic. If the reader needs its
own copy of either file, add it to that same consistency check instead of letting a fourth
untracked copy drift.

## 4. Word-status scale — a real gap, not a drop-in match

LingQ's scale is six levels: **Ignore, New, Recognized, Familiar, Learned, Known**, with
`Recognized`–`Learned` on keys **1–4**, **k** for Known, and **Tab** to jump to the next
not-yet-marked word. `progress.js` (already in this repo) only has four states —
`known` / `hard` / `seen` / `queued` — which is **not** the same model. Extend or replace it to
the full six-level scale and the exact keybindings above; don't assume the existing states already
cover this.

**Keep the guid-keyed persistence pattern** (`localStorage`, keyed by `hash(Telugu script)`,
cache-then-write, cross-tab sync via the `storage` event) — that pattern is sound and is *why*
a word marked known while reading Harry Potter can already show as known here for free, since the
guid is the same scheme in both texts. Widening the state set should not break that sharing.

## 5. Dictionary panel

Two lookup modes per word, switchable, matching LingQs own "web dictionary vs. its own AI"
split:

- **Web dictionary** — a link out (or embed, if a target site's own policy allows framing —
  check before assuming) to a real Telugu dictionary/translation source for the clicked word.
- **Baked analysis** — this project's own precomputed data: the gloss already in
  `data/master_words.tsv` where the word exists there, or the Mini-Story-specific vocabulary work
  once it exists.

**A third, opt-in mode: an AI-generated contextual explanation**, on the Lexa pattern discussed
and settled in this project's prior session — tabs for Explain / Examples / Grammar, plus a
**Forms** tab pointing a verb at its actual paradigm in `../GRAMMAR_LAB` rather than re-deriving
it. This must be **per-word, on-demand, and opt-in** — a word can recur across dozens of
sentences, and precomputing every occurrence by default is neither necessary nor cheap. Because
this is a static, keyless site by design, a live call needs a **user-supplied API key entered and
stored only in the user's own browser** (localStorage, never committed, never sent anywhere but
the provider's own endpoint) — reasonable specifically because this is a single-user personal
tool, not something anyone else will ever load. Make this explicit in the UI, not a silent
assumption.

## 6. Audio

Real, natural recorded audio (Azure Neural TTS, already generated per-sentence — see
`ministories/README.md` and `DECISIONS.md` #8) plays for the full story, sentence-synced, the way
`STUDY/assets/reader.js`'s player already works — that mechanism transfers directly.

On LingQ, clicking a single word plays a *separate* pronunciation, sourced from an online
dictionary/TTS rather than clipped from the sentence recording. **Given this project already
generates its own Azure audio and avoids exposing keys or standing up a server, the better-fit
implementation is: precompute one short clip per distinct headword** (the same `ms_audio.py`
mechanism, extended to single words) **rather than a live third-party call from the browser.**
Note the LingQ behavior as the feature to match, not the literal implementation to copy.

## 7. Word lists and stats

- **LingQs / New Words / All Words**, exactly as the screenshots show — check `STUDY/words.html`
  and `words.js` first; a vocabulary-list view already exists for the other text and may need
  only re-pointing, not rebuilding.
- Sortable alphabetically and by at least one other axis (frequency or first-occurrence order are
  both already available in the existing data).
- **A known-word-count-over-time view.** This is genuinely new — nothing in `progress.js` today
  keeps a history, only current state. It needs some kind of periodic snapshot (e.g. record the
  known count once per day the tool is opened) to produce real growth-over-time, not just a
  present-moment number.

## 8. Constraints, stated plainly

- No backend, no server, no default-exposed API key. Static site, same as everywhere else in this
  repo.
- Don't delete or break `STUDY/`'s existing pages — de-emphasize their nav, keep the pages working.
- Don't reinvent `te2rom.js`, `Colloquial.romanize`, or the guid scheme (`tools/ids.py`) — port,
  don't rewrite.
- File layout, framework choice (or no framework), and exact code structure are yours to decide —
  propose a concrete plan and state it before large-scale rewriting, the same review-before-commit
  discipline the rest of this project already follows.

## 9. Mistakes not to make (each of these actually happened once already this project)

- Assuming `progress.js`'s four states already match LingQ's six — they don't; extend them.
- Assuming a `seq` column is comparable across split lesson files for the same story — it isn't;
  `ms_segment.py` numbers `seq` per file, not per story (see `ministories/DECISIONS.md` re:
  `ms_lr_export.py`'s original meta-classification bug).
- Writing a new chat-style romanizer from scratch — `Colloquial.romanize` already exists and is
  tested; port it.
- Treating a checker or a new state model as correct because it runs without errors on clean
  data — that proves nothing. Test any new logic against deliberately broken input first.
