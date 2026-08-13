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

## Past — video 14

Not yet audited. The past stem is the one that varies most from the root, so this is the audit
with the highest chance of finding a real error.

## Habitual & future — video 19

Not yet audited.
