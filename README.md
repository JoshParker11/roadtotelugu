# Road to Telugu

A personal system for learning Telugu through English: a grammar-backed course, a verb
conjugation lab, and the Anki decks both feed. Static HTML, no build step, no dependencies.

**Live:** see the Pages URL in the repo's About panel · **Local:** open `index.html`

| Directory | What it is |
|---|---|
| [`LEARNING_GUIDE/`](LEARNING_GUIDE/) | The course — lessons in source order, deep dives, mini stories, songs, sentence stems |
| [`GRAMMAR_LAB/`](GRAMMAR_LAB/) | Verb Lab — 35 root verbs, 14 paradigms, interleaved production drill ([readme](GRAMMAR_LAB/README.md)) |
| [`anki/`](anki/) | Source-of-truth CSVs for the word and sentence decks ([readme](anki/README.md)) |

## The idea

The goal is conversational Telugu for family and for colleagues in Hyderabad, at roughly two
hours a day, without restarting the system every few weeks. The guiding document is
[`LEARNING_GUIDE/LEARNING_GUIDE.md`](LEARNING_GUIDE/LEARNING_GUIDE.md).

Division of labour between the pieces:

- **Anki** carries vocabulary and whole sentences, including on the commute.
- **The course** supplies explanations, worked examples and controlled input.
- **The Verb Lab** covers the one thing flashcards handle badly — producing an inflected form
  fast enough to speak it.

## How it is actually used

[`PRACTICE.md`](PRACTICE.md) holds the study-session structure, the review-load arithmetic, why
the commute is the wrong place for production drilling, the verdict on sources that were
evaluated and rejected, and every open thread. Read it before picking the project back up after
a gap.

[`LEARNING_GUIDE/concepts/verb-forms-explained.md`](LEARNING_GUIDE/concepts/verb-forms-explained.md)
explains what tense, aspect, mood and polarity are, what all fourteen Verb Lab forms mean, and
why three were deliberately left out.

## Honest limits

**No native speaker has reviewed the Telugu here yet.** The lessons are extracted from an
external resource; the mini story, the assembled sentence scripts and every Verb Lab paradigm
were generated. Forms cross-check against each other, which says the method is sound, not that
any given cell is right. [`GRAMMAR_LAB/review.html`](GRAMMAR_LAB/review.html) turns verification
into six questions per verb.

Everything targets educated colloquial Hyderabad/Telangana speech. Coastal Telugu and most
textbooks differ in places; neither is wrong.

## Not included

`English-Telugu-+RootVerbs.pdf` (bhashafy.com) is third-party material and is gitignored rather
than redistributed. The 35 verbs it lists are recorded in `GRAMMAR_LAB/data/verbs.js`, so the
site does not depend on it.

Course content is derived from an external paid resource and is not a substitute for it. Song
pages quote short lyric excerpts for study and analysis.

## Working on it

Nothing needs installing to view the sites. Two scripts exist for regenerating data:

```bash
python3 anki/tools/build_csvs.py
```

Rebuilds both Anki CSVs from the course pages. Re-run after processing a new lesson; row order
is stable so new material appends with fresh IDs.

Verb corrections go in `GRAMMAR_LAB/data/verbs.js` — change a stem, and the whole paradigm for
that verb regenerates.
