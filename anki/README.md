# Anki source of truth

Two CSVs extracted from the Foundational Telugu website in `../LEARNING_GUIDE/`. These are the
canonical lists. Edit them here, re-import into Anki; do not edit cards in Anki and expect the
change to survive.

| File | Rows | What it is |
|---|---|---|
| `telugu_words.csv` | 272 | Vocabulary, in the site's existing 5-field format |
| `telugu_sentences.csv` | 151 | Production sentences, English-prompt-first |

Everything here comes from lessons 1–6, the "How was your day?" scenario, the two song pages,
Mini Story 01, and the `oka` deep dive. That is the full extent of what the website currently
contains. See **What is missing** at the bottom.

## `telugu_words.csv`

Columns 1–5 are the note fields already used throughout the site. Columns 6+ are metadata for
this file's role as a source of truth — set them to *Ignore* in the Anki import screen, except
`Tags`.

| # | Column | Import as |
|---|---|---|
| 1 | `English` | Field 1 — English, carries the register/context cue |
| 2 | `Romanized` | Field 2 |
| 3 | `TeluguScript` | Field 3 |
| 4 | `Audio` | Field 4 — deliberately empty, for your family recordings |
| 5 | `Example` | Field 5 — short framing sentence, romanized |
| 6 | `Tags` | **Tags** |
| 7 | `ID` | Ignore — stable key (`W0001`…), also the study order |
| 8–13 | `Source` `Section` `Category` `Tier` `Flag` `AlsoSeenIn` | Ignore |

Row order is study order: lesson 1 → 6, then the scenario, then the songs.

Tags are `src::lesson-03`, `cat::pronoun`, `tier::core`, and `flag::verify` where relevant.

`Tier` reflects the site's own advice about what is worth carding:

- `core` (219) — every lesson and scenario word, plus the song words tagged *daily*
- `standard` (28) — song words tagged *limited*, and the number teens the site calls lower priority
- `recognition` (25) — the poetic song register. The song pages are explicit that carding these
  "fills your deck with words you'll never say." Suspend or skip: `tag:tier::recognition`

Six rows carry `flag::verify` — song vocabulary the site itself flagged for native-speaker
confirmation.

Every row has Telugu script taken verbatim from the site. Seven romanizations appeared on two
pages; those were merged into one row and the second page recorded in `AlsoSeenIn`. `aḍugu` is
kept twice on purpose — "step" and "to ask" are genuinely different words.

## `telugu_sentences.csv`

Built for the drill you described: read the English, produce the Telugu out loud, flip, shadow.

| # | Column | Import as |
|---|---|---|
| 1 | `EnglishPrompt` | Field 1 — the situation, with tense/register cues |
| 2 | `EnglishAudio` | Field 2 — **empty, this is the field you asked for** |
| 3 | `TeluguScript` | Field 3 — HyperTTS reads this for the back |
| 4 | `Romanization` | Field 4 |
| 5 | `TeluguAudio` | Field 5 — empty, for HyperTTS |
| 6 | `Notes` | Field 6 — literal meaning, grammar or register note for the back |
| 7 | `Tags` | **Tags** |
| 8 | `ID` | Ignore — stable key (`S0001`…) |
| 9–15 | `Source` `Kind` `RegisterCue` `CardMode` `ScriptStatus` `Level` `Label` | Ignore |

### Filling the audio

Both audio fields are empty. In Anki: **Browse → select the notes → Notes → HyperTTS → Add
audio**, once per field. Point the English pass at `EnglishPrompt` → `EnglishAudio`, and the
Telugu pass at `TeluguScript` → `TeluguAudio`. Restrict the Telugu pass to
`-tag:flag::needs-script` so you don't generate audio for the four rows that have no script.

### Columns that need your attention

`CardMode` — 146 rows are `production`. Five are `recognition`: the answer isn't a Telugu
utterance ("Which two possessives are completely new words?", "5,000,000"). They're real drills
from the site's self-tests but they don't work as production cards. Suspend them:
`tag:mode::recognition`.

`ScriptStatus` — how the Telugu script was obtained. **This is the column to trust least.**

- `verbatim` (94) — printed in Telugu script on the site, copied exactly
- `assembled` (53) — the site gave romanization only, so the script was rebuilt word by word
  from forms the site does print. Zero ambiguity in the lookup table, and the method reproduces
  89 of the 91 multi-word sentences whose script *is* on the site. Still: these are the rows to
  put in front of a native speaker first. `tag:flag::assembled`
- `needs-script` (4) — couldn't be assembled from attested forms, left blank rather than guessed.
  `tag:flag::needs-script`

A general-purpose romanization-to-script transliterator was tried first and scored only 87% on
the site's own known pairs, failing on exactly the highest-frequency items (`ṭīcharu`, `nāna`,
`dēśam`, the whole `-aṇḍi` family). It was abandoned in favour of the lookup approach. No Telugu
in this file was invented — it is either copied from the site or composed from parts the site
prints, and the `Notes` on the site's own pages still apply: treat generated Telugu as draft
until a proficient Telangana speaker has heard it.

`RegisterCue` — `respectful` (31) or `informal` (2), derived from grammar the site teaches:
`mīru`/`mī`/`gāru`, the `-ṇḍi` and long `-andi` endings, `-nnārā`/`-āru`. Where the Telugu is
marked and the English prompt didn't already say so, `[respectful]` or `[informal]` was appended
to the prompt so the card asks for the right form. The remaining 118 rows are genuinely neutral
or have no register-bearing element.

`Kind` — where the sentence came from: `phrase` (18), `scenario` (16), `drill` (48, from the
lesson self-tests), `example` (24), `contrast` (13, minimal pairs from the `oka` deep dive),
`frame` (12, templates with `______` blanks), `story` (12), `dialogue` (8).

The 12 `frame` rows contain `______` on both sides. They are worth keeping as cards — fill the
blank with something true about yourself each time — but they will look odd on first review.

## What is missing

**The 1500-word list is not here, and can't be — the website doesn't contain it.** Lessons 1–6
yield 272 words. There is no verb list beyond the 16 that appear incidentally, which is the
opposite of the verb-heavy weighting you want.

The `../LEARNING_GUIDE/stems/stem-data.js` file has ~90 English sentence frames ("I don't
understand", "Where is ___?", "How do you say ___?") tagged `now` (buildable with lessons 1–6)
or `soon` (needs the tense lessons). They're English-only — no Telugu — so they aren't in
`telugu_sentences.csv`, but they are the obvious next batch to get Telugu for.

Three things would close the gap, in order of value:

1. A frequency-ranked Telugu verb list with the conjugations you'll actually use. Nothing on the
   site supplies this.
2. Telugu for the ~90 stems in `stem-data.js`.
3. Lessons 7+ of the Udemy course, processed the same way the first six were, plus *Spoken
   Telugu for Absolute Beginners*.

None of that changes the format of these two files — new rows append with the next `W`/`S` id.
