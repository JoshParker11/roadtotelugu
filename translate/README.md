# Harry Potter 1 → Telugu

A meaning-for-meaning translation of the first Harry Potter book, built as a study text.

## Why this is worth doing

You already know the book. Comprehensible input works when you can reconstruct meaning from
memory the moment the language fails you, and there is almost no text where that is more true.
Every chapter translated also generates vocabulary in context, which feeds straight back into the
deck.

The bottleneck is not producing Telugu. It is judging whether the Telugu is good, which you
cannot yet do. Everything in this directory exists to make the *checkable* parts checkable and to
make the unjudgeable parts consistent, so that when a native speaker does read it, their
corrections apply to the whole book instead of to one page.

## What is committed and what is not

`source/` and `work/` are gitignored, for two separate reasons:

- **`source/`** is the English novel, in copyright.
- **`work/`** is our translation of it. A translation is a *derivative work* — no more
  publishable than the original. This repo is public. Rowling's rights holders have a long
  record of pursuing exactly this.

Everything else here — the tooling, the style guide, the address matrix, the glossary — is our
own analysis and a term list, and is committed. If `work/` were ever lost, everything needed to
redo it consistently survives.

There is an official Telugu edition (Manjul Publishing, ISBN 9788183224215, print only). Worth
owning as a check. Translate a passage *first*, then compare — reading theirs first just anchors
you to their choices.

## The documents

| | |
|---|---|
| [STYLE.md](STYLE.md) | Register, dialect, the three-bucket rule, and the stitching convention |
| [ADDRESS.md](ADDRESS.md) | Why address matters so much in Telugu, and how to read the matrix |
| [address.tsv](address.tsv) | Who says నువ్వు vs మీరు to whom, and third-person respect |
| [glossary.tsv](glossary.tsv) | The 156 anchor terms, with gender and narrator respect level |
| [DECISIONS.md](DECISIONS.md) | Append-only log of calls made, plus the open questions |

Read STYLE.md §4 before writing a single sentence. The stitching convention is the part your
anchor policy needs and the part nothing else will tell you.

## The tools

```bash
python3 tools/hp_segment.py                      # source -> work/chNN.tsv  (safe to re-run)
python3 tools/hp_terms.py --ch 1                 # proper nouns not yet in the glossary
python3 tools/check_hp.py --ch 1                 # QC
python3 tools/check_hp.py --ch 1 --backtranslate # blind back-translation sheet
```

**`hp_segment.py`** cuts the novel into paragraph-level segments with content-derived GUIDs, one
TSV per chapter — 3,016 segments across 17. Re-running carries existing translations forward by
GUID; it will not silently eat work.

**`hp_terms.py`** lists proper nouns the glossary does not classify yet. Run it before starting a
chapter. Chapter 1 is fully covered; later chapters are not.

**`check_hp.py`** catches the errors invisible to someone who cannot yet read the target:

- a name dropped from a paragraph
- a phrase left in English and forgotten
- inconsistent stitching (`Harry-కి` here, `Harryకి` there)
- a free word hyphenated as though it were a suffix
- the English edited after it was translated
- status columns that disagree with the content

It cannot tell you whether the Telugu is *good*. Nothing can.

## The workflow for one chapter

1. `hp_terms.py --ch N` → add any new names to `glossary.tsv`
2. Translate, working down the TSV. Segment by segment, `status=draft`
3. `check_hp.py --ch N` → fix what it reports
4. `check_hp.py --ch N --backtranslate` → back-translate from the Telugu **without looking at
   the English**, then diff against the `en` column. This is the only check that finds dropped
   clauses and invented content
5. Read it aloud, or run it through TTS. Unnatural rhythm is audible long before you can say why
6. Native review — sampled, not proofread. Nobody will proofread 77,000 words as a favour. A page
   at a time, rated on three things: does it sound like a book, is the address right, is anything
   simply wrong
7. Mine the new vocabulary into the deck

## Status columns

`todo` → `draft` → `query` → `checked` → `done`

`query` means translated but with an open question. Use it freely and keep moving; a chapter
should never stall on one sentence. Open questions go to `review/questions.md` with the rest.

## Scale, honestly

77,000 words. This is a long project, and English's participial pile-ups need genuine
restructuring for Telugu word order rather than substitution.

Do chapter 1 completely and well — 119 segments — and treat the glossary, the matrix and this
tooling as the real deliverable. That is the reusable 80%. Then put it in front of a native
speaker and let their reaction decide whether chapters 2–17 happen.

## A note on the scan

The source is a cp1252 OCR scan with artefacts: chapter nine lost its `CHAPTER NINE` marker,
chapter seventeen's title has prose glued to it, `You-Know-Who` appears in three spellings, and
occasional words are split mid-token. The segmenter handles the structural ones and the
glossary's `variants` column absorbs the spelling ones. Expect the odd broken word in the English
column; translate what was clearly meant.
