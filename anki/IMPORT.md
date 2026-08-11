# Importing into Anki

Two files, both generated. Regenerate with `python3 tools/build_exports.py`.

| File | Rows | Note type | Deck |
|---|---|---|---|
| `import_words.txt` | 2,010 | `Telugu Production` | `Telugu::Vocab` |
| `import_sentences.txt` | 2,872 | `Telugu Sentence v3` | `Telugu::Sentences` |

Both carry their own `#notetype`, `#deck`, `#separator` and `#guid column` headers, so Anki
configures the import itself. You should not have to map a single column by hand.

---

## Before you start

**1. Back up.** `File → Export → Anki Collection Package`, include scheduling, save it
somewhere that isn't the Anki folder. You have 4,588 notes and this is worth two minutes.

**2. Add the missing field to `Telugu Sentence v3`.**

`Tools → Manage Note Types → Telugu Sentence v3 → Fields → Add`, name it exactly
`EnglishAudio`, then use **Reposition** to move it to **position 2**. The final order must be:

```
1. English      2. EnglishAudio     3. Romanized
4. Telugu       5. Audio            6. Notes
```

Field order is how the import maps columns. If `EnglishAudio` ends up anywhere else, the
Telugu will land in the wrong field on every one of 2,872 notes.

`Telugu Production` already has the right five fields and needs no change.

---

## The import

`File → Import`, choose the file, and check the preview screen shows:

- **Type**: the note type named in the table above
- **Deck**: as above
- **Existing notes**: **Update**
- **Match scope**: Notes (not "Notes and deck")
- First column mapped to **Guid**, last column to **Tags**

Then Import. Words first, sentences second.

### Why the GUID column matters

Anki normally decides whether an incoming row is "the same note" by comparing the **first
field**. Our first field is the English gloss, and it is not unique: వెయ్యి, వేయి and వేల are
three real words all glossed "thousand"; ఈ రోజు and ఈరోజు are two spellings of "today". On
first-field matching Anki would silently collapse 167 word rows and 95 sentence rows into
each other and you would lose the variants.

`#guid column:1` points Anki at the master's stable id instead. Two consequences:

- Nothing collapses. Every row lands as its own note.
- **The import is idempotent.** Fix a row in `data/master_*.tsv`, re-export, re-import, and
  Anki updates that note in place. It does not duplicate. This is the mechanism that makes
  the master a real source of truth instead of a one-time dump.

So the loop for any future correction is: edit the master → `python3 tools/build_exports.py`
→ import again. Never fix a card in Anki and expect it to survive.

---

## After the import

### Generate the audio

Both audio fields are deliberately empty. In `Browse`, select the notes, then
**Notes → HyperTTS → Add Audio**, once per field:

| Deck | Read from | Write to | Voice |
|---|---|---|---|
| `Telugu::Vocab` | `TeluguScript` | `Audio` | Telugu |
| `Telugu::Sentences` | `Telugu` | `Audio` | Telugu |
| `Telugu::Sentences` | `English` | `EnglishAudio` | English |

The English pass on the sentence deck is what makes the deck usable on the bus: prompt plays
in English, you produce Telugu out loud, then flip and shadow the Telugu.

Generate Telugu audio from the **script** field, never the romanization — TTS reads Telugu
script correctly and reads `nēnu vidyārthini` as gibberish.

### Do not turn all of this on at once

2,010 words and 2,872 sentences is roughly two years of intake at 5 new cards a day. Dumping
it all into the new-card queue is how a deck becomes something you avoid.

Suspend everything, then unsuspend in bands. The tags are there for exactly this:

```
tag:known::100          sentences where you already know every word — 2,319 of them
tag:src::site           the 272 words the course actually taught, in lesson order
tag:src::book1000       the book's curated 225
tag:flag::inflected     verb forms glossed as headwords — leave suspended
deck:Telugu::Vocab -tag:src::site    everything beyond the course
```

A reasonable start: unsuspend `tag:src::site`, and sentences matching
`tag:known::100 tag:src::site`. That is a few hundred cards you have genuinely met, and it
grows as you unsuspend further bands.

### What is deliberately missing

89 words and 8 sentences are held out of these files — Kannada typesetting, missing script,
bound suffixes, English words respelled in Telugu letters. See `review/ERRORS.md`. They stay
out until a decision is recorded in the triage files, so the deck cannot teach you something
false. Re-export picks them up once they are fixed.

---

## Your old decks

The 4,561 notes under `~Archive::` have all been read into the masters — 854 words and 2,022
sentences existed **only** there and are now preserved, along with 1,134 hand-written
pronunciation guides (`NAY-noo`) and the `Island` topic groupings, which nothing else in the
project had.

So the archive is now redundant. Leave it until you have imported and spot-checked, then
delete it if you want the collection clean. Nothing in it is unique any more.
