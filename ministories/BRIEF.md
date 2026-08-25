# The brief

**Read this first if you are picking up this project cold** — a new assistant, a new session, a
different model, or the user six months from now with no memory of any of it.

**If you were specifically handed [READER_BRIEF.md](READER_BRIEF.md)** — the build spec for the
LingQ-style reading application — read this document and `DECISIONS.md` first anyway. That brief
is deliberately just the new part; this one is the part it depends on.

Everything here is either the ethos, a pointer, a worked example, or a status snapshot. The rules
themselves live in the other documents; this tells you which one to open, what has already been
decided, and what mistake a fresh session makes by default.

---

## 1. What this is, in one paragraph

A personal, offline reading system for Telugu, built around the 60 LingQ Mini Stories — sixty
short texts LingQ released publicly for communities to translate into languages it doesn't
support (Telugu is one). Each story is told three ways: third person, then retold first person,
then broken into numbered statement/question/answer triples. That three-way repetition is the
entire teaching mechanism — it manufactures the comprehensible-context a beginner doesn't have
yet. The plan is to translate all 60 into checked Telugu, generate real audio for every sentence,
and read/listen to the result in a personal reading tool modeled on LingQ itself — because
Language Reactor turned out not to fit (see §6) and rebuilding the reading experience directly
is the call that was made.

This sits alongside `../translate/` (a Harry Potter translation, same repo, same author, very
different rules — see §3 for why they diverge). Read `../translate/BRIEF.md` once for contrast;
do not assume its conventions carry over here. Several of them are deliberately opposite.

## 2. The ethos, stated as commitments

- **Consistency beats elegance.** A plain rendering used the same way every time is worth more
  than a better one that disagrees with itself ten lines later. The reader cannot detect
  inconsistency — that is what makes it the most dangerous error, and the one every check in this
  project exists to catch.
- **Never stall, but never guess silently either.** Stuck on a word or a grammatical call? Make
  the plain choice, set `status=query`, write the actual question down, move on. A silently wrong
  guess is worse than an admitted one, because it propagates.
- **Write the reasoning down, not just the answer.** `DECISIONS.md` is append-only for exactly
  this reason — six months from now, "why" is the thing that will have evaporated.
- **The bottleneck is not producing Telugu, it is judging it.** Nobody working on this can yet
  read Telugu well enough to catch a wrong-but-fluent sentence by eye. Every tool here exists to
  make the checkable parts mechanically checkable, so that a native speaker's eventual time goes
  to the part that actually needs a human.
- **Two independent opinions agreeing is weak evidence; two disagreeing is a real signal.** This
  was tested directly — a second LLM's translation of story 1 agreed with this project's on most
  lines, and the one place it clearly erred (translating "he makes food" as "he eats a meal") was
  caught by knowing what the sentence was supposed to mean, not by the second opinion being
  independently trustworthy. Use cross-checks to find disagreements, not to manufacture
  confidence.

## 3. Why this diverges from `../translate/` on two specific points

**Names are transliterated into Telugu script (మైక్), not kept in Latin script with a hyphen
(Mike-కి) the way Harry Potter's characters are.** The novel's convention buys *navigability*
across 77,000 words the reader already knows in English. A forty-line Mini Story has nothing to
get lost in, and the Anki deck this project feeds is essentially pure Telugu script — 2 Latin-
character rows out of 2,215. Full reasoning: `DECISIONS.md` #1.

**Segments are sentences, not paragraphs.** The novel needs the paragraph as its unit because a
real translation moves information between sentences. A Mini Story is a drill wearing a story as
a costume — sentence *n* of the story becomes question *n* two sections later, and that
correspondence is the entire teaching content. Segmenting by paragraph would dissolve it.

## 4. Where everything is

| | what it settles |
|---|---|
| **[README.md](README.md)** | Provenance, licensing rationale, the tool pipeline end to end |
| **[DECISIONS.md](DECISIONS.md)** | Eleven append-only entries — read all of them, they are short. #1 (names), #5 (feminine agreement), #6 (story 4's speaker change), #7 (no term glossary yet — see §8 below), #8 (audio vendor), #9–10 (the Language Reactor export, now secondary — see §6) |
| **[CATALOG.tsv](CATALOG.tsv)** | All 62 lesson files mapped to 60 story numbers and their LingQ ids |
| **[names.tsv](names.tsv)** | 87 real proper nouns (filtered from 294 candidates — title-case lesson headings produce false positives, see `tools/ms_names.py`'s own docstring) with agreed transliterations |
| **`work/<id>.tsv`** | The actual segments — `guid`, `part` (meta/story/retell/questions), `seq`, `en`, `te`, `notes`, `status`. This is the thing you edit |
| **`audio/<guid>.mp3`** | Generated Telugu audio, one file per segment. Gitignored |
| **`source/`** | LingQ's raw English. Gitignored — not ours to redistribute |
| **`lr/`** | Concatenated per-story audio + SRT tracks, built for a Language Reactor import that turned out not to be the right destination. The *mechanism* (stitch guid-keyed clips into one continuous file with cumulative timestamps) is still exactly what the reader in `../STUDY/` wants — see §6 |

`status` ladder, same as the novel: `todo` → `draft` → `query` → `checked` → `done`.

## 5. Status right now

**Translated, checked (0 errors in `check_ms.py`), and voiced: stories 1–5, out of 60.**
**Remaining: 55 stories, fully segmented and waiting — their English is already in `work/*.tsv`
with `status=todo`.**

**Nine of the original ten `status=query` items from stories 1–5 are now resolved** —
mostly by checking `data/master_words.tsv` for existing precedent before guessing, which turned
out to be stronger evidence than either an unaided guess or waiting idle for a native speaker.
See `DECISIONS.md` #11 for the method and every individual call. **One remains genuinely open**:
the retell-intro boilerplate line spoken in all 60 lessons — a whole-sentence naturalness call
with no single-word precedent to test it against, the one item in this batch that only a
person's ear can actually settle.

## 6. Language Reactor was tried directly and does not fit — read this before suggesting it again

The original plan was: translate → generate audio → import into Language Reactor, which would
give a LingQ-like reading experience without building one. Two things killed it, found by
actually driving the tool, not by reading about it:

1. Its "Media file" import takes exactly **one** subtitle file, and its Study/Native language
   picker almost certainly drives its *own* machine translation for whatever counts as the second
   line — meaning it would silently discard this project's checked English in favor of a fresh,
   unverified back-translation of the Telugu.
2. That same tool needed no login and had no save/library affordance — it is a stateless,
   single-session local-file player, not something that persists across visits or devices. "Study
   this like LingQ" requires exactly the persistence this tool doesn't have.

**The call that followed: stop forcing Language Reactor, and finish wiring the reading experience
this repo already half-built for a different text.** See §7.

## 7. `../STUDY/` already is most of a personal LingQ — for Harry Potter, not yet for this

This is the single most important thing to know before proposing to build anything from scratch.
`../STUDY/` (read.html, words.html) already has:

- A real audio player (`reader.js`) with sentence-level seeking and transcript sync
- Click-to-look-up per word (`lex.js`), matching Telugu script directly against a word master
- Known/hard/seen/queued tracking (`progress.js`), in `localStorage`, **keyed by guid** — the same
  `hash(Telugu script)` scheme this project's `tools/ids.py` already uses
- A registry of texts (`window.READER_TEXTS`, populated from `STUDY/data/reader/*.js`,
  each holding a `lex` array), built by `tools/build_reader.py`, which already takes a `source`
  argument — it expects more than one text, it is not hardcoded to the novel

Because the guid is universal, not per-text, **a word marked "known" while reading the novel
already shows as known the moment it appears in a Mini Story** — real cross-text vocabulary
tracking, for free, with no new code. And `reader.js`'s audio model — one continuous file plus
per-line timestamps — is exactly the shape `tools/ms_lr_export.py` already produces; that tool's
output was aimed at the wrong destination, not built for nothing.

**This was scoped but explicitly not started.** The user's call this session was to focus on
translation volume and the word-explanation feature first, in chat, rather than write more
Python. Wiring `ministories/` into `STUDY/`'s existing reader is real, bounded, valuable work —
generate a `STUDY/data/reader/ministories.js` (or one per story) in the same shape `textbook.js`
already uses — and it is the natural next engineering task whenever building resumes. It is not
abandoned. It is paused.

## 8. The new thing: a Lexa-style contextual dictionary, not yet built

LingQ's own AI dictionary ("Lexa") uses named, user-editable prompt tabs — Explain / Examples /
Grammar, each a template with `<WORD>` and `<CONTEXT>` placeholders, wrapped in one shared system
sentence ("Answer questions for a student learning \[study language\]. Write your answer in
\[translation language\]."). Confirmed by the user finding LingQ's own settings screen, which
exposes this to any subscriber to edit — it is a documented, user-facing configuration surface,
not something extracted from anywhere.

**Plan, decided this session, not yet executed:**

- A fourth tab, **Forms**, pointing a verb's explanation at its actual paradigm in
  `../GRAMMAR_LAB` instead of re-deriving it from scratch each time.
- A system frame tailored to this project's own already-decided register and terminology —
  standard written వ్యావహారికం, the same case/tense vocabulary the Verb Lab already uses — rather
  than LingQ's generic framing.
- **Workshop the exact wording in chat, against real sentences from stories already translated,
  before generating anything at scale.** This is a prompt-design problem and benefits from
  iteration the way translation itself does.
- Once the wording is settled: **precompute it.** This project is a static site with no backend
  by design — a live per-click API call would mean an exposed key or new server infrastructure,
  neither acceptable. Generate an explanation for every distinct (word, sentence) pair that
  actually occurs in the corpus, once, via the batch API, and ship it as static JSON next to each
  text's `lex` array — the same offline-build-into-static-data pattern every other tool here
  already follows.
- This feature currently has **no consistency check analogous to `check_ms.py`.** That is the
  strongest argument for spending real model quality on it rather than economizing — a wrong
  grammatical explanation, delivered with the same confident tone as a correct one, is a worse
  failure mode here than anywhere else in this project, because nothing currently catches it.

## 9. The workflow, concretely

**To translate the next story:**
```bash
python3 tools/ms_apply.py --pending N        # read the English for story N
# translate; write a patch TSV: guid, te, notes, status
python3 tools/ms_apply.py patch.tsv           # apply — refuses to clobber existing work
python3 tools/check_ms.py --num N --warn      # verify before moving on
```
`check_ms.py` catches: untranslated Latin left behind, question marks dropped, names missing from
the Telugu, shared boilerplate translated two different ways across lessons, and — the check that
actually justifies the file — a word rendered two different ways between a story and its own
retell, which is invisible to a reader who cannot yet judge Telugu but is exactly the kind of
error that erodes trust in the whole corpus if it accumulates unchecked.

**To generate audio**, once translated: either `tools/ms_audio.py` (direct Azure Speech, scripted
end to end) or the `ms_hypertts_export.py` / `ms_hypertts_import.py` pair (routes through
HyperTTS Pro, which the user already pays for — one manual pass through Anki's batch generator per
run). Both land in the same place, `ministories/audio/<guid>.mp3`; nothing downstream cares which
produced a given file. `te-IN-MohanNeural` was confirmed good by ear on story 1's audio.

**To workshop the dictionary prompts:** pick a handful of words from already-translated,
already-checked stories (stories 1–5 are settled ground), try the Explain/Examples/Grammar/Forms
prompts against real `(word, sentence)` pairs from `work/*.tsv`, and iterate the wording directly
in this kind of conversation before anything is generated at scale.

## 10. Mistakes a fresh session makes by default

- **Assuming names stay in Latin script**, because that's the Harry Potter convention. Wrong here
  — see §3 and `DECISIONS.md` #1.
- **Assuming a row's `seq` number is comparable across files for the same story.** It isn't —
  `ms_segment.py` numbers `seq` per file, and story 1's split across 01a/01b/01c means its two
  `meta` rows (title, retell-intro) can carry the *same* `seq` value in different files. A real
  bug shipped from exactly this assumption; it was caught by listening to the actual audio output,
  not by reading the code. Classify by content (`RETELL.match(...)`), never by position, when the
  two might disagree.
- **Trusting that a fresh checker rule that reports zero findings has proven anything.** It hasn't
  — `check_ms.py`'s whole design was validated by deliberately injecting five known faults and
  confirming all five were caught, twice (once when the rule was too strict and threw false
  positives, once after fixing it). Any new check needs the same fault-injection test before it's
  trusted.
- **Treating a second model's agreement as confidence.** It isn't, on its own — see the ethos
  above. Disagreement is the useful signal.
- **Forgetting that `ms_names.py` deliberately excludes `part=meta` rows** when scanning for
  proper nouns — Title Case lesson headings capitalize every word, which defeats the two tests
  that separate a real name from an ordinary capitalized word (does it ever appear lowercase; is
  it ever not sentence-initial). Re-including meta rows reintroduces "Business," "Routine,"
  "Eighteen" and similar noise into `names.tsv`.
- **Proposing to rebuild the reading experience from scratch.** Don't — see §7. It already exists,
  for a different text, and the guid scheme makes extending it far cheaper than starting over.
