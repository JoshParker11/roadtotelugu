# Practice, and what is still open

Decisions and reasoning that were worked out in conversation and would otherwise be lost.
Written 2026-08-12, at the point where week 1 was finished and week 2 had just started.

---

## The focused hour

Steady state, once Anki reviews have built up:

| | |
|---|---|
| **25 min** | **Anki.** Reviews first, then new cards. Non-negotiable — skipping a day costs more than it saves. Every answer spoken aloud. |
| **15 min** | **Verb Lab.** 5 verbs, "weakest first" preset. Notice step off once familiar. |
| **10 min** | **One lesson section or deep dive**, ~3× a week. Otherwise a song or story page. |
| **10 min** | **Free production.** Five true sentences about your actual day, aloud. Write down what you couldn't say — that list is the next question for a native speaker. |

**Why that order.** Reviews and new cards are the only genuinely time-bounded thing and need
the freshest attention. The Verb Lab is also high-effort retrieval, so it comes second — which
means ~40 minutes of hard retrieval before anything easy. The reading at the end is not filler,
it is recovery that makes the hard part sustainable daily. Don't cut it to drill more.

The free-production block is the one people skip and the one that converts knowledge into
speech.

### The review-load ceiling

**15 words + 3 sentences a day grows to roughly 150–180 reviews/day at steady state** — the
usual ~10× multiplier for mature cards. At 8–10 seconds each that is 25–30 minutes, before new
cards. So within about two months Anki alone consumes half the hour. That is the ceiling.

**Watch the review count around week 6.** If it passes ~200/day, drop new words to 10 rather
than letting Anki crowd out the verb drill and the speaking.

### Rules that matter more than the schedule

- **Say everything aloud.** Silent Anki builds recognition, and recognition is not the goal.
- **Never fix cards in Anki.** Add a line to `data/overrides_*.tsv` instead; an in-app edit is
  overwritten on the next import.
- **Keep a running question list.** Anything you couldn't say, or Telugu that looked wrong.
  That list is what makes ten minutes with a native speaker worth an hour of solo study.

---

## The commute

**Driving is bad for the thing you planned to do in the car.** Retrieval practice — producing
from an English prompt — is the most attention-hungry technique available and the one that most
rewards full attention. Doing it while driving spends your worst cognitive resource on the
work that needs your best. Worse, you cannot tell when you were wrong, so errors quietly
automate.

What survives partial attention:

- **Shadowing** — imitation, not recall. Builds articulation and prosody. The default track in
  `tools/build_audio.py`.
- **Narrow listening** — repeated exposure to a small set already studied at the desk.

So keep the production track, but treat it as **consolidation of material already drilled**,
never as first exposure. `build_audio.py` defaults to cards already in review for that reason:
audio-only exposure to language you cannot yet segment is close to worthless.

### The gap: perceptual training

Nothing in this project trains the ear, and Telugu has three contrasts English lacks:

- **Vowel length** — `nēnu` vs `nenu`, `pāḍu` (sing) vs `paḍu` (fall). Meaning-bearing.
- **Retroflex vs dental** — `ṭ/t`, `ḍ/d`, `ṇ/n`.
- **Gemination** — `pelli` vs `peli`.

Minimal-pair discrimination is the **best possible fit for a car**: purely auditory, no output
required, benefits from massed repetition. It is also a prerequisite for comprehensible input —
CI does not work if the stream is acoustic mush. The archived research roadmap already sets the
target: *85% identification on trained sound contrasts*.

**Built.** `tools/minimal_pairs.py` scans the word master for pairs differing by exactly one
of the three contrasts and writes `review/minimal-pairs.tsv`. The filter that matters is the
gloss check — ṭamāṭa/ṭamāṭā and gaṭṭiga/gaṭṭigā fall out of a naive scan but are one word
spelled two ways. 19 real pairs so far, and the list grows as the vocabulary does.

It is a **recording script**: hand it to a native speaker, record the two columns, and it
becomes the discrimination drill. Until there is audio it is still worth reading aloud.
It also works as a data check — it surfaced `తను` glossed "Eat", which is the book's typo for
`తిను` (`తను` means "himself").

---

## Verdict on the Goethe Verlag / 50LANGUAGES deck

Evaluated `Telugu__through_English_-_Vocabulary.apkg` (1,946 notes, Book2 thematic vocabulary).
**Do not pivot to it, do not merge it.** Recorded so this isn't re-litigated:

- **Covers 0 of our top 100 words by frequency.** No *I, you, go, come, eat, good, yes, no,
  water*. Has *despair, distrust, curiosity, aircraft carrier, Brussels sprout*.
- **792 of 1,946 entries are multi-word phrases** filed as vocabulary — `అణచి వేయబడిన స్థితి`
  glossed "depression".
- **419 words end in ము**, the formal written register. `కోపము` where Hyderabad says `కోపం`.
- **Only 201 of 1,851 overlap** with our master — a near-disjoint set.

Same failure mode as the top-1000 list: an English concept list translated into 50 languages,
so abstract English nouns come out Sanskritic.

**Worth revisiting around month four** for two things: every note has native-recorded Telugu
*and* English audio (we can only generate synthetic), and the concrete topics — body (40),
people (52), fruit (41), vegetables (39), animals (57) — are ~250 usable nouns. Its
romanization is strict ISO 15919 and agrees with `te2rom.py` on 75.5%, every disagreement being
convention not error, so it is mechanically convertible when wanted.

---

## Open threads

### Blocked on you

| Thread | Blocked on |
|---|---|
| Re-import to Anki | Deliberately deferred. Word file is 1,993 rows with clean fronts; current deck has the old concatenated glosses. |
| `review/*.tsv` — 355 rows total, **0 decided** | The 16 in `book-script-mismatch.tsv` are the only actively wrong Telugu in the project. Highest value per minute of anything on this list. |
| Commute audio | `brew install ffmpeg`, plus HyperTTS actually run. `tools/build_audio.py` is written and untested against real audio. |
| Spoken Telugu vocab source | Adapter written in `tools/adapters.py`; file never supplied. |

### Offered and deferred

- **Minimal-pair audio generator** (see above).
- ~~**Session log**~~ — built, see below.
- **Generated midterm/final** — the week-1 test is a fixed bank of 61. After two weeks it
  measures recall of the test rather than the language. The midterm should draw randomly from
  `data/master_sentences.tsv` by lesson tag so each sitting differs.

## The practice log

`python3 tools/session_log.py` appends a dated entry to `log/YYYY-MM.md` and opens it in
`$EDITOR`. The Anki numbers — cards, minutes, retention, new vs review, split by note type —
are read from the collection's revlog, because you will not reliably record "47 reviews in 11
minutes at 84%" but your collection already knows. The prose is yours.

`--show` prints today's numbers without writing. `--summary` gives streak and totals.

Of the prompts, **"what I could not say"** is the one worth discipline. It is the bridge from
practice back into the pipeline: those gaps become questions for a native speaker and rows in
`review/`. Everything else in this project has an audit trail; this is the field that gives
daily practice one.

### Latent asset nobody would find

**1,126 words and 2,014 sentences carry a hand-made syllable-stress guide** (`nēnu` → `NAY-noo`)
harvested from the archived Anki decks. It is in the `pronunciation` column of both masters and
is **not emitted to Anki**. Adding it to a note type would cost one line in
`tools/build_exports.py`.

### Known-wrong, already documented

`review/ERRORS.md` is regenerated from the data and stays accurate. The short version: 3 Kannada
entries, 16 book script/romanization mismatches, 89 inflected verbs glossed as headwords, 12
bound suffixes, 66 respelled English words. All flagged, none shipped to the deck.
