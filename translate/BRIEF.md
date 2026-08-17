# The brief

**Read this first if you are picking up the translation cold** — a new assistant, a new session,
or me six months from now with no memory of any of it.

Everything here is either the ethos, a pointer, or a worked example. The rules themselves live in
the other documents; this tells you which one to open and what mistake you are about to make.

---

## 1. What this is, in one paragraph

A meaning-for-meaning Telugu translation of the first Harry Potter book, made as a **study text
for one specific beginner**, not as a publishable translation. The reader already knows the story
in English, which is the whole point: when the Telugu defeats him he can reconstruct the meaning
from memory and keep reading. Two consequences follow from "study text", and almost every rule in
this project is one of them:

1. **Proper nouns stay in English, in Latin script**, so he always knows where he is. A real
   translation would never do this. We do it deliberately, trading naturalness for navigability.
2. **The Telugu around those names has to be worth learning** — natural, standard, and consistent
   with the Anki deck he studies, because new vocabulary flows back into it.

The bottleneck is not producing Telugu. It is that the reader **cannot yet evaluate the output**.
So the project's real work is making the checkable things checkable and the unjudgeable things
consistent — so that when a native speaker eventually reads it, their corrections apply to the
whole book rather than to one page.

## 2. The ethos, stated as five commitments

- **Consistency beats elegance.** A slightly stiff choice made the same way 200 times is worth
  more than 200 individually better choices that disagree. The reader cannot detect inconsistency;
  it is therefore the most dangerous error, and the one every rule here is guarding against.
- **Never stall.** Stuck on a sentence? Translate it the plain way, set `status=query`, write the
  question down, move on. A chapter dying on one clause is the actual failure mode.
- **Write the reasoning down, not just the answer.** Every document here is append-only for this
  reason. "Why" survives; memory does not.
- **Say when you are unsure.** The reader cannot check you. An unmarked guess is worse than an
  admitted one, because it propagates silently.
- **Don't translate the whole book unattended.** See §7.

## 3. Where everything is

Read in this order. The first two are mandatory before writing a single sentence.

| | what it settles |
|---|---|
| **[STYLE.md](STYLE.md)** | Register, dialect, the three-bucket rule, **the stitching convention (§4)**, prose and dialogue rules |
| **[ADDRESS.md](ADDRESS.md)** + [address.tsv](address.tsv) | నువ్వు vs మీరు, వాడు/అతను/ఆయన, per speaker–addressee pair |
| **[glossary.tsv](glossary.tsv)** | The anchor terms. Also gender and narrator respect level, which the verb agreement depends on |
| **[DECISIONS.md](DECISIONS.md)** | Calls already made, and the open questions still to settle |
| **[README.md](README.md)** | Workflow, tooling, what is committed and why |
| `work/chNN.tsv` | The actual segments. Gitignored |
| `source/hp1_en.txt` | The English. Gitignored, in copyright |

`../review/questions.md` is where native-speaker questions accumulate.

**STYLE.md §4 is the part nothing else will tell you.** It is the convention for attaching Telugu
morphology to Latin-script names, and it is unique to this project.

## 4. The compressed version

If you only retain seven things:

1. **Anchors stay English.** Names, spells, houses, Quidditch terms, coinages — exactly the list
   in `glossary.tsv`, no per-sentence judgement.
2. **Three buckets, not two.** Anchor (Latin) · transliterate into Telugu script (a common noun
   with no Telugu word — డ్రాగన్) · translate (a common noun that has one — మంత్రదండం). A wand is
   not a proper noun. If every object stayed English there would be nothing left to learn.
3. **Bound suffix → hyphen. Free word → space.** `Harry-కి`, `Muggle-లు`, `Hogwarts-లో`, but
   `Harry కూడా`, `Dursley గారు`, `Harry అనే అబ్బాయి`. The closed suffix list is in STYLE.md §4.
4. **The stem is always the English base form.** `Muggle-లు`, never `Muggles`.
5. **Verb last, every clause.** A verb in the middle means English wearing Telugu words.
6. **Address comes from address.tsv, not from instinct.** This is where an LLM fails by default —
   see §6.
7. **Standard written వ్యావహారికం.** Not గ్రాంథికం. Hagrid is the one character who gets
   nonstandard forms.

## 5. A worked example

The opening of chapter 1, as translated. This transmits the style faster than the rules do.

> **EN** — Mr. and Mrs. Dursley, of number four, Privet Drive, were proud to say that they were
> perfectly normal, thank you very much.
>
> **TE** — Privet Drive-లో నాలుగో నంబరు ఇంట్లో ఉండే Mr. Dursley, Mrs. Dursley దంపతులు — తాము
> పూర్తిగా మామూలు మనుషులమని గర్వంగా చెప్పుకునేవాళ్ళు, ఆ మాట మీద ఎవరైనా అనుమానం వ్యక్తం చేయడానికి
> వీల్లేదన్నట్టు.

What to notice: `Privet Drive-లో` (locative, hyphen). `Mr. Dursley` keeps its English title and
gets no గారు on top. దంపతులు carries "Mr. and Mrs." better than repeating both names. And "thank
you very much" — which is defensive pride, not thanks — becomes a whole clause, because there is
no Telugu idiom for it. **That is what meaning-for-meaning means here.**

> **EN** — Mr. Dursley was the director of a firm called Grunnings, which made drills.
>
> **TE** — డ్రిల్లు యంత్రాలు తయారుచేసే Grunnings అనే సంస్థకు Mr. Dursley డైరెక్టరు.

The English relative clause moves to the *front* as a prenominal participle. The whole sentence
inverts. `Grunnings అనే సంస్థ` — అనే is a free word, so a space.

> **EN** — None of them noticed a large, tawny owl flutter past the window.
>
> **TE** — ఒక పెద్ద, గోధుమరంగు గుడ్లగూబ కిటికీ పక్క నుంచి రెక్కలు కొట్టుకుంటూ ఎగిరిపోవడం వాళ్ళలో
> ఎవరూ గమనించలేదు.

An owl is a common noun with an ordinary Telugu word, so it is **not** an anchor — గుడ్లగూబ.
Bucket three. And the whole English clause becomes a nominalised object of one final verb.

## 6. How an LLM gets this wrong

Specific, observed, and worth checking yourself against:

- **Address drift.** You have no memory between paragraphs, so you will pick నువ్వు or మీరు afresh
  each time and a relationship will silently shift mid-chapter. Every individual sentence passes;
  the dialogue as a whole is incoherent, and a native reader sees it instantly. **Look the pair up
  in address.tsv every time.**
- **Transliterating the anchors.** The overwhelming default is to render Harry as హ్యారీ. Do not.
  It is the single most visible violation.
- **Anchoring too much.** The opposite failure. "Culture-bound object" read broadly swallows every
  noun in the book. Anchor only when Telugu has no word *and* substituting one would change the
  scene.
- **Word-for-word under the label of meaning-for-meaning.** If your Telugu sentence count and
  clause order match the English exactly, you have not restructured it. Split and merge freely
  inside a segment; just never add or remove content.
- **Inventing speech-tag verbs.** English has chortled, snapped, piped, spat. Telugu does not, and
  coining equivalents reads badly. Use అని + an ordinary verb + a manner adverb.
- **Forgetting the verb goes last** in subordinate clauses specifically, even when you got it right
  in the main clause.
- **Contempt via pronoun alone.** వాడు is both the contemptuous *and* the affectionate form. Snape
  and Ron use the identical pronoun to opposite effect. Disdain has to live in vocabulary and
  clipped verb endings.

## 7. What not to do

**Do not generate the full book unattended.** Two reasons. It is an in-copyright novel and a
complete translation is a complete derivative work — the project keeps it private and gitignored
for exactly this reason, and mass-generating it is a different act from helping with a passage.
And the owner learns nothing from prose he did not fight for; the hours are the point.

The useful shape is: **he drafts, you review** — checking stitching, arguing register, catching a
dropped clause, running the back-translation. Producing a worked model of a passage to demonstrate
a convention is fine and useful. Producing chapters 2 through 17 is not.

## 8. Telugu demands information English withholds

Discovered while translating, and the reason a translation cannot be mechanical. Watch for these —
each one is a question the English simply does not answer:

| English says | Telugu forces you to know |
|---|---|
| sister, brother | **relative age** — అక్క/చెల్లి, అన్న/తమ్ముడు |
| we | **inclusive or exclusive** — మనం (with you) vs మేము (not you) |
| you, he, she | **respect level**, and the verb agrees |
| a cousin, an aunt | **which side of the family**, often |

The first of these already bit: "Mrs. Potter was Mrs. Dursley's sister" required knowing Lily is
the younger — చెల్లి — a fact the sentence does not contain. It is logged in the chapter 1 notes
as a query. **When one of these appears and the source does not settle it, do not quietly pick
one.** Mark `status=query` and write the question down; a global assumption made silently is
expensive to unwind.

## 9. Before you hand anything back

```bash
python3 tools/check_hp.py --ch N
```

It verifies anchor preservation, stitching, stray English, source drift and status coherence. It
cannot tell you the Telugu is good — nothing can — but it will not let you hand back something
inconsistent. Run it. Then say plainly which segments you were unsure about.
