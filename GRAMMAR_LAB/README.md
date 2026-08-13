# Telugu Verb Lab

A standalone static site for conjugation practice, in the same visual language as
`../LEARNING_GUIDE/`. No build step, no dependencies, no server — open `index.html`.

Built for the desk hour: the part of Telugu that Anki cards cannot carry, which is putting
the right ending on the right stem fast enough to say it.

| File | What it is |
|---|---|
| `index.html` | Verb picker, session scope, and the rationale for the study method |
| `paradigms.html` | Every form of every verb, morphology colour-coded. Reference, not practice |
| `study.html` | The drill runner |
| `review.html` | Verification queue and printable stem sheet for a native speaker |
| `data/verbs.js` | The 35 verbs as a **stem inventory** — the only file worth editing |
| `data/engine.js` | Person endings and the rules that turn stems into forms |
| `assets/app.js` | Selection, spacing schedule, shared rendering |

35 root verbs × 14 paradigms = **1,709 generated forms**. 30 drillable cells per verb in the
core scope, 49 with everything switched on.

## Source of the verbs

`English-Telugu-+RootVerbs.pdf` (bhashafy.com), 35 roots over two pages. That PDF is third-party material and is deliberately **not** committed to this repo — it is gitignored. Nothing here depends on it: the 35 roots live in `data/verbs.js` — five more than
the "30 common verbs" you mentioned.

The Telugu was read off the **rendered pages**, not the PDF text layer. That text layer is
corrupted by a font-encoding problem and silently produces wrong words: `ఇవుు` for ఇవ్వు,
`కొట్ట ు` for కొట్టు, `వా ా యి` for వ్రాయి, `పర్చగెత్త ు` for పరుగెత్తు. If you ever re-extract from
this PDF, do not trust copy-paste.

## Stems, not forms

The important design decision, and the reason this is maintainable.

Telugu person endings are completely regular — `-ānu -āvu -āḍu -undi -āṁ -āru` after the
tense marker, `-nu -vu -ḍu -du -ṁ -ru` on the negative. What varies from verb to verb is a
small set of stems. So `verbs.js` stores about ten fields per verb and `engine.js` generates
the paradigm:

```js
{ id:'cheyi', root:['chēyi','చేయి'],
  np:['chēs','చేస్'], T:['t','త'], pst:['chēs','చేస'],
  neg:['chēya','చేయ'], a:['chēya','చేయ'], inf:['chēyā','చేయా'],
  hort:['chēddāṁ','చేద్దాం'] }
```

Two consequences that matter:

1. **A correction is one edit.** If a native speaker says the past stem is wrong, you change
   one string and all six past cells, plus anything else built on it, regenerate correctly.
2. **Review is tractable.** Nobody has to proofread 1,709 forms. Six probe questions settle a
   verb; `review.html` lays them out and exports them as plain text.

Both scripts concatenate cleanly because stems are stored pre-composed for whatever follows:
a stem taking a consonant-initial ending carries a virama (`చేస్` + `తాను`), one taking a
vowel-initial ending does not (`చేస` + `ాను`), and Telugu vowel signs are combining characters.

Genuine irregularities are per-verb `ov` overrides — `rā` → `raṇḍi` not *`rāvaṇḍi`, `uṇḍu` →
`lēdu` not *`uṇḍalēdu`.

## How the drill works, and why

You asked what the research says rather than guessing, so the design follows it:

- **Retrieval, not completion.** Filling in a visible conjugation table is close to worthless;
  pulling the form out of memory is what sticks. There is no fill-in-the-grid exercise here.
  Every item hides the answer until you commit.
- **Production, not recognition.** Practice at producing improves producing; practice at
  recognising mostly improves recognising. Since the goal is speech, there is no multiple
  choice. You say the whole form aloud, then self-grade. Typing is optional and off by default.
- **Interleaved, not blocked.** Walking one verb's paradigm top to bottom feels productive and
  tests badly a week later. The session never serves two items from the same verb
  consecutively — including when a missed item is re-queued, except where nothing else is left at the tail of the queue.
- **Spaced, with immediate feedback.** Three grades feed a Leitner schedule in `localStorage`
  (gaps of 1, 3, 7, 16, 35 days). Missed items also come back later in the same session.

The one thing tables are good for is *noticing* — you cannot retrieve a pattern you have never
seen. The optional notice step shows each paradigm once with the stem in amber and the ending
in orange. Twenty seconds, then drill. Turn it off once a verb is familiar.

**Person-invariant forms are drilled across all six persons on purpose.** The negative past,
the obligation and the conditional never change shape in Telugu — the pronoun carries person.
Seeing `rālēdu` come back under six different subjects is the lesson, because trying to
inflect these is the standard learner error. In the reference tables they print once and then
read "↑ unchanged".

## Using it

1. `index.html` → pick verbs. Five is a good session. Presets: the essential five, random
   five, the irregulars, the `-ko` reflexives, or **weakest first**, which ranks by your own
   history.
2. Pick a scope. Start at *the core six* paradigms and widen only when the endings arrive
   without hesitation.
3. Start. `space` or tap reveals; `1` `2` `3` grade as missed / shaky / got it.

Progress, selection and verification marks live in this browser's `localStorage`. There is a
reset link in the footer of the home page.

## What has not been checked

**No native speaker has seen any of this yet.** The paradigms are generated from a stem
inventory I wrote.

A number of individual cells do cross-check against Telugu already in your course — `undi`,
`unnānu`, `raṇḍi`, `tinalēdu`, `ivvaṇḍi`, `āgaṇḍi` all fall out of the engine and all match
what the lesson pages already teach. That is reassuring about the machinery, not proof about
every cell.

Known soft spots, in priority order:

- **Four verbs flagged `check`** — run, throw, drive, fly. Each has a note explaining why.
  `parugettutānu` in particular is clumsy where speakers say `parigeḍatānu`.
- **The conditional** is the least settled paradigm throughout. It sits in tier 3 and is
  excluded from the two narrower scopes.
- **Register.** Everything assumes educated colloquial Hyderabad/Telangana speech, which is
  what the course targets. A coastal speaker or textbook gives `chebutānu` where this prints
  `cheptānu`, and `-āmu` where this prints `-āṁ`. Neither is wrong; follow what you hear at home.
- **Six verbs have no hortative** — come, run, love, throw, drive, fly. Those cells show
  "not natural for this verb" rather than an invented form.

Work `review.html` with a native speaker, correct the stems in `data/verbs.js`, and the
paradigms regenerate. Tick a verb as verified and the tick shows up on the paradigm page.

## Extending it

Adding a verb is one object in `data/verbs.js`; nothing else needs to change. Adding a
paradigm is one entry in `FORMS` plus a case in `conjugate()` in `data/engine.js`.

The obvious next additions once these 35 are solid: the perfect (`chēsi unnānu`), the
completive `-ēyi` that Hyderabad speech uses constantly (`visirēstānu`), and past continuous.
All three were left out deliberately rather than guessed at.
