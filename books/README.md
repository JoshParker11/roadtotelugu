# Books

Familiar books in Telugu, read chapter by chapter (Page) or one sentence at a time (Line by
line). Tap a word for its gloss, a morpheme breakdown, and the grammar rules it uses. Each word
is in one of three states: **new** (blue), **seen** (amber, which a word becomes when you first
tap it), or **known** (plain). Names and English loans are never coloured.

## Adding a chunk

1. Drop the chunk into `source/<book>/` named `chapter-NN-chunk-NN.md`, in the FORMAT.md
   shape (`**N.**` / `EN:` / `RO:` / `TE:`, then `## Mined vocab`).
2. `python3 tools/build_books.py` prints every Telugu word that has no row in
   `source/lexicon.tsv`. Add those rows: `te, rom, en, kind (word|loan|name), parts
   (morph=meaning + …), rules (ids from source/grammar.tsv), note`.
3. Re-run the build. It writes `data/books.js`, the only file the page loads.

Chunks of the same chapter merge in order. A new book needs a `source/<id>/book.json`.

The lexicon and grammar rules are shared by every book, and so is word status, so a word you
know from one chapter stays known everywhere.

All Telugu and every gloss is a draft until Neha or a tutor has checked it.
