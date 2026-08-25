# Decisions

Append-only. Calls made once and applied to all 62 lessons. Anything decided for a single
sentence belongs in that row's `notes` column, not here.

---

## 1. Proper nouns are transliterated into Telugu script, not anchored in Latin

**Decision.** `Mike` → మైక్, `Dustin` → డస్టిన్. Recorded in [names.tsv](names.tsv), which is to
this project what `glossary.tsv` is to the novel. 225 distinct names, 1,711 occurrences.

**Why this differs from `../translate/`.** The novel keeps names in Latin script and stitches
Telugu morphology onto them with a hyphen (`Harry-కి`). That convention buys *navigability* —
knowing where you are in 77,000 words you already know in English. Three arguments say it does
not transfer here:

1. **Nothing to navigate.** A Mini Story is forty-odd sentences. You cannot get lost in it.
2. **The deck is pure Telugu script.** Of 2,215 rows in `data/master_words.tsv`, two contain
   Latin characters; of 2,880 sentences, nine, and those nine look like import corruption. Since
   the entire payoff is vocabulary flowing back into that deck, Latin-script anchors would
   generate entries in a form every existing card contradicts.
3. **Reading foreign names in Telugu script is a skill worth having**, and one that Hyderabad
   demands constantly. The novel can afford to skip teaching it; a beginner course should not.

**What was rejected.** LingQ's own guidance to translators is to replace the names with target-
language ones (their community sheet lists it as a task). Rejected because it breaks the
parallel-text property this project depends on: when the Telugu defeats you, the name is the
anchor you use to reconstruct meaning from the English. Change డస్టిన్ to a Telugu name and that
anchor is gone.

**Consequence.** The hyphen-stitching rule in `../translate/STYLE.md` §4 does not apply here, and
neither does its closed suffix list. Telugu morphology attaches to a transliterated name the
ordinary way (మైక్‌కి), because it is now an ordinary Telugu noun.

## 2. Register and dialect carry over from the novel unchanged

Standard written వ్యావహారికం, standard dialect rather than Telangana forms — for the same reason
given in `../translate/STYLE.md` §§1–2: the deck being studied is standard, and generating
vocabulary in a variety the deck contradicts is the one outcome worth avoiding. The novel's
single exception (Hagrid) has no counterpart here.

## 3. LingQ's own scaffolding is translated, not stripped

The `Story Twelve:` titles and the fixed line introducing the retell are kept as `part=meta` and
translated, because they are spoken in the audio and the Telugu recordings should match. The
retell line is keyed on its text alone, so **one guid covers all 60 lessons** — agreed once,
propagated everywhere.

## 4. Lesson 2 skips "Five:" in its question sequence

LingQ's source, not our parser: the raw payload has 47 lines and our TSV has 47 rows. It is the
only lesson of 62 whose ordinals are non-contiguous. `check_ms.py` must whitelist it rather than
report it forever.

---

## Open questions for a native speaker

Raised by story 1; all four are marked `status=query` in `work/01a.tsv` and `work/01b.tsv`.

| | question |
|---|---|
| breakfast | టిఫిన్ (colloquial, and what Hyderabad actually says) vs అల్పాహారం (formal). Recurs constantly across the 60 |
| "drives to work" | Telugu idiom prefers "goes in his car" — `తన కారులో పనికి వెళ్తాడు` — which drops the verb *drive*. Acceptable, or should the driving be explicit? |
| customers | కస్టమర్లు, the everyday borrowing, over వినియోగదారులు, which is right but reads like a government notice |
| the retell boilerplate | `ఇదే కథను ఇప్పుడు వేరే విధంగా చెప్తున్నాను.` — appears in all 60 lessons, so it is worth getting right once |

## 5. Third-person feminine agreement: ఆమె + -ుంది, non-honorific

Karen, Clare and the daughter take `ఆమె` and the `-ుంది` ending (`వెళ్తుంది`, `చేస్తుంది`), not the
honorific `-ారు`. A neutral narrator describing an ordinary character is the unmarked case, and
this is how Telugu prose narrates. Honorific `-ారు` would be a claim about status that the English
does not make; it is reserved for characters the narrator or another character actually defers to.

This matters more than it looks: the masculine `-ాడు` and feminine `-ుంది` paradigms are entirely
different shapes, and stories 3–5 are the first place both appear. Getting the pairing wrong once
would teach it wrong sixty times.

## 6. Story 4's retell changes SPEAKER, not just person

Most retells move third person to first for the same subject. Story 4 does something else: the
story is narrated by a parent ("My daughter goes to school") and the retell is spoken by the
daughter ("I go to school"). So `నా కూతురు` → `నేను`, and `వాళ్ళు` → `మేము` where the daughter
includes herself.

Worth flagging because it breaks the assumption the QC leans on. The checker handles it — a name
or pronoun opposite a name or pronoun is a person shift whatever the forms — but a translator
working line by line could easily produce a first-person retell of the *parent*, which would be
fluent, consistent, and wrong.

## 7. Open: there is no term glossary yet, only a name list

`names.tsv` covers proper nouns. It does not and cannot cover the recurring common vocabulary that
actually needs pinning: breakfast, customers, homework, hobby, school subjects. `ms_names.py`
correctly refuses to list `math`/`science`/`history` because they appear lowercase in the body —
they are common nouns, not names — but they still need one agreed Telugu rendering across sixty
lessons.

The novel solves this with `../translate/glossary.tsv`. This project needs the equivalent, built
from the terms that actually recur once more stories are drafted. Until it exists, term
consistency across lessons is unenforced — the checker can only compare a story against its own
retell, never lesson 4 against lesson 40.

## 8. Audio: Azure Neural TTS (te-IN-ShrutiNeural / te-IN-MohanNeural), one file per segment

**Considered and rejected:**

- **NotebookLM.** Not a text-to-speech API — it writes and narrates a scripted two-host summary
  from source documents. No way to hand it 47 fixed sentences and get 47 fixed clips back in the
  same order.
- **Google Cloud TTS** (the engine behind one of HyperTTS's main options). Checked twice against
  the current voice list: **no Telugu voices at all.** Not low-quality — absent.
- **Language Reactor's own import-and-narrate.** It does its own machine translation and TTS when
  fed English text, which would discard the checked translation, the person-shift pairing and
  every glossary decision in favour of an unverified auto-pipeline for a language LR barely
  supports. Audio is generated by us and brought into LR as synced media, not generated by LR.
- **ElevenLabs.** Markets Telugu explicitly and has the largest voice library, but the free tier
  is 10k characters/month — the full corpus would need a paid tier — and, like Gemini, it is a
  general multilingual model rather than a Telugu-specific one.
- **Gemini TTS** (2.5/3.1 Flash Preview). Telugu confirmed supported, and its steerable delivery
  ("read this slowly, like a patient teacher") is a real capability Azure's SSML controls don't
  match — genuinely worth a side-by-side later. Not the default because it is preview-stage and a
  general 24-language model, not a Telugu-specific one, on the one axis (pronunciation) the
  listener cannot yet judge for themself.

**Why Azure won.** `te-IN-ShrutiNeural` and `te-IN-MohanNeural` are GA (not preview), and are
purpose-built Telugu voices trained on native Telangana/Andhra Pradesh speaker recordings, not a
general-purpose model's best effort at a language it wasn't specifically tuned for. That
distinction matters more for audio than it did for the translation model, because pronunciation
is the one axis of quality even a fluent-Telugu-reading native speaker's later review cannot fully
substitute for — you need to have *heard it said correctly* to reproduce it, and you cannot yet
tell correct from confidently wrong by ear.

**Granularity: one file per segment**, `ministories/audio/<guid>.mp3`, matching every other guid-
keyed artefact in this project. A mispronounced sentence costs one regenerated file, not a
relisten-and-find-it inside a whole lesson recording, and the same files are directly reusable as
Anki clips later without re-cutting anything.

**Delivery rate slowed 12% below Azure's default** — the point of the Mini Stories is being able
to actually hear the story/retell/question structure, not just have it technically spoken at
native conversational speed.

## 9. Language Reactor import: one continuous audio file + two authored SRT tracks per story

LR's dual-subtitle player is fed **two SRT files you supply** — target and native, same
timestamps — alongside a media file. That is the path used here, because it is also the path
that never touches LR's own machine translation: both tracks are ours, so there is nothing left
for LR to translate. `tools/ms_lr_export.py` builds all three files per story from the same
guid-keyed data everything else in this project already uses.

**Play order is by story number, not by file.** Story one is split across 01a/01b/01c because
that is how LingQ split it, but a listener wants one continuous recording: title → story → the
retell-intro line → retell → questions.

**Meta rows are classified by content, not by their `seq` column.** `seq` is numbered per file,
and story one's retell-intro line lives alone in 01b.tsv, where it is — correctly, for that file —
`seq=1`, the same value the title carries in 01a.tsv. A first version sorted on `seq` and placed
the retell-intro line second in the whole recording, right after the title, before any story line.
Fixed by reusing `ms_segment.py`'s own `RETELL` pattern to ask "is this the retell-intro line"
directly, rather than inferring it from position.

**Silence is inserted between clips, not left to the clips themselves.** Each segment was
synthesized alone and butts against a hard edge. A short gap between sentences and a longer one
at a genuine section change is the acoustic equivalent of a paragraph break — nothing is
fabricated in the text, only in the pacing of already-real speech.

**Concatenation goes through ffmpeg's filter graph, decoding and re-encoding once, not the concat
demuxer's stream-copy path.** Stream-copy only glues cleanly when every input shares identical
codec parameters, which is not guaranteed across the two audio-generation paths this project
supports (`ms_audio.py`'s direct Azure calls vs. HyperTTS's batch export). A first draft used
`len(inputs)` — a flat CLI-argument list — as ffmpeg's stream index, which drifts as soon as a
4-token lavfi silence input and a 2-token file input are mixed; fixed with a counter incremented
once per actual `-i`.

I haven't hands-on-verified Language Reactor's exact import dialog wording — it needs a logged-in
account. Confirm the concrete steps once the first story is actually tried.

## 10. A third output, `.bilingual.srt`, for players that accept only one subtitle file

Tried against Language Reactor's actual "Media file" tool and confirmed by hand: it takes exactly
one subtitle upload, plus a Study-language/Native-language picker that almost certainly drives
its *own* auto-translation for whatever counts as the second line — not a slot for a second file
we supply. Handing it only the Telugu track would silently replace the checked, deliberate English
(the "doesn't speak French" → "ఫ్రెంచ్ రాదు" kind of call) with a fresh, unverified machine
back-translation.

`ms_lr_export.py` now also writes `story_NN.bilingual.srt` — one file, two lines per cue (Telugu
first, English second), same timestamps as the separate tracks. Whatever accepts a single SRT
gets both languages verbatim, with nothing left for the player to translate on its own.

Also worth recording: the "Media file" tool needed no login, offered no save/library affordance,
and does not appear to be account-persistent — which does not fit "study this like LingQ" (a
library entry that survives and follows you across devices). `My texts`, a separate tab in LR's
own navigation, looks like the more likely fit for that but requires being signed in to inspect,
so it hasn't been verified yet.

## 11. Resolved nine of the ten open questions from stories 1–5 — by checking the deck first

The right move turned out not to be guessing harder, and not waiting for a native speaker either:
**check `data/master_words.tsv` before doing either.** That deck is the existing, already-used
vocabulary this whole project feeds — its precedent is stronger evidence than either an unaided
guess or abstract reasoning about "what sounds right," because "consistency beats elegance" means
matching what is already established beats optimizing a single sentence in isolation.

Direct deck confirmation resolved six outright: టిఫిన్ (breakfast), రాదు (the "doesn't speak
French" idiom), విసుగు (bored), సైన్స్/చరిత్ర (the mixed borrowed/native pattern for school
subjects), and అక్క/చెల్లి (Telugu's lexically distinct elder/younger sister terms, confirming
అక్క was correct for Clare specifically because she is stated as older). Three more were resolved
by grammar or by the register commitment already on record rather than deck precedent, and are
recorded as such rather than dressed up with false certainty: the reflexive చేసుకుని (a genuine
grammar fact, not a preference), keeping the causative చేయిస్తుంది (matches the force level the
English "makes him do" already carries), and హాబీ over వ్యాపకం (no deck precedent either way,
resolved by the వ్యావహారికం register decision alone — weaker evidence, flagged as such in that
row's notes).

**One changed the actual translation, not just the note**, and the process is worth recording
because it caught a real mistake in itself: the first pass at resolving "best friend" wrote a
note claiming a change to బెస్ట్ ఫ్రెండ్ without touching the `te` column — exactly the kind of
inconsistency this project's own tooling exists to catch, caught here by re-checking the work
rather than trusting the note. Fixed across all five occurrences of the phrase in story 4
(story, retell, and three question-part lines), not just the one row first touched.

**One is still `status=query`, deliberately**: the retell-intro boilerplate line
("ఇదే కథను ఇప్పుడు వేరే విధంగా చెప్తున్నాను."), spoken in all 60 lessons. It is a whole-sentence
naturalness judgment with no single-word deck precedent to test it against — the one genuine case
in this batch where only a person's ear can settle it, not reasoning from the evidence already on
hand. Full corpus re-checked clean (0 errors) after all ten resolutions.
