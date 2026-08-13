# Importing into Anki

Two files, generated from the masters by `python3 tools/build_exports.py`:

| File | Rows | Note type | Deck |
|---|---|---|---|
| `anki/import_words.txt` | 1,995 | `Telugu Production` | `Telugu::Vocab` |
| `anki/import_sentences.txt` | 2,872 | `Telugu Sentence v3` | `Telugu::Sentences` |

Both carry `#notetype`, `#deck`, `#guid column` and `#tags column` headers, so Anki configures
the import itself — you should not have to set anything on the import screen except the
duplicate-handling mode in step 4.

**The import is idempotent.** Rows are matched on the guid column, not on the first field. Fix
something in the master, re-export, re-import, and the existing note is updated in place. That
is what makes this safe to redo, and it is the reason not to edit cards inside Anki — those
edits are overwritten on the next import. Corrections go in `data/master_*.tsv`.

> ### One-time break: the guid scheme changed on 2026-08-13
>
> The guid used to be the row number — `W0519`. That works until the master changes length.
> Dropping a single bad entry renumbers every row after it, so `W0519` stops meaning తను and
> starts meaning నివసిస్తున్నారు. Anki matches the guid, finds the note, and **overwrites it
> with a different word while keeping its scheduling.** Measured on one real rebuild:
> **1,431 of 1,927 shared guids had come to point at a different word.**
>
> Guids are now derived from the Telugu script (`tools/ids.py`), so the same word keeps the
> same id forever no matter what else enters or leaves the master. Verified: dropping an entry
> now moves **0** guids, where the old scheme moved 1,431.
>
> Because none of the new guids match the old ones, **the notes already in your collection
> cannot be updated in place — they have to be replaced once.** Do the clean sweep in step 3
> below. The deck is young enough that this costs almost nothing now and gets much more
> expensive later. This is also where your 95 orphaned notes came from.

---

## 1. Back up first

**File → Export → Anki Collection Package**, tick *Include media*. You have 4,588 existing
notes and 25 of them are in live decks; this takes a minute and makes every later step
reversible.

## 2. Add the `EnglishAudio` field

Only `Telugu Sentence v3` needs changing. `Telugu Production` already has exactly the right
five fields.

**Tools → Manage Note Types → Telugu Sentence v3 → Fields → Add** → name it `EnglishAudio`
→ select it → **Reposition** → `2`.

Field order must end up exactly:

```
1. English        2. EnglishAudio   3. Romanized
4. Telugu         5. Audio          6. Notes
```

Anki maps import columns to fields positionally. If `EnglishAudio` sits anywhere but position
2, every field after it lands in the wrong slot.

## 3. Delete every note in the two target note types

Not just the old experiments this time — **everything**, including what you imported earlier
this week. The guid scheme changed (see the note above), so those notes can no longer be
matched and updated; leaving them in place would give you two copies of every card.

Nothing is lost. Every one of them came from the masters, and the masters are unchanged by
this — you are re-importing the same content with ids that will survive the next rebuild.
What you do lose is the scheduling on the ~29 cards you have reviewed, which is a day of
work against a bug that would otherwise corrupt the deck silently every time it grows.

In the Browse window, search each of these, select all (⌘A), and delete:

```
note:"Telugu Production"
note:"Telugu Sentence v3"
```

Leave the `~Archive::` decks alone for now. Their content is in the masters too, but keep them
until you have confirmed the new decks look right.

## 4. Import

**File → Import** → `anki/import_words.txt`, then again for `anki/import_sentences.txt`.

On the import screen check three things:

- Notetype and Deck are pre-filled from the file headers
- **Existing notes: `Update`** — this is what makes re-imports update rather than duplicate
- *Match scope* mentions the guid, not the first field

Expect **2,010 new notes** then **2,872 new notes**. If Anki reports a large number of
*updated* notes on a first import, something is matching unexpectedly — stop and check.

## 5. Set a sane pace

You have just added 4,882 new cards. The export is already in study order — course material
first, then sentences sorted by how much of each you already know — and Anki introduces new
cards in import order, so the order needs no further work.

What needs setting is the daily limit. **Deck options** for each deck:

- `Telugu::Vocab` → new cards/day **10**
- `Telugu::Sentences` → new cards/day **5**

That is ~15 new cards a day, which at your two hours is sustainable and still gets you
through the core in a few months. Raise it after a fortnight if reviews feel light.

If you would rather control batches explicitly, suspend everything and unsuspend a set at a
time instead:

```
deck:Telugu::Sentences            → select all → suspend
tag:set::001                      → unsuspend
```

## 6. Generate the audio with HyperTTS

Do this **in batches by set tag**, not all at once — a few thousand notes in one pass is slow
and easy to interrupt halfway.

Three passes. In Browse, search, select all, then **Notes → HyperTTS → Add Audio**:

| Search | Source field | Target field | Voice |
|---|---|---|---|
| `note:"Telugu Production" tag:set::001` | `TeluguScript` | `Audio` | Telugu |
| `note:"Telugu Sentence v3" tag:set::001` | `Telugu` | `Audio` | Telugu |
| `note:"Telugu Sentence v3" tag:set::001` | `English` | `EnglishAudio` | English |

The third pass is the one that makes the commute drill work: English audio on the front means
you can be prompted without looking at the screen.

Pick one Telugu voice and stay with it. Your archived research notes make the point — a single
consistent model speaker is worth more early than variety.

## 7. Add the English audio to the Production card front

The `Production` template currently shows `{{English}}` as text only. Add the audio so it
plays automatically:

**Tools → Manage Note Types → Telugu Sentence v3 → Cards → Production**, front template:

```
{{English}}
{{EnglishAudio}}
```

The back already reveals `{{Romanized}}`, `{{Telugu}}` and `{{Audio}}`, which is the right
order for produce-then-shadow.

## 8. Check it worked

In Browse:

| Search | Expect |
|---|---|
| `note:"Telugu Production"` | 2,010 |
| `note:"Telugu Sentence v3"` | 2,872 |
| `tag:set::001` | 100 (50 words + 50 sentences) |
| `"note:Telugu Sentence v3" EnglishAudio:` | notes still missing English audio |
| `tag:known::100` | 2,315 sentences with no unknown words |

Then open one card of each type and confirm the audio plays and the fields are in the right
places.

---

## What is deliberately not in the import

89 words and 8 sentences are held back — Kannada-typeset entries, missing script, bound
suffixes, English words respelled in Telugu letters. They stay in the masters and are listed
in `review/ERRORS.md`. Once you have worked through `review/`, re-run:

```bash
python3 tools/build_master.py && python3 tools/build_sentences.py && python3 tools/build_exports.py
```

and re-import. Existing notes update in place; the held-back rows join as new notes.
