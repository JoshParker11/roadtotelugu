# Verb Lab audit — against the course's all-pronoun videos

The Verb Lab's 1,919 forms are generated from ~10 stems per verb in `GRAMMAR_LAB/data/verbs.js`.
Those stems came from the course's root-verb PDF plus my own knowledge, and until now nothing had
checked the *output* against an authoritative statement of the paradigm.

Week 2 supplies three such statements — videos 10, 14 and 19, each of which is the course reading
out a full pronoun table. This file records what each one found.

Method, per tense:

1. Dump every generated form: `node -e "…cells(v)…"`.
2. Diff the romanized half against `tools/te2rom.py` run on the Telugu half. Any disagreement is
   an internal inconsistency regardless of which side is wrong.
3. Diff the forms themselves against the video.

---

## Present continuous — video 10, audited 2026-08-13

**Verdict: the paradigm was correct. Three defects found, all in how it was rendered or what was
missing, none in the linguistics.**

### ✓ Confirmed correct

Every stem, ending and person marker matches the course across all 35 verbs. Specifically
confirmed: the four stem classes (u-stem, s-stem, n-stem, `-kō` reflexive), the retroflex `ṭ`
marker after nasal stems, and the `-tunnadi → -tōndi` contraction for she/it. The stem classes
had been derived independently from the PDF; the course confirms all four.

### ✗ 180 forms romanized with the wrong nasal — fixed

`tinṭunnānu`, `unṭunnānu`, `kūrchunṭunnānu` — dental `n` before retroflex `ṭ`. The script says
otherwise and so does `te2rom.py`: `tiṇṭunnānu`, `uṇṭunnānu`, `kūrchuṇṭunnānu`.

Cause: the non-past stem stores its romanization as a fixed string (`tin` / `తిం`), but the
anusvara it represents assimilates to whatever follows. The *same* stem is correctly `n` before
the dental of the she/it past — `తింది` `tindi` — so the choice cannot be made until the ending
is attached.

Fix: `assimilate()` in `engine.js`, applied inside `join()`. Ten of 35 verbs, every paradigm
built on the non-past stem.

### ✗ Negative present continuous was missing entirely — fixed

The Verb Lab had `negFuture` (`chēyanu`) and `negPast` (`chēyalēdu`) but not `chēyaḍaṁ lēdu`,
which is a third of this lesson.

Not a suffix on the verb: `-ḍaṁ` makes a verbal noun and `lēdu` says it is absent. It needed no
new stem data — it is `shorten(v.inf)`, the same stem the purposive already puts in the dative
(`chēyaḍaṁ` → `chēyaḍāniki`). Added as `negPresent`, person-invariant, and put in the `core`
scope, so **"the core five" is now "the core six"** in `assets/app.js` and the prose that names it.

Worth having in the same drill as `negPast` deliberately: `chēyalēdu` "didn't do" and
`chēyaḍaṁ lēdu` "am not doing" are one syllable apart and both common.

### ✗ `cc` vs `chch` — fixed

`pst:['vacc',…]` and `pst:['icc',…]` against the masters' `vachch` / `ichch`. Twelve forms. The
masters win; they are what the Anki cards say.

### △ Left open on purpose

**The `avi` row is not in the Verb Lab.** Six persons are drilled, the course teaches eight
pronoun groups, and the missing one is the non-human plural (`-tunnāyi`) — the rarest cell in the
system. Adding it means a seventh row in every table, everywhere, for one form. Not done.

**"We" is `manaṁ` with the contracted `-tunnāṁ`** where the course teaches `manamu` / `mēmu` with
the full `-tunnāmu`. Same cell, two registers. The Verb Lab shows the colloquial reduction. Note
that the ending cannot distinguish inclusive from exclusive — only the pronoun can.

### After the fixes

```
1,919 forms · 0 disagreements with te2rom.py
```

(1,709 before; the extra 210 are `negPresent` × 35 verbs × 6 persons.)

---

## Past — videos 13 & 14, audited 2026-08-13

**Verdict: clean. 19 of 19 course-attested forms match.**

This was the audit most likely to find something — the past stem is the least derivable part of
the paradigm, which is why `verbs.js` stores `pst` separately for all 35 verbs rather than
computing it. Thirteen positives and six negatives are stated outright across the two videos,
including every awkward case: `vachchānu`, `kūrchunnānu`, `chadivānu`, `chūsānu`,
`paḍukunnānu`, `nērchukunnānu`, `chaduvukunnānu`, and the negatives `chadavalēdu` and
`paḍukōlēdu`. All correct.

One thing the course gets wrong that the Verb Lab gets right: video 13 says the stem exceptions
"are the same as the ones we saw in the previous lesson on the present tense". True for the
s-stem and `-kō` classes, false for nine verbs — `chaduvu`/`chadiv`, `naḍavu`/`naḍich`,
`ivvu`/`ichch`, `rā`/`vachch`, `nilabaḍu`/`nilabaḍḍ`, `visiru`/`visir`, `eguru`/`egir`,
`naḍupu`/`naḍip`, plus the `nāṭyaṁ chēyi` compound. The separate `pst` stem was the right call.

No change needed. Confirms one existing decision too: the course states outright that Telugu
does not distinguish the perfect from the simple past, which is exactly why
`concepts/verb-forms-explained.md` left it out of the Verb Lab.

## Habitual & future — videos 16 & 19, audited 2026-08-13

**Verdict: clean. 47 of 47 course-attested forms match.**

The largest of the three: video 19 gives full positive *and* negative tables across all pronouns
for `āḍu`, `chēyi` and `māṭlāḍu`. Eleven first-person positives, six first-person negatives, and
thirty cells from the pronoun tables.

Two results worth naming, because neither had been checked against any source before today:

- **The she/it negative ending is `-du`, not `-di`** — `chēyadu`, `āḍadu`. `END.neg[3]` had this
  right. The video explains the reason, which is a good one: `*āḍadi` would be identical to the
  pronoun `adi` sitting next to it, so the vowel shifted to keep them apart.
- **`kūrchōnu`** matches the vowel merger the video describes for `-ō` verbs.

One ambiguity the course does not mention and the Verb Lab cannot show, since it has no `avi`
row: the `avi` negative ending is `-vu`, **identical to `nuvvu`**. `āḍavu` is both "you don't
play" and "they (things) don't play".

---

## Immediate future — video 21, audited 2026-08-13

**Verdict: 10 of 10 attested forms match — but this one required a change, not just a check.**

The immediate future was not in the Verb Lab at all. It is now, as `immFuture`.

Worth adding rather than listing because it is fully derivable from pieces the engine already
had: **plain stem + `bō` + `t` + the present-continuous endings**. It is not really a tense —
it is `pōtunnānu` ("I am going") fused on as a suffix with p softening to b, exactly as English
bleached *go* into "going to". Ten lines of code, **210 new drillable forms**.

All ten forms the video states outright come out correct, including the two that could have gone
wrong: `kūrchōbōtunnānu` and `nērchukōbōtunnānu`, where the `-ō` survives instead of becoming
`-uṇ-` as it does in the present.

It uses `v.neg`, the same stem as all three negatives — so `chēyabōtunnānu`, never
`*chēsabōtunnānu`. Four forms off one stem.

Total generated forms: **2,129**, all agreeing with `tools/te2rom.py`. Placed in the
`moods` scope, not the default `core`.

**Naming:** the course titles this "future continuous". It is not — a future continuous would be
"I will be playing". The instructor's own explanation describes the prospective/immediate future.
Named `immFuture` / "Immediate future" here.

### Open question for a native speaker

There is **no negative cell**, because the course teaches none and the ordinary negative future
(`āḍanu`) appears to cover the ground. Is *"I'm not about to ___"* expressible in Telugu, and if
so how? Until that is answered the paradigm ships positive-only.

---

## Adjectives & uṇḍu — video 23, audited 2026-08-13

**Verdict: the first real error, and it was on the most-used verb in the language.**

The engine produced all the right forms for `uṇḍu`. The *labels* were wrong. The row the engine
calls `past` — `unnānu · unnāvu · unnāḍu · undi · unnāru` — is precisely what this video teaches
as the **present**: `nēnu santōṣangā unnānu`, "I am happy, right now". And the row labelled
`future` is the **general-fact present**: `Hyderabad vēḍigā uṇṭundi`.

Telugu splits English "is" into an observation now (`undi`) and a standing property
(`uṇṭundi`). Those two rows *are* the split. Nothing about them is past or future.

Left alone the drill would have cued `unnānu` as **"I waited"**. It means **"I am"**. That is not
a cosmetic mislabel — it is a card teaching the wrong meaning for the highest-frequency verb in
the deck, and the one whose forms are already scattered through the existing collection.

**Fix:** a per-verb `cueOv` map in `verbs.js`, read by `cue()` in `engine.js`. Six lines. Chosen
over special-casing the tense machinery, which is correct for the other 34 verbs — the problem is
that one verb's semantics do not fit the labels, not that the labels are wrong in general.
`uṇḍu` now cues *"I am ___ (right now — an observation)"* and *"I am ___ (in general — a standing
fact)"*, and its `note` says the headings lie.

### Question for a native speaker

The captions give "vikramgad" for **"sad"**. `vichārangā` fits the sounds and is correct Telugu;
`bādhagā` is likely commoner in Hyderabad. Which does she reach for?

---

## The conjugation PDF — video 22's resource, audited 2026-08-13

**Verdict: one real error, and it was the biggest one yet.**

Video 22 links a PDF, *Telugu Verb Conjugations* (bhashafy.com): 18 verbs over 36 pages, a
positive and a negative grid each. `tools/parse_conjugations.py` reads it positionally — the
text layer splits cells mid-word and interleaves the columns — and recovers **880 cells**.
`tools/check_conjugations.py` diffs them against the generator.

**Compare rows, not cells.** A first pass compared cell against cell and reported 375
disagreements, nearly all four systematic things wearing 375 faces. A Telugu form is a stem plus
an ending and those fail independently: a wrong stem breaks six cells while every ending stays
perfect. Splitting them gives 612 comparable cells in 102 rows, **69 rows clean outright**, 25
more differing only in the stem.

### The finding: `lēdu` inflects

For every other verb the negative past is one invariant form. For `uṇḍu` it takes person
markers — `lēnu · lēvu · lēḍu · lēdu · lēmu · lēru` — and the PDF and video 22 agree on this.
`verbs.js` carried a single flat override.

These are high-frequency: `lēru` is what you get told on the phone. **Fixed** — `ov` now accepts
a six-cell array, and `invariantFor()` tells the paradigm tables to stop printing "↑ unchanged"
for this verb only. Every other verb still renders as invariant.

### Where the PDF is wrong and the generator is right

- **Missing gemination**: `ich-ānu`, `vach-āmu`, `kūrchun-ānu` for `ichchānu`, `vachchāmu`,
  `kūrchunnānu`.
- **Vowel length**: four verbs print `-ṭondi` where the PDF's own summary table says `-tōndi`.
- **Find-and-replace damage**: four pages were cloned from the Play page with "āḍu" replaced by
  the new root, and the replace ran over the body text — the Drink page prints the pronoun
  `Vāḍu` as "Vtāgu" and the he-row ending `-āḍu` as "-tāgu". 9 cells.

### Deliberate differences, not errors

- **The `-va-` glide**: PDF `kūrchō-ḍam-lēdu`, ours `kūrchōvaḍaṁ lēdu`. Both heard; ours is the
  standard written form. Four verbs. **Worth asking about.**
- **"We"**: PDF `-āmu` (manamu), ours `-āṁ` (manaṁ). 49 cells, the standing scope choice.
- **Nasal assimilation**: PDF `kūrchun-ṭānu`, ours `kūrchuṇṭānu`. Notation, not pronunciation.
- **Stem contraction**: PDF `veḷḷu-tunnānu` and `cheppu-tunnānu` in full where we contract to
  `veḷtunnānu` / `cheptunnānu`. Ours is what the videos say and what Hyderabad speaks.

---

## Scorecard after week 2

| Tense | Video | Forms checked | Mismatches |
|---|---|---|---|
| Present continuous | 9, 10 | 27 | 0 |
| Past | 13, 14 | 19 | 0 |
| Habitual & future | 16, 19 | 47 | 0 |
| Immediate future | 21 | 10 | 0 (paradigm added) |
| Adjectives & uṇḍu | 23 | 7 | forms 0, **labels wrong** |
| Conjugation PDF | 22 + resource | 612 | **1 real error** |
| **Total** | | **722** | **2 real errors** |

The Verb Lab's 1,919 forms were generated from a PDF and inference, with no native-speaker or
authoritative check. Week 2 has now verified the three tenses that carry ordinary conversation —
every paradigm in the default `core` drill scope except the two negatives derived from them.

Three changes came out of this: the nasal-assimilation bug in romanization (180 forms), the
missing `negPresent` paradigm (+210 forms), and the missing `immFuture` paradigm (+210 forms).
The generator went from 1,709 forms to 2,129 over the week.

---

## Standing gaps, unchanged after six audits

- **The `avi` row** (non-human plural, `-tunnāyi` / `-āyi`) is not drillable. Six persons drilled,
  eight taught.
- **"We" is `manaṁ` / `-āṁ`** where the course teaches `manamu` / `mēmu` with `-āmu`. Same cell,
  colloquial vs careful register.

Both are cosmetic and both are now six-for-six, so they are a deliberate scope choice rather
than an oversight. Worth revisiting only if the `avi` row starts coming up in real conversation,
which for a household and an office is unlikely.

The cost is visible on the lesson pages: four cells in Lesson 11's tables (`āḍabōtunnāmu`,
`āḍabōtunnāyi`, and the `chēyi` equivalents) are correct Telugu taught by the course but are not
drillable, because they are the `mēmu` and `avi` rows.

All open native-speaker questions from every lesson are consolidated in `review/questions.md`.
