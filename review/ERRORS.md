# Error log

Every known defect across all sources, with where to fix it. Regenerate the counts with
`python3 tools/build_master.py && python3 tools/build_sentences.py`.

Nothing listed here has been deleted. Flagged rows stay in the masters and are held out of
the Anki exports until a decision is recorded, so the deck never ships something suspect.

## By severity

### 1. Wrong Telugu — fix first, these are the only actively harmful entries

| Issue | Count | Where |
|---|---|---|
| Entries typeset in Kannada, not Telugu | 3 | `review/vocab-triage.tsv` |
| Book script disagrees with the book's own romanization | 16 | `review/book-script-mismatch.tsv` |

The mismatch check romanizes the book's script and compares it to the romanization the book
prints beside it. It catches real printing errors: *Drink / Taagu* set as `డాగ్` (ḍāg) rather
than తాగు, *Journey / Prayaanam* set as `పుట్టినరోజు` (birthday), *Paper / Kaagitham* set as
`పేపర్`. Ten minutes with a native speaker clears this list.

### 2. Structurally wrong — mostly from the English-first frequency list

| Issue | Count | Why it matters |
|---|---|---|
| Inflected verb forms glossed as headwords | 89 | `annāḍu` = "said" is *he* said. Learned as vocabulary it bakes in an agreement error. 40 were traced to a lemma automatically against the Verb Lab paradigms. |
| Bound suffixes presented as words | 12 | `లో` = "in" is a case ending, not a word. Telugu has no definite article, so `ది` = "the" is not a word at all. |
| English words respelled in Telugu letters | 41 | `సెట్ seṭ` = "set". Some are genuine loanwords — the flag means decide, not wrong. |

### 3. Incomplete — a field is missing

| Issue | Count |
|---|---|
| No Telugu script | 16 words, 7 sentences |
| No romanization in the source | 11 |
| No English gloss | 3 |
| Multi-word phrase filed as a word | 32 |
| Several English glosses merged onto one form | 129 |

### 4. Not captured from the book

Words missing: [64, 91]
Sentences missing: [92, 93, 117, 291, 436, 437]

8 of 1000 items, where the page layout departs from the pattern.
Worth typing in by hand rather than engineering around.

## By source

| Source | Ingested | Notes |
|---|---|---|
| Course website | 272 words, 151 sentences | Cleanest. ~15 romanization typos on the pages themselves were corrected by deriving from script — `అరుగు` is *arugu* not *aragu*, `కానీ` is *kānī* not *kāni*. |
| Book (Gokila Agurchand) | 223/225 words, 769/775 sentences | Kannada entries, script/romanization mismatches, four items run together on one line. |
| Top-1000 list | 1000 rows → 901 distinct | An English frequency list machine-translated into Telugu. Suffixes, inflected verbs and respelled English all follow from that. |
| Spoken Telugu vocab | not yet supplied | Adapter written, waiting on the file. |
| Family conversations | 508 rows → 144 vocabulary candidates | 142 rows were pure English. No script anywhere, so nothing can be promoted automatically. Transcripts stay private. |

## Triage files

| File | Rows | What to do |
|---|---|---|
| `review/vocab-triage.tsv` | 187 | Fill `decision` = keep / drop / replace |
| `review/book-script-mismatch.tsv` | 16 | Fill `correct_script` |
| `review/sentence-triage.tsv` | 8 | Fill `decision` |
| `review/convo-vocab-candidates.tsv` | 144 | Fill `telugu_script` + `english` for the ones worth keeping |
