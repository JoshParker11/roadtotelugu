# Telugu Romanizer — Chrome extension

Shows romanization for Telugu script in the three places it is read: under the player's captions
on YouTube, in place of the script in a transcript side panel, and under each line on
[languagereactor.com](https://www.languagereactor.com/) itself. LR does the dictionary and export
work and has no romanization for Telugu.

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

## The Language Reactor site, and the Mac “app”

**The app is not an app.** `~/Applications/Chrome Apps.localized/Language Reactor.app` is a
Chrome shortcut — its `Info.plist` carries `CrAppModeShortcutURL =
https://www.languagereactor.com/phrasepump` and `CrBundleIdentifier = com.google.Chrome`, and the
executable is Chrome's `app_mode_loader`. The window is a Chrome tab in a frame with no address
bar, on the same profile, running the same extensions. So nothing here has to integrate with a
desktop application: **matching the site in the manifest is the whole of it**, and the extension
then works identically in the app window and in a normal tab.

Reaching the settings from the app window: the puzzle-piece **Extensions** button in its title
bar → Telugu Romanizer. `chrome://extensions` itself only opens in a real Chrome window.

On the site there is no video, so the caption/panel split does not apply and a third pass runs
instead. It treats the two shapes of Telugu differently:

| what | treatment | why |
|---|---|---|
| a text row, Telugu only | romanization on its own line underneath | it is a line, like a caption |
| Telugu quoted inside English prose | romanization inline, right after the word | a block under the paragraph lands nowhere near the word |

Neither one **replaces** the script, which is the difference from the YouTube panel, and it is
deliberate: LR hangs click-to-define, the known/unknown colouring and the save-word button off
the element holding the script. Swap that text out and the dictionary goes with it — which is the
entire reason to be on the site. *Settings → The Language Reactor site* has an **Instead of the
script** mode if you ever want the old behaviour, and it is not the default.

Two details that were bugs before they were tested, worth not reintroducing:

- The Telugu-or-prose test is decided **once per element** and stored in `data-tr-shape`. The
  moment romanization is added, every element contains Latin letters, so re-testing reclassifies
  every row as prose on the next sweep.
- `romanize()` passes Latin through untouched, so romanizing a *mixed* text node and appending
  the result prints the entire English sentence a second time. Mixed nodes are split on their
  Telugu runs; only the runs are annotated.

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

## On the phone

Neither phone can run this as an extension: Chrome for Android has never supported extensions and
Chrome for iOS has no extension API. `mobile/` is the way round that — a **bookmarklet**, a
bookmark whose address is a line of JavaScript, which loads `mobile/loader.js` into whatever page
you are looking at.

Setup instructions, and the two lines to copy, are the page itself:
**<https://joshparker11.github.io/roadtotelugu/chrome-extension/mobile/>** — open it *on the
phone*, because the awkward step is getting the text into a bookmark's address field.

`loader.js` loads `src/te2rom.js`, `src/colloquial.js` and `src/content.js` **from the Pages
deploy**, rather than bundling them. A bundle would be a fourth copy of the romanizer, and
`check_te2rom.py` exists because three was already one too many. Fix `content.js`, push, and the
phone has the fix on the next tap.

What it replaces, and how:

| Chrome gives the extension | the bookmarklet's substitute |
|---|---|
| `chrome.storage.sync` | `localStorage` on languagereactor.com's origin, per device |
| the popup's switches | which of the two bookmarks you tap |
| on/off | tapping the same bookmark again — it flips `enabled`, and `content.js` already reverts on a storage change |
| `content_scripts.matches` | `window.__trReader`, set by the loader before `content.js` runs |

That last one is why `content.js` checks `__trReader` as well as the hostname. A page cannot use
it to hijack the extension: a content script has its own isolated `window`, so the desktop path
only ever reads the hostname. Injected by the bookmarklet, `content.js` runs in page context
instead, where the flag is visible — and reader mode is the right default there anyway, since
tapping the bookmark *is* "annotate what I am reading".

It works because **languagereactor.com sends no CSP** — no header, no meta tag — so a script
element pointing at github.io is not blocked. If that ever changes, the page is simply
un-annotated: the text lives in the LR account and is never modified, so there is nothing to
lose.

Tested against a mock of the My Texts reader served over HTTP, loading the real `src/` files:
first tap annotates; second tap on the same bookmark reverts the page to its original text;
third restores it; the other bookmark switches scheme in place; and content rendered later —
Language Reactor is a single-page app and never reloads — is annotated with no further tap.
**Not yet tested on a real phone against the real site.**

**Android:** bookmarklets are unreliable there (Firefox blocks `javascript:` from the address
bar, Chrome needs a workaround). The tablet wants a real Firefox add-on, which is a separate job.

## Installing it for yourself

No store account needed, and nothing is published.

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. **Load unpacked** → choose this `chrome-extension` folder
4. Open a YouTube video with Telugu captions, or a text on languagereactor.com

The site match is new, so an **existing install has to be reloaded** before it appears there —
the reload arrow on the extension card, then reopen the Language Reactor window.

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

The **site** pass was tested against a mock of the reader's structure — rows of per-word spans, a
translation column, a sidebar with prose — where lines, prose, re-render, scheme switching and
the off switch all behaved, and turning it off restored the page byte for byte. A mock is not the
real markup. The one thing to watch on the real page is whether the extra line under a row fits:
if rows overlap or clip, LR is positioning them itself, and the answer is the same as the panel's
— *Panel text size*, or **Instead of the script**.

## Publishing

Not required for personal use — loading unpacked works indefinitely. If you ever want it in
the Chrome Web Store it needs a one-time developer registration fee, a privacy policy, and a
review pass. Given it reads page text on youtube.com, expect questions about the host
permission. There is no reason to bother unless someone else wants it.
