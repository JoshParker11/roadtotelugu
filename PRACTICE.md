# Practice, and what is still open

Decisions and reasoning worked out in conversation that would otherwise be lost.
Started 2026-08-12; the strategy below was rewritten 2026-08-14, after the course extraction
finished and the masters were re-sequenced.

---

## The hour — phase A, roughly day 4 to day 30

Morning Anki (15 new words, 3 new sentences, reviews) and the commute are separate. This is the
dedicated block, and **its job is converting recognition into production, not meeting new
vocabulary.** New vocabulary is the morning's job.

| min | | |
|---|---|---|
| **10** | **Yesterday's misses** | Retrieve what you wrote down yesterday. This is the loop that makes writing it down worth anything. |
| **20** | **Today's unlocked sentences** | ~30 land per day. Read → cover → produce from English → then **vary them** (change person, tense, negate). |
| **10** | **Verb Lab** | Weakest-first. |
| **10** | **Native content** | One short clip. No obligation to understand — exposure, and anything recognised gets noted. |
| **10** | **Free production** | Five true sentences about your day. Write down what you could not say. |

Wherever "write it down" appears above, the destination is **your own notes** — the formal log
was considered and dropped (see below). The habit is what matters; the file format does not.

**The 20-minute block is the hour.** Everything else supports it. Those sentences use exactly the
words learned that morning, which is what makes them worth more than anything else at this stage.

This shifts around day 30–45, when the N+1 sentences stop being a stretch and native content
takes over the middle twenty.

### When there is only fifteen minutes

Ranked, so the choice is never in question:

1. **Anki reviews** — always; the only genuinely time-bounded thing
2. **The N+1 set** — the day's highest-value retrieval
3. **Verb Lab, weakest-first**
4. **One native clip, once through**
5. **Minimal pairs aloud** — `review/minimal-pairs.tsv`

### Two systems, deliberately separate

| | owns | state |
|---|---|---|
| **Anki** | the permanent core — 15 words + 3 sentences a day | scheduled forever |
| **The drill** (to build) | wide practice over everything unlocked | lightweight, disposable |

They never conflict because they do different work, and **the queue will always exceed the
time**. That is correct: the drill's job is triage, not completion. Nothing breaks when a
practice item slides, which is exactly why it cannot live in Anki.

### Why Anki stays at 3 sentences a day

Every Anki card is a lifetime commitment at roughly a 10× review multiplier. 15 words + 3
sentences already projects to the ceiling below. What should change is *which* three — the most
reusable, not merely the next in unlock order. The other ~27 that unlock each day are practice
material, not deck material: you do not need to retain them, you need to process them.

---

## Standing constraints

Three decisions that should not be quietly reversed later.

**Do not generate novel Telugu.** Every Telugu string in this project traces to a verified
source, and that discipline is why the deck is trustworthy. Generated sentences are *plausible*
but unverified, and would be automating errors into a deck reviewed daily and not yet auditable
by the learner. Generating **exercises from verified Telugu** — cloze, recombination through the
audited conjugation engine, English→Telugu prompts — is unlimited and safe. Revisit generation
only when a native speaker can spot-check a batch, or when the 1,419 unlockable sentences run
dry, whichever comes first.

**The review deck is a closed set.** Mined native sentences do not go into it. The phase-one
sentences are *sequenced* — `unlock_day` makes them a curriculum — and dropping an eight-unknown
native sentence in destroys that property. Mined **words** append to the word queue; mined
**sentences** are held separately with a computed unlock day and graduate into the reviewable set
on their own when vocabulary catches up.

**The study order is append-only.** A word that has a `study_order` keeps it forever; new words
append. Re-sorting would renumber cards already in the deck, and the only way to make Anki honour
a new order is delete-and-reimport, which destroys scheduling. It also keeps the path linear —
"word 312 came on day 21" stays true. `sequence.py --reorder` forces a full recompute and is
correct exactly once, before the first import.

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

## The study desk

`STUDY/words.html` — the whole word master as one ordered queue, built 2026-08-14. Third static
site alongside the course and the Verb Lab, and the surface the drill and the daily log will
share.

**Two kinds of state, and the split is the design.** Which words you have *met* is derived, not
stored: the master is already an ordered curriculum, so a start date and a rate settle all 2,103
at once, and storing 2,103 booleans to represent one date would be a database that can disagree
with itself. Which words you *know* cannot be derived from anything — it is a judgement — so it
is stored per word.

| | where | shape |
|---|---|---|
| Schedule | `rtt.setup` | `{start, rate, skip}` — `skip` subtracts days you took no new cards |
| Known | `rtt.known` | `{guid: date-marked}` |
| Needs work | `rtt.hard` | `{guid: date-marked}` |

**Keyed by guid**, the sha1 of the Telugu script from `tools/ids.py` — which is what makes hand
marking safe to keep. Re-run the pipeline, re-export, re-import, and every mark still points at
the word it was made about. A row number would not survive one insertion.

`STUDY/assets/progress.js` owns all of it and touches no DOM, so the log and the drill read the
same state rather than each inventing their own. `exportState()` emits `{setup, known, hard}` —
already the shape a Python consumer would want, so nothing has to be reshaped later.

`tools/build_studydata.py` publishes `data/master_words.tsv` to `STUDY/data/words.js`. It reads
the **master**, not `anki/import_words.txt`: the Anki file is disposable output with five fields
and no order, day, island or lesson. A `.js` file rather than `.json` because `fetch()` is
blocked under `file://` and the site has to work opened from the folder — the same reason the
Verb Lab ships `verbs.js`.

**Marking words known ahead of schedule is the point**, not a side feature. Words picked up at
home are free vocabulary the sentence drill can use immediately, and nothing but you knows which
they are. The "By theme" grouping exists for exactly that sweep.

---

### Dropped 2026-08-15: the formal daily log

A page for daily entries was planned and is **not being built**. The learner's call, and the
reasoning survives scrutiny: the path is already reconstructible without it, and a ritual that
stops feeling worth it gets abandoned anyway — at which point the record has a hole in it that
is worse than never having started.

What makes this safe rather than merely convenient: **Anki's revlog is already recording the
objective half, automatically and retroactively.** Every review, lapse, interval and ease is in
the collection whether or not anybody writes an entry. `tools/session_log.py --summary` reads it
on demand, so "how did week 3 actually go" remains answerable in six months from data nobody had
to type. The decision is reversible at zero cost, which is why it is the right one to take now.

What is genuinely lost is **"what I could not say"** — the gaps between what you wanted to
express and what you could. No collection records that. The learner is keeping this
informally, which is the same content without the tooling, and it stays the highest-value
thing to write down. It feeds `review/questions.md` and the shopping list for the masters.

`tools/session_log.py` stays as an on-demand stats reader (`--show`, `--summary`). It is no
longer a daily ritual.

---

## What to build next, in order

1. **Word capture.** The half of the dropped inbox that was never about journaling. When a word
   turns up in native content or in conversation and belongs in the deck, something has to get
   it into `data/master_words.tsv` — appended to the end of the study order, never inserted.
   That is a pipeline function and it survives the log's cancellation on its own merits.

   Small: a plain append-only text file plus a command that folds it into the master and
   re-runs the exports. No format, no schedule, no prompts to ignore. Build it when the first
   word actually needs capturing rather than in advance.

2. **The recombination drill.** A page, not a terminal tool — it has to run during the session,
   record state for free, and work on a phone. Same architecture as the Verb Lab: data generated
   offline into JSON, drill runs static, state in `localStorage`.

   *Design settled in conversation:* the drill item is the **transformation**, not the sentence —
   72 variants per sentence is not a space to enumerate, and what is being trained is the
   operation. Each sentence is served with one transformation, chosen by which operation is
   weakest. Revisits escalate through modes rather than repeating: **comprehend** (day it
   unlocks) → **produce** (+1) → **cloze** (+3) → **transform** (+7, +16, +35), on the Verb Lab's
   existing Leitner gaps.

   *Measured against the corpus:* **468** unlockable sentences contain a Verb Lab form and are
   recombinable by tense and polarity; **131** also have a bare pronoun subject and can be
   recombined by person. Tense swaps are always safe. **Person swaps are not** — `ikkaḍa okaṭi
   undi` → `nēnu ikkaḍa okaṭi unnānu` is grammatical and nonsense — so restrict them to the 131.

3. **Text-analysis page.** Paste Telugu, get: coverage against the known set; the unlock curve
   ("learn the top 20 unknown words from *this text* and coverage goes 34% → 58%"); the text
   rendered with known words dimmed; and the sentences already at N+1. **Split unknown words into
   two piles** — already in the master at position 400 (arrives day 27) versus not in the master
   at all. Those need opposite actions and lumping them hides the only decision the page exists
   to support. Plus **projected comprehensibility**: a day slider turns "someday" into a date.

4. **The podcast.** An hour of audio with a timestamped transcript, supplied but not yet ingested.
   At this vocabulary the point is not comprehension: it is (a) becoming a frequency corpus that
   votes on the word order, as the family recordings already do, (b) the playlist of lines already
   at 100% coverage — real native audio, comprehensible now, and (c) a number to aim at.

5. **Course leftovers, not blocking.** Six one-minute story videos (11, 12, 15, 17, 18, 20), Quiz
   5 and Practice Test 2, and ~20 minutes of conversation and cultural-immersion lessons the
   learner has deliberately deferred as outside the core.

### Blocked on the learner

| Thread | Blocked on |
|---|---|
| The clean re-import | **Done 2026-08-14.** Both note types deleted and re-imported against content-derived guids. The order is now append-only; `sequence.py --reorder` is a mistake from here on. |
| `review/questions.md` | 12 questions for a native speaker, consolidated. Ten minutes with his wife clears most of them. |
| `review/*.tsv` triage | 355 rows, 0 decided. `book-script-mismatch.tsv` is the only actively wrong Telugu in the project. |
| Commute audio | `brew install ffmpeg`, plus HyperTTS actually run. |

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
