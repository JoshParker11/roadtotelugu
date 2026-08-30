# An Intensive Course in Telugu — ingest

64 lesson PDFs → dialogues the reader can use. Stage one is done; the hard part is named below.

The PDFs themselves are third-party paid material and are **not** in this repo — they live in
`~/Downloads/Lesson PDFs - An Intensive Course in Telugu`, and `tools/ic_extract.py --pdfs`
points elsewhere if they move. What is committed is the derived study data, the same line the
project already draws for `sources/raw/book1000.pdf` and the LingQ mini stories.

```bash
python3 tools/ic_extract.py --report     # counts only, writes nothing
python3 tools/ic_extract.py --pairs      # raw/lesson-NN.tsv + raw/pairs.tsv
```

## What came out

**1,839 units across all 64 lessons, 58 of them (3.2%) without an English translation.**

| | |
|---|---|
| dialogue turns | 52 lessons, delimited by the `speaker :` label |
| prose blocks | 12 lessons — 61–64 are "OVERALL REVIEW" newspaper passages, the rest revision units. Flagged `prose`, and paired line-by-line rather than by turn, which is weaker |

## The two findings that decided the route

**Romanization exists for six lessons, not sixty-four.** Unit I (lessons 1–6) prints four lines
per turn — Telugu, English, Devanagari, romanization. From lesson 7 the scaffolding is dropped.
Measured, not assumed: 291 romanized dialogue lines in lessons 1–6 and exactly zero after. So
reading the romanization and transliterating back into script — the obvious plan — reaches 6 of
64 lessons and stops.

**The legacy Telugu encoding is identical across all 64 files.** The subset fonts have
meaningless per-file names (`TT371O00` in lesson 1, `TT694O00` in lesson 7) but preserve the
original character codes, so the same word is the same bytes everywhere: `A¨` is అది in 47 of
the 64 files. The whole book uses **209 distinct glyph codes, 142 of which cover 99%** of all
occurrences.

That is what makes the real route viable: decode the font once, and every lesson's Telugu comes
out as Telugu — and as *script*, which is the project's canonical anchor everywhere else, rather
than romanization that would have to be inverted.

## Where the decoder's evidence comes from

Three sources, and finding the second and third is what moved the decoder off its plateau. A
decoder is right when `decode(legacy)` run back through `tools/te2rom.py` reproduces the book's
own romanization — so every pair below is gated on that before it is allowed to teach anything.

| file | what | how many |
|---|---|---|
| `raw/pairs.tsv` | every Telugu line in a romanized lesson paired with the romanization printed under it | 1,170 lines |
| `raw/inline_pairs.tsv` | the grammar notes' inline glosses — `^èþ§æþ$Ðèþ#ṁø caduvukō` — where word and romanization sit on the same line | 1,273 (642 distinct) |

**The first version of `pairs.tsv` had 182 lines**, because it only looked at the *dialogues* of
lessons 1–6. Unit I romanizes the whole lesson — repetition drills, substitution drills,
exercises. Lesson 1 sets 774 romanization spans and the dialogue accounts for 27 lines of them.
Six times the parallel text was sitting there the whole time, missed only because the extractor
happened to be walking the dialogue when the corpus was built.

**The inline glosses matter for a different reason: coverage.** Everything in `pairs.tsv` comes
from lessons 1–6, which never use the glyphs the rest of the book needs. The grammar notes gloss
inline in *every* lesson, so they reach the tail of the inventory — which is exactly where the
errors were.

## Column meanings

`legacy` is the extracted bytes **preserved exactly**, not cleaned. It looks like corruption and
is not — it is a different encoding, and normalising it would destroy the only copy of the
Telugu. `rom` is the book's romanization where it exists, with its diacritic glyphs mapped
(`¡`→ā, `∆`→ṇ, and ten others read off rendered glyphs rather than inferred — the first pass
guessed `∆` as ū from context and it is ṇ: `[gaṇṭa]`, not `[gaūṭa]`).

## The decoder, and where it actually stands

```bash
python3 tools/ic_rom2te.py --check    # 182/182 aligned turns round-trip clean
python3 tools/ic_decode.py --learn    # induce intensive/glyphmap.tsv  (~50s)
python3 tools/ic_decode.py --check    # accuracy on the fixed word-pair set
python3 tools/ic_decode.py            # decode raw/ -> work/
```

**Held-out word accuracy: 48.8%. Training-set word accuracy: 63.8%. Character-level
similarity on held-out words: 80.9%.**

Accuracy is measured on held-out word types — a fixed 15% chosen by hash of the legacy string,
so the split is stable across runs and cannot drift as the corpus grows. Until that split
existed, `--check` scored the decoder on the pairs it had trained on and reported 84%, which
measured memorisation. **Ignore any number in this file's history above 50%.**

**`intensive/work/` is not usable as study material and must not be baked into the reader.**
Half the words are wrong, and a wrong decode is not a garbled string — it is a well-formed
Telugu word that is not the one on the page.

### What was tried, and what each was worth

| change | held-out words |
|---|---|
| one code → one Telugu segment, EM | — (pre-split; ~45% train) |
| fixed the initialiser: it seeded word-prefixes only, starving mid-word segments | — |
| bootstrap against `data/master_*.tsv` — keep decodes that land on a real word, retrain | — |
| **units of up to 3 legacy codes, not 1** | the single biggest jump |
| units of up to 5 — `Ææÿ$` is four codes and spells రు | + |
| beam search over segmentations instead of longest-match | + |
| 182 → 1,205 parallel lines (the drills of lessons 1–6 were never being read) | + |
| 647 inline glosses from the grammar notes of all 64 lessons | + |
| pruning units EM rarely routes through (`MINUSE`) | **47.8% → 46.6%: no help** |
| beam 24 → 60 → 150 | **identical. Search is not the bottleneck** |

Two decode-time tie-breakers were swept and both lost: a bonus per source code consumed
(−1.4%) and a bonus per character emitted (−22.6%). Log-probability alone wins.

### The diagnosis

**The model cannot fit its own training data (63.8%).** That is the number that matters, and it
rules out the comfortable explanations — it is not the held-out split being unlucky, not the
beam being narrow, and not a shortage of parallel text.

It is also not the model's structure. The encoding is provably concatenative and monotone:

```
AMæüPyæþ → అక్కడ      Aç³šyæþ$ → అప్పుడు
CMæüPyæþ → ఇక్కడ      Cç³šyæþ$ → ఇప్పుడు
GMæüPyæþ → ఎక్కడ      Gç³šyæþ$ → ఎప్పుడు
```

`MæüP` is క్క, `yæþ` is డ, `A/C/G` are అ/ఇ/ఎ. Those are reusable units, not memorised words, and
a monotone segmentation model can represent them exactly. Something in the estimation is
failing to find them, and four rounds of attack did not locate it.

### The answer: OCR, not decipherment

```bash
python3 tools/ic_ocr.py --check --limit 250   # score against the book's own romanization
python3 tools/ic_ocr.py                       # OCR every Telugu line -> raw/ocr/NN.tsv
python3 tools/ic_ocr.py --build               # join onto the turns -> work/NN.tsv
```

**Word accuracy 92.8%, exact line 63.6%, character similarity 92.2% — against the decoder's
48.8% on the same kind of test.** Scored the same way and against the same evidence: OCR a
Telugu line from a romanized lesson, run it through `te2rom.py`, compare with the romanization
the book printed underneath. Nothing here rests on OCR's reputation.

Needs `brew install tesseract tesseract-lang`.

#### What the settings are worth, swept rather than assumed

| | word accuracy |
|---|---|
| `--psm 7` "single text line" — the obvious choice | 82.5% |
| `--psm 6` | 82.6% |
| **`--psm 13` "raw line"** | **96.6%** |

`psm 13` bypasses Tesseract's layout analysis entirely. Those heuristics are built for page
images and actively damage a crop already known to be a single line. This was the largest single
win anywhere in this pipeline and it is one flag.

Resolution has an optimum rather than a direction: at `psm 13`, zoom 6 gives 96.6%, 8 gives
95.9%, 10 gives 93.0%. Past ~6× the strokes thicken and the vowel-length marks (ి vs ీ) close
up — the one distinction Telugu cannot afford to lose. Padding likewise: 1 → 95.2%, 3 → 96.6%,
5 → 86.4%.

#### Two measurement bugs that were understating it

Worth recording because both made a working system look broken:

1. **Crops merged across columns.** These pages set two columns at matching heights, so merging
   line fragments on y alone produced a box spanning both. `idi pustakaṁ.` came back as
   `adi gaḍiyāraṁ.` — correct OCR of the wrong box. Fragments now need to be horizontally
   adjacent as well.
2. **Unscoreable lines were being scored.** In the drills the gold romanization cannot be
   matched to its Telugu at all — the scorer was handing OCR item 1's romanization and marking
   it wrong for correctly reading item 3. Bands containing more than one Telugu line are now
   left unscored instead of counted as failures. **Measurement only** — the production path
   OCRs every line and needs no romanization.

The drill numbering (`1.` `2.`) and word-space placement are also normalised away: the Telugu
line carries numbers the romanization omits, and the book sets `rāmārāvu gāru` and
`rāmārāvugāru` interchangeably. Neither is an OCR error.

#### What did not work

**Snapping OCR output to the project lexicon cost 14 points** (92.8% → 78.7%). Standard OCR
post-correction, and wrong here: this book's vocabulary is far larger than the 5,000 words the
project has collected, so most tokens the lexicon does not recognise are correct readings of
words it has never seen, and the nearest known word is simply a different word. The same trick
helped `ic_decode.py`, where the input was a guess being checked against reality rather than a
reading already better than the reference.

#### The output

**1,868 turns across all 64 lessons. 9 have no Telugu, 44 are flagged `ocr-suspect` — 2.8%
needing a look.** 97% of the 12,798 Telugu words are well-formed script.

The flag works because **OCR fails loudly**. A line Tesseract cannot read comes back as digit
runs or stray Latin (`9206`, `[0002`), never as plausible-but-wrong Telugu. That is the exact
opposite of `ic_decode.py`, whose errors were well-formed Telugu words that happened to be the
wrong ones, and it is the whole reason this output can be trusted where the decoder's could not:
the bad lines announce themselves.

Curly quotation marks are not a defect — lesson 59 sets its dialogue in them, and an earlier
well-formedness check counted every one as a failure.

#### The seam

`ic_extract.py` owns the structure — speakers, turn boundaries, English — and never depended on
how the Telugu would be recovered. The only connection is the `keys` column (`page:y` per line),
which `--build` looks up. That is why none of the extraction work was lost when the decoder was
abandoned, and why a better OCR engine can be swapped in later without touching anything else.

## In the reader

```bash
python3 tools/build_ic_reader.py            # lessons 1-6, book-derived only
python3 tools/build_ic_reader.py --all      # every lesson, OCR included and marked
```

Writes `reader/data/intensive.js` (`window.IC_DATA`) in the same shape `build_ms_reader.py`
writes for the mini stories, and reuses its `Resolver` verbatim — so the lexicon, the verb-form
lookup, the stem+suffix decomposition and the word guids are one implementation, and a word
marked known in a mini story is already known here.

**Lessons 1-6 by default, and that is a claim about trust rather than a convenience.** Those are
the lessons whose Telugu is derived from the book's own romanization and round-trips back to it
exactly. `--all` adds lessons 7-64 at ~93% OCR word accuracy, and every line from OCR carries an
`ocr` marker so the reader can say so.

### The turn is the line

A turn carries one English translation, and several Telugu sentences often sit inside it —
`idi gōḍa. adi vākili.` is one turn with one gloss. Splitting the Telugu without splitting the
English would invent an alignment nobody wrote down. The mini stories are sentence-per-line
because LingQ supplied them that way; this book did not.

### Two bugs the integration turned up

**Story numbers collided.** The router matched `#/story/1` on `s.num`, and both datasets number
from 1, so every Intensive Course lesson was unreachable behind its mini-story twin. Stories now
carry an `id` (`ms1`, `ic1`) derived from the source name rather than array position.

**Lexicon indexes are per-dataset.** A line's tokens hold indexes into *its own* `lex`, so
merging two datasets without shifting the second one's indexes points every Intensive Course
word at whatever mini-story word sits at that index — which reads as plausible nonsense rather
than as an error. The merge offsets them.

The library heading also derived its counts from the data instead of the literal "11 of 60
stories" that was in the markup, which was already stale.

### Also not done

- Sentence splitting inside a turn, the `build_ms_reader.py` bake, and audio.
- Prose pairing is line-level and drifts wherever the two columns wrap differently.
