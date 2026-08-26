# The translation prompt

The standing instruction that sits in front of **every** Mini Story translation, whichever model
does the work. Paste §1 verbatim, then the batch.

Why this exists: two different models were compared on story 2, and the differences were not
fifty independent judgement calls — they were about eight systematic policy choices, each applied
consistently down the whole text. One model had better ears (idiom, register), the other had
better discipline (structure, consistency). This prompt is the merge, so the next translation
starts from both rather than re-deriving one of them.

---

## 1. The prompt — paste this verbatim

> Translate the meaning into natural, conversational Telugu as a native speaker from Andhra
> Pradesh / Telangana would actually tell this simple story. Do not preserve English syntax or
> wording. Keep the language simple enough for a beginner, but never simplify it into unnatural
> Telugu.
>
> **Register.** Standard written వ్యావహారికం — the Telugu of newspapers, subtitles and ordinary
> speech. Not గ్రాంథికం, which would make a beginner's story read like scripture. Prefer the
> everyday spoken form over the formal one where both exist: చెయ్యక్కర్లేదు over చేయనవసరం లేదు,
> తెలియట్లేదు over తెలియదు, దాచుకో over ఆదా చేయు. Standard dialect, not Telangana-specific forms
> (ఎలా, not ఎట్ల), because the learner's flashcard deck is standard and vocabulary flows back
> into it.
>
> **Let Telugu be Telugu, especially where it differs most from English.**
>
> - **Use the dative-experiencer construction wherever Telugu naturally would.** Telugu makes the
>   person a dative experiencer where English makes them a subject. Wanting, knowing, liking,
>   being bored, being afraid, having, and language ability all work this way:
>   అతనికి వెళ్లాలని ఉంది (he wants to go), అతనికి తెలుసు (he knows), అతనికి ఇష్టం (he likes),
>   అతనికి ఫ్రెంచ్ రాదు (he doesn't speak French), అతనికి విసుగ్గా ఉంది (he is bored).
>   Do **not** flatten these into nominative subjects. This is one of the most important
>   structural facts about the language and the stories should teach it.
> - **Frame deliberation as a question to oneself**: వెళ్దామా అని అనుకుంటున్నాడు, not
>   వెళ్లాలని ఆలోచిస్తాడు.
> - **Telugu has no verb "to have."** Possession is existence: అతనికి హోంవర్క్ ఉంది.
> - **Telugu needs no copula.** An equational sentence has no "is": మైక్ వంటవాడు. Keep it that
>   way — do not convert it into a verbal sentence like "works as a cook."
> - Say things the way the language says them. A country is not ఖరీదైనది; expenses there are
>   high — ఫ్రాన్స్‌లో ఖర్చు చాలా ఎక్కువ. You నేర్చుకో a language, you చదువు a book.
>
> **Translate what is there — no more, no less.** This is a parallel text a beginner uses to
> reconstruct meaning from the English, so drift between the two columns costs more than usual.
> Do not add intensifiers, connectives or detail the English does not have ("very", "somewhere",
> "a few days") unless Telugu is ungrammatical without them. Do not drop anything either.
>
> **Structure is load-bearing. Do not tidy it.**
>
> - The questions section is a drill. Every line that begins `One:`, `Two:`, `Three:` etc. must
>   keep that ordinal in Telugu — ఒకటి:, రెండు:, మూడు:. These words are spoken in the audio.
>   **Dropping them desynchronises the recording and destroys the numbered structure.**
> - Never invent a heading. If the English has no "Questions:" line, the Telugu has none either.
> - **Keep the statement / question / answer triple in one grammatical frame.** If the statement
>   is equational (మైక్ వంటవాడు), the question must question that same frame (మైక్ వంటవాడా?) and
>   the answer must return to it. A triple whose three lines use three different constructions
>   has stopped drilling anything.
> - The story and its first-person retell must differ **only in person** — the pronoun and the
>   verb ending. If the story says చేసుకుని, the retell says చేసుకుని too. Rendering the same
>   word two ways ten lines apart is the single most damaging error here, because the learner
>   cannot detect it.
>
> **Agreement.** Ordinary third-person female characters take ఆమె and the -ుంది ending
> (వెళ్తుంది, చేస్తుంది), **not** the honorific -ారు, which would claim a deference the English
> does not make. Male characters take అతను and -ాడు.
>
> **Tense.** Use the habitual/future (-తాడు / -తుంది / -తారు) throughout, matching the English
> present. This is a standing convention for consistency across all sixty stories, not a claim
> that it is always the most natural choice — do not switch to past tense for one-off events.
>
> **Names** are transliterated into Telugu script and then inflect like ordinary Telugu nouns
> (మైక్ → మైక్‌కి). Never leave a name in Latin letters. Use the fixed spellings in the glossary
> below; if a name is not listed, transliterate by sound and flag it.
>
> **When unsure, flag — never guess silently.** A wrong translation that reads fluently is worse
> than an admitted uncertainty, because nobody downstream can catch it. Use the `note` column.
>
> **Fixed renderings — use these exactly, they are already settled:**
>
> | English | Telugu |
> |---|---|
> | Here is the same story told in a different way. | ఇదే కథను ఇప్పుడు వేరే విధంగా చెప్తున్నాను. |
> | Mike / Dustin / Karen / Clare / Jon / Amy / Julie | మైక్ / డస్టిన్ / కారెన్ / క్లేర్ / జాన్ / ఏమీ / జూలీ |
> | France / French / English (language) | ఫ్రాన్స్ / ఫ్రెంచ్ / ఇంగ్లీష్ |
> | winter | శీతాకాలం |
> | breakfast | టిఫిన్ |
> | homework | హోంవర్క్ |
> | customers | కస్టమర్లు |
> | to learn (a language) | నేర్చుకో |
> | expenses are high (for "expensive") | ఖర్చు ఎక్కువ |
>
> **Output format.** Return a tab-separated table and nothing else — no commentary, no
> explanation, no markdown fences. Exactly three columns, with this header row:
>
> ```
> guid	te	note
> ```
>
> - `guid` — copy the guid from the input row **character for character**. It is the only thing
>   linking your output back to the source.
> - `te` — the Telugu, in Telugu script. No romanization, no English.
> - `note` — leave empty when confident. When unsure, state the actual question in one line
>   ("kept X over Y because ...; confirm register"). Anything with a note gets held for review.
>
> One row of output per row of input, in the same order. Do not merge, split, reorder, or omit
> rows — the row count must match exactly.

---

## 2. How to run a batch through another model

```bash
python3 tools/ms_apply.py --pending 6        # the input: guid, part, seq, en
```

Paste §1, then that table. Take the model's TSV back, save it as `patch.tsv`, then:

```bash
python3 tools/ms_apply.py patch.tsv          # refuses to clobber existing work
python3 tools/check_ms.py --num 6 --warn     # must be 0 errors before going further
python3 tools/build_ms_reader.py             # rebake the reader
```

`check_ms.py` mechanically catches most of what the guardrails above are guarding against:
English left untranslated, question marks dropped, names missing from the Telugu, ordinals
non-contiguous, the boilerplate rendered two ways across lessons, and a word rendered two ways
between a story and its own retell. **It cannot tell you the Telugu is good** — only that it is
consistent with itself and with the English.

## 3. What it cannot check, and what to do about it

Nothing here verifies that a sentence means what it should. Story 1's cross-check found one model
rendering "he makes food" as "he eats a meal" — fluent, consistent, and wrong. The only defences:

- **Keep the flags.** A `note` is worth more than a confident blank.
- **Cross-check, but read the disagreements, not the agreements.** Two models agreeing is weak
  evidence; both were trained on similar Telugu and can be confidently wrong in the same
  direction. Where they *differ* is where the real questions are.
- **Batch the questions for a native speaker** rather than asking per sentence.

## 4. Open questions a native speaker should settle — these propagate across all sixty stories

1. **Tense.** Habitual present throughout (the current convention), or present-for-states with
   past for one-off completed events? "He decides to stay home" is a single event, and -తాడు can
   imply *he decides, characteristically*. This is the highest-value question on the list.
2. **Register depth.** Is చెయ్యక్కర్లేదు right for a text that is *read*, or does it read too
   casual on the page even though it is right in speech?
3. **శీతాకాలం vs చలికాలం** for winter. శీతాకాలం is in the deck; చలికాలం is more colloquial. If
   the answer is చలికాలం, the deck entry should change too.
4. **The retell boilerplate**, spoken in all sixty lessons — the one line where getting it right
   once fixes it everywhere.
