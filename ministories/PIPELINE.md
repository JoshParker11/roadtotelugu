# The pipeline — from raw story to reading it on the phone

**This is the operating manual for finishing the Mini Stories reader.** Paste-it-into-a-fresh-
session grade: a cold assistant (or the user, months from now) should be able to open this and
run the machine without re-deriving anything. It assumes the reader at `../reader/` is built and
live (it is — see `DECISIONS.md` #12); what remains is *volume* (55 stories) and *depth* (a
definition for every word). Read `BRIEF.md` first for the ethos and the mistakes a cold start
makes; this file is deliberately just the crank to turn.

**The goal state, concretely:** all 60 stories readable at
<https://joshparker11.github.io/roadtotelugu/reader/> on the phone, every sentence with audio,
and **every word clickable to a real definition card** — baked, offline, no key needed — with
the AI tab remaining the ad-hoc fallback for anything the baked card doesn't answer.

---

## 0. The standing translation guardrails

```bash
python3 tools/ms_batch.py --remaining     # what is left, and a suggested batch size
python3 tools/ms_batch.py 6               # -> ministories/batch_6.txt, ready to paste
```

`ms_batch.py` writes the guardrails and the untranslated rows into one file, and prints the row
count the reply must match. Use `work/*.tsv` as the source, never `source/api/*.json` — the raw
LingQ payloads are unsegmented and carry no guid, and the guid is what lets a reply be applied
without trusting that row order survived a copy-paste.

Paste [TRANSLATION_PROMPT.md](TRANSLATION_PROMPT.md) §1 in front of every translation batch,
whichever model does the work. It carries the register, the dative-experiencer rule, the
structural rules the drill depends on, the fixed renderings settled so far, and the exact output
format `ms_apply.py` expects back.

## 1. The per-story loop (repeat ×55)

Each story is one pass through five tools, all idempotent, all guid-keyed. Nothing here is new;
every command is documented in `README.md` and behaves as documented.

```bash
# 1. Translate (the only step that needs judgment — see BRIEF.md §9 and ../translate/STYLE.md)
python3 tools/ms_apply.py --pending N          # read story N's English
#    ... translate; write patch.tsv: guid, te, notes, status ...
python3 tools/ms_apply.py patch.tsv            # apply — refuses to clobber existing work

# 2. Check — non-zero exit means stop and fix, not continue
python3 tools/check_ms.py --num N --warn

# 3. Voice it (needs AZURE_SPEECH_KEY / AZURE_SPEECH_REGION in the environment)
python3 tools/ms_audio.py --num N              # ~50 segments, skips anything already on disk

# 4. Continuous per-story audio + subtitle tracks (this is what the reader seeks within)
python3 tools/ms_lr_export.py --num N

# 5. Bake the reader (rebuilds all stories; any story with complete te + audio appears)
python3 tools/build_ms_reader.py

# 6. New words got word-audio manifest rows in step 5 — voice the new ones (cheap, skips existing)
python3 tools/ms_audio.py --words              # needs an Azure key; if you have none, instead:
python3 tools/ms_hypertts_export.py --words    #   -> Anki -> HyperTTS batch -> export
python3 tools/ms_hypertts_import.py <export.txt> --words
```

Then look at it locally (`python3 tools/serve.py` → <http://localhost:8123/reader/>), listen to
at least the first minute of the story audio (a real bug was once caught only by listening —
`DECISIONS.md` #9), and ship (§4 below).

Batching is fine: translate five stories, then run steps 2–6 once each with no `--num`. The
translation itself is the bottleneck and should stay one story at a time with a `check_ms.py`
run between — the checker's story-vs-retell comparison is the only thing standing in for a
native speaker right now.

**Do not hand-edit** `reader/data/ministories.js` or `ministories/word_audio.tsv`; both are
generated. The editable surface is `work/*.tsv`, full stop.

## 2. The word registry — every word gets a real definition card

This is the one genuinely new build remaining. Today the baked card covers ~62% of tokens
(master gloss, Verb Lab form equivalent, or stem+suffix split); the other 38% show "not in the
word master" plus dictionary links and the pay-per-click AI tab. The goal is a **baked
definition for 100% of words** — the Language Reactor-style card (senses by part of speech +
a short contextual explanation) but precomputed, offline, and free at click time.

**The shape: `ministories/vocab.tsv`** — the term glossary `DECISIONS.md` #7 says is missing,
now with the reader as its consumer. One row per (word guid, sense):

```
guid    te    sense_no    gloss    pos    explain    context_guid    status
```

- `guid` — `ids.guid('W', script)`, same as everywhere.
- `gloss` — the short equivalent ("having made (for oneself)"), what lists and review show.
- `explain` — 2–4 sentences, the card body: dictionary form if inflected, what the suffixes
  contribute, register notes. Modeled on the LR "Explain" card, in this project's grammatical
  vocabulary (the system frame in `reader/assets/aidict.js` is the template to reuse).
- `context_guid` — the segment the sense was drawn from, so the card can quote its sentence.
- `status` — same ladder as everything (`draft` → `checked`), because nothing checks an
  explanation's correctness yet and pretending otherwise is the failure mode BRIEF §8 warns about.

**The accumulation rule (decided by the user, worth stating verbatim):** when translation of a
later story uses an already-registered word in a **new sense or construction**, *append a new
`sense_no` row* — never overwrite the existing one. First occurrence wins row 1; the registry
only ever grows. A word's card shows all its senses, first-met first.

**Built, and filled from chat rather than the Batch API — see `DECISIONS.md` #14.**
`tools/ms_vocab.py` exists and takes the same patch-file shape as `ms_apply.py`, so definitions
can come from an interactive session now or a batch job later without a second code path:

```bash
python3 tools/ms_vocab.py --pending --limit 40   # words with no card, + the checked facts + context
python3 tools/ms_vocab.py patch.tsv              # apply
python3 tools/ms_vocab.py --stats                # coverage
```

Stories 1–5 are done: all 151 previously-unresolved words have a card, all `status=draft`.
`build_ms_reader.py` merges the registry and the reader renders it at the top of the Dictionary
tab. The original Batch API plan below still stands for scaling to 60 stories.
The reasoning: this site is static and keyless by design; per-click live calls are the opt-in
exception, not the default. The tool should:

1. Read `word_audio.tsv` (the distinct-word manifest the baker already writes) minus guids
   already in `vocab.tsv` — so re-runs only pay for new words, same rule as `ms_audio.py`.
2. For each word, build one request: word + its first-occurrence sentence (from the baked data)
   + the English of that sentence + the master/Verb Lab info where it exists (give the model the
   checked facts; ask it only for what's missing).
3. Submit as **one batch** (50% price, results keyed by `custom_id` = guid), poll, write rows
   with `status=draft`.
4. `build_ms_reader.py` then merges `vocab.tsv` into each lex entry (new fields: `senses`,
   `explain`), and the reader's Dictionary tab renders them above the web-dictionary links.
   The AI tab stays for ad-hoc follow-ups.

**Cost, so nobody has to guess** (rough tokens: ~700 in / ~250 out per word; distinct words grow
sublinearly — 267 across stories 1–5, so estimate ~2,000–2,500 across all 60):

| model | list price | ~2,500 words, batched (50%) |
|---|---|---|
| Haiku 4.5 | $1 / $5 per MTok | **≈ $2.50** |
| Opus-class | $5 / $25 per MTok | **≈ $12** |

So yes — the "lower-end model" instinct is right that this is cheap either way. The counter-
argument is BRIEF §8's own: nothing checks these explanations, a wrong one delivered confidently
is the worst failure mode in the project, and the entire corpus costs about one lunch even at
the top tier. **Recommendation: strongest available model, batched, once** — economize on
things that have checkers. Either way: generate stories 1–5's words first, read every card
before scaling to 60 (the same workshop-before-scale rule BRIEF §8 sets for the prompts).

## 3. What "polished" means — the checklist

- [ ] 55 stories translated, `check_ms.py` clean, voiced, lr-exported, baked (§1)
- [ ] `tools/ms_vocab.py` written; `vocab.tsv` covering every distinct word; cards render (§2)
- [ ] `ms_audio.py --words` run after the last bake, so every headword has a pronunciation clip
- [ ] AI prompt wording workshopped against stories 1–5 (BRIEF §8 — still open; the prompts in
      `reader/assets/aidict.js` are a first cut)
- [ ] The one open translation query — the retell-intro line, all 60 lessons — settled by a
      native speaker's ear (`DECISIONS.md` #11), then re-voice that one guid with `--force`
- [ ] Eventually: a native-speaker pass over `vocab.tsv` rows, flipping `draft` → `checked`

## 4. Shipping — how this reaches the phone

GitHub Pages serves the `main` branch root at
**<https://joshparker11.github.io/roadtotelugu/>**; the reader is `/reader/` under that. Deploy
is just: commit on `ministories`, merge to `main`, push. No build step — Pages serves the files
as committed, which is why the baked artifacts are committed:

- **Committed**: `work/*.tsv`, `reader/` (including `data/ministories.js`), `word_audio.tsv`,
  future `vocab.tsv`, and `ministories/lr/*.mp3` + `.srt` (un-ignored deliberately: our own
  TTS of our own translation, ~2 MB/story ≈ 120 MB at 60 stories — fine for a repo, and the
  phone can't play audio that isn't hosted).
- **Still gitignored**: `ministories/audio/` (per-segment + word clips — regenerable, and
  `lr/*.mp3` is the artifact the reader actually streams), `source/` (LingQ's English).
  ⚠️ If word-pronunciation clips should work on the phone too, `audio/words/` needs the same
  un-ignoring treatment as `lr/` — decide when the clips are first generated.

On the iPhone: open the reader URL in Safari → Share → **Add to Home Screen**. Word marks live
in that browser's localStorage; the vocabulary queue's backup drawer (on the words page) is the
bridge if marks ever need to move between phone and laptop.

## 5. Standing rules (the ones that already bit someone once)

- `seq` is per-file, never per-story — classify meta rows by content (`RETELL.match`).
- Any new checker or state logic gets fault-injection-tested on deliberately broken input
  before being trusted. Zero findings on clean data proves nothing.
- Guids are the identity everywhere; anything keyed otherwise will silently fork.
- Re-running generators must never clobber hand-entered work or re-spend money; skip-if-exists
  is the contract every tool here honors.
- The editable files are `work/*.tsv` and (soon) `vocab.tsv`. Everything under `reader/data/`
  and `lr/` is output.
