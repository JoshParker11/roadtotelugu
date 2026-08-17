# Style guide

The standing decisions. Anything decided once and applied everywhere lives here; anything
decided for one passage lives in [DECISIONS.md](DECISIONS.md).

---

## 1. Register: standard written వ్యావహారికం

Telugu is diglossic. గ్రాంథికం is the literary register and it is wrong for this — it would make
a children's novel read like scripture, and none of its vocabulary is usable in conversation.
Everything here is in modern standard written వ్యావహారికం: the register of newspapers, novels
and subtitles.

## 2. Dialect: standard, with one deliberate exception

Your own corpus settles this. Counting the two masters:

| standard | | Telangana | |
|---|---:|---|---:|
| ఎలా | 27 | ఎట్ల | 5 |
| ఉన్నావ్ | 4 | ఉన్నవ్ | 0 |
| ఏమిటి | 5 | ఏంది | 0 |

The deck you are actually studying is standard. Since the entire payoff of this project is that
new vocabulary flows back into that deck, the translation matches it — otherwise you generate
words in a variety your Anki cards contradict.

**The exception is Hagrid.** Rowling writes him in nonstandard West Country English, and that
is characterisation, not noise; flattening it into standard Telugu loses something real. He gets
colloquial forms — ఏంది for ఏమిటి, ఎట్ల for ఎలా, clipped verb endings. He is the only character
who does. See [ADDRESS.md](ADDRESS.md).

---

## 3. Anchor terms

Names and coinages stay in **Latin script, in English**, so you always know where you are in the
text. This is not what a published translation does; it is a deliberate trade of naturalness for
navigability, and it is the right trade for a study text.

Which terms are anchors is not a judgement call made per sentence — it is
[glossary.tsv](glossary.tsv), and the checker enforces it.

### There are three buckets, not two

This is the distinction that keeps the text from becoming English with Telugu glue:

| bucket | script | example | rule |
|---|---|---|---|
| **Anchor** | Latin | `Quidditch`, `Harry`, `Gryffindor` | It is in glossary.tsv |
| **Transliterate** | Telugu | డ్రాగన్, గోబ్లిన్ | A common noun with no Telugu equivalent |
| **Translate** | Telugu | మంత్రదండం, చీపురుకట్ట | A common noun that has one |

A wand is not a proper noun. Neither is a cauldron, a broomstick, a potion, a cloak, an owl, a
castle or a staircase — and those are exactly the words this project should be generating for
the deck. If they all stayed English there would be nothing left to learn.

**The trap is "culture-bound objects."** Read narrowly, it means *treacle tart* and *Yorkshire
pudding* — things with no Telugu equivalent that are doing work in the scene. Read broadly it
swallows every object in the book. Anchor a culture-bound item only when both are true:

1. Telugu has no ordinary word for it, and
2. replacing it with a Telugu equivalent would change the scene.

Otherwise translate it. When in doubt, translate and log it in DECISIONS.md.

---

## 4. The stitching convention

Telugu is agglutinative: case, number and postpositions attach to the noun. An anchor in Latin
script still has to take them.

### Bound suffixes attach with a hyphen. Free words take a space.

```
Harry-కి చెప్పాడు            told Harry
Hogwarts-లో                  at Hogwarts
Muggle-లు                    Muggles
Dursley-ల ఇల్లు               the Dursleys' house
Harry కూడా                    Harry too          (కూడా is a free word)
Dursley గారు                  Mr Dursley         (గారు is a free word)
Harry అనే అబ్బాయి              a boy called Harry (అని/అనే is a free word)
```

The hyphen is not decoration. It makes every inflected form of a name findable with one grep —
`grep -o 'Harry-[^ ]*'` returns the complete case paradigm — and it shows you the morpheme
boundary, which is the whole reason you wanted anchors in the first place.

**The closed list of hyphen-attached suffixes.** The checker rejects anything else glued to an
anchor:

> లు · ల · కి · కు · ని · ను · తో · లో · నుంచి · నుండి

Everything else — గురించి, కోసం, వల్ల, దగ్గర, మీద, గారు, కూడా, అనే — is a separate word with a
space before it.

### Choosing between -కి and -కు, -ని and -ను

Pick as if the anchor were pronounced in Telugu.

| | after | examples |
|---|---|---|
| **-కి** | front vowel (i, e) or any consonant | `Harry-కి` `Ron-కి` `Hagrid-కి` `Snape-కి` `Hogwarts-కి` |
| **-కు** | back vowel (a, u, o) | `Draco-కు` `Neville-కు`¹ |
| **-ని** | animate objects, default | `Harry-ని` `Fluffy-ని` |
| **-ను** | inanimate, after back vowels | `Remembrall-ను` |

¹ Neville ends in a consonant sound in Telugu (నెవిల్) — so `Neville-కి`. Judge by the Telugu
pronunciation, never by the English spelling.

### The stem is always the English base form

Telugu supplies number and case; English inflection never appears.

```
Muggle-లు        NOT  Muggles
Dursley-లు       NOT  Dursleys
Harry గది        NOT  Harry's room
```

Genitive is normally juxtaposition — `Harry గది`, `Hagrid గుడిసె`. Reach for `-యొక్క` only when
the juxtaposition is genuinely ambiguous; it is stiff.

### Titles are part of the anchor, and never doubled

`Mr. Dursley`, `Professor McGonagall`, `Madam Hooch` — keep the English title exactly as the
source writes it, and do **not** add గారు on top. One honorific per name. Use గారు only where the
source has a bare surname and the speaker is being deferential.

### Kinship terms are the one place to prefer Telugu

`Uncle Vernon` and `Aunt Petunia` appear constantly. Rendering them `Vernon మామయ్య` and
`Petunia అత్త` keeps the name anchor intact while teaching two extremely high-frequency Telugu
words you will use in real life. Recommended, but confirm it in chapter 1 before it propagates
through the whole book.

### Vocatives take no ending

`"Harry!"` stays `"Harry!"`. Telugu's vocative particles are free words and are superb
characterisation — ఒరేయ్ (rough, to a male), ఏరా, బాబూ (affectionate, to a boy), అమ్మా. Vernon
barking ఒరేయ్ at Harry and Hagrid saying బాబూ does more work than any adjective.

### Agreement has to come from somewhere

A Latin-script anchor carries no Telugu gender, so the verb cannot agree with it automatically.
Gender is in [glossary.tsv](glossary.tsv); respect level is in [address.tsv](address.tsv). This
is the most likely place for a silent error, which is exactly why both are columns in a file and
not something to remember.

---

## 5. Prose

- **Verb goes last.** Every clause. If a draft has a verb in the middle, it is English wearing
  Telugu words.
- **Break the participial pile-ups.** English stacks participles where Telugu wants a chain of
  conjunctive participles in -ి or -తూ, then one finite verb. This is the single biggest
  structural difference and the main reason the paragraph, not the sentence, is the unit.
- **Relative clauses move in front.** English postposes them; Telugu makes a prenominal
  participle in -ిన / -ే.
- **Reported speech uses అని.** Dialogue tags become `"…" అని <verb>`. This is not optional in
  Telugu the way it is in English.
- **Narration is past tense**, dialogue whatever the moment needs.
- **Sentence counts need not match.** Split and merge freely inside a segment. Do not add or
  remove *content* — that is what the back-translation check is for.

## 6. Dialogue

- Keep the source's double quotes.
- English has a huge inventory of speech tags — chortled, snapped, piped, spat. Telugu is much
  poorer here and inventing verbs reads badly. Use అని + an ordinary verb + a manner adverb
  instead. Losing some of that variety is an acceptable cost; fake verbs are not.

## 7. Numbers and punctuation

- Small numbers as Telugu words; digits for addresses and large figures.
- Telugu digits (౧౨౩) are not used in modern prose. Don't.
- Keep the source's paragraph breaks — the segment store depends on them.

---

## 8. When you are stuck

In order:

1. Is it a term? → glossary.tsv, and if it is not there, add it.
2. Is it an address or agreement question? → address.tsv.
3. Has it come up before? → DECISIONS.md.
4. Still stuck → translate it the plain way, mark the segment `status=query`, and put the
   question in `review/questions.md` for a native speaker. Do not stall the chapter on one
   sentence.
