# Telugu Romanizer — Chrome extension

Shows romanization for Telugu script on YouTube: a line under the player's captions, and in
place of the script in a transcript side panel. Built to sit alongside
[Language Reactor](https://www.languagereactor.com/), which does the dictionary and export work
but has no romanization for Telugu.

## Why it lives in this repo

The romanizer exists three times now — `tools/te2rom.py` for the pipeline,
`STUDY/assets/te2rom.js` for the site, and `chrome-extension/src/te2rom.js` here. Three copies
of one rule is exactly the drift this project has been careful about, so
`python3 tools/check_te2rom.py` diffs the Python against the JS across every Telugu token in
the masters **and** verifies this copy is byte-identical to the site's. Re-copy after any
change:

```bash
cp STUDY/assets/te2rom.js chrome-extension/src/te2rom.js && python3 tools/check_te2rom.py
```

Split it out later with `git subtree split --prefix=chrome-extension` if it ever needs its own
repo. Until then, one checker covers all three.

## Two schemes

| | script | project | colloquial |
|---|---|---|---|
| | కూడా | `kūḍā` | `kooda` |
| | తిను | `tinu` | `thinu` |
| | ఇంట్లో | `iṇṭlō` | `intlo` |
| | వెళ్ళు | `veḷḷu` | `vellu` |

**Project scheme** marks vowel length and retroflexion, so it maps back to exactly one
spelling. It is what the deck and the site use.

**Colloquial** is what Telugu speakers actually type: long vowels doubled, the dental series
taking the `h` and retroflex staying plain. It is **lossy on purpose** — `ē` and `e` both
become `e`, `ఠ` and `త` both `th` — so it reads naturally but cannot be looked up or
round-tripped. Word-final long `ā` is written single (`kooda`, not `koodaa`), which the family
transcripts settle: 28 occurrences of `kooda` and none of `koodaa`.

## Installing it for yourself

No store account needed, and nothing is published.

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. **Load unpacked** → choose this `chrome-extension` folder
4. Open a YouTube video with Telugu captions

After editing any file, press the **reload** arrow on the extension card, then reload the
YouTube tab.

## Settings

The toolbar popup has the four switches worth flipping mid-video: on/off, scheme, captions,
panel. **More settings** opens the options page, which adds a live sample of both schemes and
the panel selector.

## The panel selector, and why it is a setting

Language Reactor is a separate extension whose markup can change in any release, so nothing
here hard-codes its class names — a hard-coded selector fails silently the day they rename
something. Instead the panel path finds *any* text node containing Telugu outside the video
player and annotates it.

That is deliberately broad. If it annotates something it should not:

1. Right-click the Language Reactor panel → **Inspect**
2. Walk up the element tree to the container that holds the transcript
3. Copy a CSS selector for it (right-click the node → Copy → Copy selector)
4. Paste it into **Panel selector** in the options page

## The one thing that does not work: panel rows still clip

Long transcript rows in the Language Reactor panel are cut off. **Four attempts failed**, and
they are recorded here so the fifth does not repeat them:

1. relax `max-height` on ancestors — some rows use a fixed `height` instead
2. relax fixed `height` too — over-reached, hit the panel's scroll container, and the whole
   transcript went blank
3. measure instead of guess: find the ancestor whose `scrollHeight` exceeds its `clientHeight`,
   relax only that one, stop at any scroller — still clipped
4. never grow an absolutely positioned row, since a virtualised list computes each row's top
   and growing one overlaps its neighbour; shrink the text instead — still clipped

The premise behind all four was wrong. Romanization is **1:1 with the script character for
character** (median over 295 measured lines), not "half again longer". What differs is rendered
width — Telugu glyph clusters are wide, Latin letters narrow — and that ratio cannot be computed
from outside the page.

**The working answer is the manual one:** the popup's *Panel text size* slider, 60–100%. It does
not fight the layout, so it cannot fail. Try 85%.

**What would settle it properly:** right-click a clipped row → Inspect → Computed tab, and read
off `height`, `max-height`, `overflow-y`, `display`, `position` and `-webkit-line-clamp` for the
row and its two or three ancestors. Everything above was inferred from screenshots.

## What is unverified

The caption selector (`.ytp-caption-segment`) is YouTube's own and stable. The panel behaviour
has not been tested against a live Language Reactor install — that needs the extension
running, which is your machine, not mine. Expect the first session to need the selector above.

## Publishing

Not required for personal use — loading unpacked works indefinitely. If you ever want it in
the Chrome Web Store it needs a one-time developer registration fee, a privacy policy, and a
review pass. Given it reads page text on youtube.com, expect questions about the host
permission. There is no reason to bother unless someone else wants it.
