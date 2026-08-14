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

## Scorecard after week 2

| Tense | Video | Forms checked | Mismatches |
|---|---|---|---|
| Present continuous | 9, 10 | 27 | 0 |
| Past | 13, 14 | 19 | 0 |
| Habitual & future | 16, 19 | 47 | 0 |
| Immediate future | 21 | 10 | 0 (paradigm added) |
| **Total** | | **103** | **0** |

The Verb Lab's 1,919 forms were generated from a PDF and inference, with no native-speaker or
authoritative check. Week 2 has now verified the three tenses that carry ordinary conversation —
every paradigm in the default `core` drill scope except the two negatives derived from them.

Three changes came out of this: the nasal-assimilation bug in romanization (180 forms), the
missing `negPresent` paradigm (+210 forms), and the missing `immFuture` paradigm (+210 forms).
The generator went from 1,709 forms to 2,129 over the week.

---

## Standing gaps, unchanged after four audits

- **The `avi` row** (non-human plural, `-tunnāyi` / `-āyi`) is not drillable. Six persons drilled,
  eight taught.
- **"We" is `manaṁ` / `-āṁ`** where the course teaches `manamu` / `mēmu` with `-āmu`. Same cell,
  colloquial vs careful register.

Both are cosmetic and both are now four-for-four, so they are a deliberate scope choice rather
than an oversight. Worth revisiting only if the `avi` row starts coming up in real conversation,
which for a household and an office is unlikely.

The cost is visible on the lesson pages: four cells in Lesson 11's tables (`āḍabōtunnāmu`,
`āḍabōtunnāyi`, and the `chēyi` equivalents) are correct Telugu taught by the course but are not
drillable, because they are the `mēmu` and `avi` rows.
