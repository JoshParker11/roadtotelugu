# Address and respect

The data is [address.tsv](address.tsv). This explains what it is for and how to read it.

## Why this is the first document and not an afterthought

English lets you write a whole novel without ever deciding how two characters stand relative to
each other. Telugu does not. Every line of dialogue forces a choice, and the same choice again
in every sentence that mentions someone in the third person:

- **నువ్వు or మీరు** — and the verb agrees, so it is never just the pronoun
- **వాడు / అతను / ఆయన** for one man, depending entirely on who is speaking about him
- **ఆమె / ఆవిడ** likewise
- whether a name takes **గారు**

Translate chapter by chapter without settling these and you get a book where a character's
relationship to another silently shifts between scenes. Every individual sentence passes
inspection; the dialogue as a whole is incoherent, and a native reader notices immediately even
though nothing is grammatically wrong.

This is also the failure a machine translation makes by default, because it has no memory
between paragraphs.

## The ladder

| | contempt / intimacy | neutral | respect |
|---|---|---|---|
| 2nd person | నువ్వు | — | మీరు |
| 3rd, male | వాడు | అతను | ఆయన |
| 3rd, female | అది¹ | ఆమె | ఆవిడ |

¹ Listed for completeness. **Do not use అది for a woman in this translation** — it is genuinely
degrading and no relationship in this book calls for it.

Two things that trip up English speakers:

- **నువ్వు is not "familiar" in the French sense.** Downward — adult to child, teacher to
  student — it is neutral and carries no warmth. Warmth comes from the vocative and the verb.
- **వాడు between friends is affectionate.** Boys say it about each other constantly. It is only
  contemptuous when the relationship makes it so, which is why Snape and Ron produce opposite
  effects from the identical pronoun.

That second point matters for this book: **contempt cannot be carried by pronouns alone**, because
the contemptuous pronoun is also the friendly one. Snape's disdain for Harry has to live in
vocabulary, clipped verb endings and word choice. If a passage feels flat, that is where to work,
not on the ladder.

## Reading the file

| column | |
|---|---|
| `speaker` | who is talking. `narrator` for narration. A `*name` is a class, not a person |
| `addressee` | who they are talking to or about |
| `second` | the second-person pronoun, and by implication the verb agreement |
| `third` | how this speaker refers to that person when they are not present |
| `vocative` | the calling-word, where one is characteristic |
| `note` | why, and whether it is a judgement call |

**Matching order: most specific wins.** Look for an exact `speaker`/`addressee` pair first; fall
back to the classes (`*any`, `*adult`, `*child`, `*teacher`, `*student`); the five default rows at
the top of the file cover everything else. The matrix does not need to be complete — it needs to
cover the pairs that recur and the ones where the obvious answer is wrong.

Narration takes its respect level from the `respect` column of
[glossary.tsv](glossary.tsv), not from here.

## The four calls worth arguing about

These are in the file with `DELIBERATE` or an explanatory note. Revisit them at the end of
chapter 1, while changing your mind is still cheap.

1. **Vernon నువ్వు → Petunia, Petunia మీరు → Vernon.** The traditional Telugu marital asymmetry.
   Modern urban couples often use నువ్వు both ways, and that would be the defensible alternative.
   The asymmetry was chosen because the Dursleys are conventional and status-anxious to the point
   of parody, and it renders that in one word. If it reads as dated rather than characterising,
   flatten it.

2. **McGonagall uses మీరు to Hagrid.** She outranks him considerably and నువ్వు would be
   unremarkable. Scrupulous correctness with everyone regardless of station is precisely who she
   is, and Telugu can show that where English cannot. Risk: it may read stiff.

3. **Ollivander uses మీరు to Harry.** An adult shopkeeper addressing an eleven-year-old would say
   నువ్వు. The upgrade makes him faintly unnerving, which fits the scene.

4. **Harry keeps మీరు with Hagrid all the way through.** Correct Telugu — adults keep మీరు however
   close the friendship — but English readers expect the friendship to close the gap, and it never
   does. Leave it. This is one of the places the translation teaches you something true about
   Telugu that the original cannot.

## Adding to it

New character, or a pair that is not covered and where the default is wrong: add a row. Put the
reasoning in `note`, not in your head. If you cannot decide, take the neutral option, mark the
segment `status=query`, and add it to `review/questions.md` — address is exactly the kind of
question a native speaker answers instantly and reliably.
