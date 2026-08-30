/* Annotate Telugu script with romanization, on YouTube and on languagereactor.com.
 *
 * THE MAC "LANGUAGE REACTOR APP" IS NOT AN APP. It is a Chrome shortcut — its Info.plist says
 * CrAppModeShortcutURL = https://www.languagereactor.com/phrasepump — so the window is a Chrome
 * tab in a frame with no address bar, running the same profile and the same extensions. Nothing
 * here needs to know it exists: matching the site in the manifest is what makes it work there.
 *
 * NOTHING HERE KNOWS LANGUAGE REACTOR'S CLASS NAMES, ON PURPOSE.
 * LR is a separate extension that can restructure its markup in any release, and a hard-coded
 * selector fails silently the day it does. It also *replaces* YouTube's caption rendering with
 * its own element, which is why targeting `.ytp-caption-segment` found nothing once LR was
 * running. So the script works on the only thing that is stable: text nodes containing Telugu.
 *
 * Where a node sits decides what happens to it:
 *   inside the player   -> a caption. Romanization is added underneath by default, because LR
 *                          hangs its click-a-word overlay off that text and replacing it would
 *                          break the tool this exists to complement.
 *   everywhere else     -> the transcript panel. Romanization replaces the script, since that
 *                          is a wall of text to read rather than a line to glance at.
 *
 * Captions are re-rendered on every cue, so they are matched on their text rather than a
 * "done" flag. Panel nodes are tracked in a WeakSet so the observer does not re-annotate the
 * annotations it just made — the usual way this kind of script ends up looping forever.
 */
(() => {
  const TELUGU = /[ఀ-౿]/;
  const MARK = 'data-tr-src';
  const PLAYER = '#movie_player, .html5-video-player, .ytp-caption-window-container';
  const SHAPE = 'data-tr-shape';

  /* The standalone site, where there is no video and so no caption/panel split: every Telugu
     string on the page is reading material. It gets its own pass rather than falling through to
     the panel one, because the panel pass *replaces* the script — see doReader.

     __trReader is the mobile bookmarklet's way in (mobile/loader.js). It cannot be set from a
     page against the extension's wishes: a content script has its own isolated `window`, so the
     desktop path only ever reads the hostname. Injected by the bookmarklet this file runs in
     page context instead, where the flag is visible — and reader is the right default there
     anyway, since tapping the bookmark is a deliberate "annotate what I am reading". */
  const LR = window.__trReader === true || /(^|\.)languagereactor\.com$/.test(location.hostname);

  const DEFAULTS = {
    enabled: true,
    scheme: 'iso',              // 'iso' | 'colloquial'
    captions: true,
    captionMode: 'under',       // 'under' | 'replace'
    panel: true,
    panelSelector: '',
    hideScriptInPanel: true,
    relaxClipping: true,
    panelScale: 100,   // manual size for panel romanization, 60–100
    reader: true,               // languagereactor.com itself
    readerMode: 'under',        // 'under' | 'replace'
  };

  let opts = { ...DEFAULTS };
  /* Reassigned, not just added to: revert() has to forget every node it ever annotated, or
     switching scheme leaves the inline annotations off for good — the spans are removed but the
     text nodes are still marked done. */
  let seen = new WeakSet();

  const romanize = t => opts.scheme === 'colloquial'
    ? Colloquial.romanize(t) : Te2Rom.romanize(t);

  const teluguNodes = (root, wantPlayer) => {
    const out = [];
    if (!root) return out;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (!n.nodeValue || !TELUGU.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
        const p = n.parentElement;
        if (!p) return NodeFilter.FILTER_REJECT;
        if (p.closest('.tr-rom, .tr-rom-inline, .tr-rom-after, script, style, textarea, input, [contenteditable]')) {
          return NodeFilter.FILTER_REJECT;
        }
        // null means the caller does not care which side of the player a node is on.
        if (wantPlayer !== null && !!p.closest(PLAYER) !== wantPlayer) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    for (let n = walker.nextNode(); n; n = walker.nextNode()) out.push(n);
    return out;
  };

  /* The nearest ancestor that lays out as a block — which is the caption *line*.
     Language Reactor splits a caption into one inline span per word so it can make each one
     clickable. Annotating per text node therefore produced one romanization per word, each in
     a block element, which stacked the whole caption vertically down the screen. Grouping by
     the line container is what keeps a line a line. */
  function lineBox(node) {
    let el = node.parentElement;
    while (el && el !== document.body) {
      const d = getComputedStyle(el).display;
      if (d !== 'inline' && d !== 'contents') return el;
      el = el.parentElement;
    }
    return node.parentElement;
  }

  /* ---------- captions ---------- */
  function doCaptions() {
    if (!opts.captions) return;
    const player = document.querySelector('#movie_player') || document.body;

    // Group the words of a caption back into the line they belong to, in document order.
    const groups = new Map();
    teluguNodes(player, true).forEach(node => {
      const box = lineBox(node);
      if (!box) return;
      if (!groups.has(box)) groups.set(box, []);
      groups.get(box).push(node);
    });

    groups.forEach((nodes, box) => {
      /* Join on a space, not on nothing. The gaps between Language Reactor's per-word spans
         are whitespace-only text nodes, which contain no Telugu and so never reach here —
         concatenating what is left ran the whole caption together as one word. */
      const text = nodes.map(n => n.nodeValue.trim()).filter(Boolean).join(' ');
      if (!text) return;
      if (box.getAttribute(MARK) === text) return;      // same cue, nothing to redo
      box.setAttribute(MARK, text);

      if (opts.captionMode === 'replace') {
        // Rewrite each word in place. The spans stay, so LR's per-word structure survives.
        nodes.forEach(n => { n.nodeValue = romanize(n.nodeValue); });
        return;
      }

      let line = box.querySelector(':scope > .tr-rom');
      if (!line) {
        line = document.createElement('div');
        line.className = 'tr-rom';
        box.appendChild(line);
      }
      line.textContent = romanize(text);
    });
  }

  /* ---------- panel ---------- */
  function panelRoot() {
    if (opts.panelSelector) {
      try { return document.querySelector(opts.panelSelector); } catch { return null; }
    }
    return document.body;
  }

  function doPanel(root) {
    if (!opts.panel) return;
    const scope = root && root.isConnected ? root : panelRoot();
    teluguNodes(scope, false).forEach(node => {
      if (seen.has(node)) return;
      const original = node.nodeValue;
      const rom = romanize(original);
      if (rom === original) { seen.add(node); return; }

      const span = document.createElement('span');
      span.className = 'tr-rom-inline';
      span.textContent = rom;
      /* A manual size, because automatic fitting has not been reliable here. Four attempts to
         detect what clips these rows all failed, and the measurement that would settle it can
         only be taken inside the real page. A control the reader sets once always works. */
      if (opts.panelScale && opts.panelScale !== 100) span.style.fontSize = opts.panelScale + '%';

      // The script stays in the DOM but hidden: one setting turns it back on, and any handler
      // the host attached to the parent still finds its text where it left it.
      const keep = document.createElement('span');
      keep.className = 'tr-script';
      keep.textContent = original;
      if (opts.hideScriptInPanel) keep.style.display = 'none';

      const frag = document.createDocumentFragment();
      frag.append(keep, span);
      node.replaceWith(frag);
      seen.add(keep.firstChild);
      seen.add(span.firstChild);

      if (opts.relaxClipping) unclip(span);
    });
  }

  /* Romanization runs about half again longer than the script it replaces, so rows sized for
     Telugu cut it off.
     
     TWO EARLIER ATTEMPTS GUESSED AT WHICH PROPERTY WAS DOING THE CLIPPING — max-height, then
     a fixed height — and each time some rows still clipped because it was the other one, or
     something else again. Language Reactor's markup is not mine to read, so this measures
     instead: an element that clips has scrollHeight greater than clientHeight. Find the one
     that actually does, relax it, and check whether that worked.

     And if it did not work, stop fighting the layout. A virtualised list positions every row
     at a computed offset, so making a row taller makes it overlap its neighbour rather than
     fit; there is no way to win that from outside. In that case the romanization is shrunk
     just enough to fit the space that exists, which no layout can refuse. */
  function unclip(el) {
    const box = clippingBox(el);
    if (!box) return;

    /* A row the layout positions by hand cannot be made taller: its neighbour's offset was
       computed for the old height, so growing it overlaps rather than fits. The harness caught
       exactly that — rows went from 46px to 70px while their tops stayed 46px apart. Skip
       straight to shrinking for those. */
    if (!positioned(box)) {
      relax(box);
      if (!overflows(box)) return;               // expanding was enough
    }

    /* Still clipped. Shrink the romanization — never the script or anything else — a step at
       a time, and stop the moment it fits. The floor is 78%, below which it stops being
       easier to read than the script was. */
    const floor = Math.min(78, opts.panelScale || 100);
    for (let scale = 95; scale >= floor; scale -= 4) {
      el.style.fontSize = scale + '%';
      if (!overflows(box)) return;
    }
  }

  const overflows = n => n.scrollHeight > n.clientHeight + 1;

  /* Absolutely positioned, or sitting among siblings that are — the signature of a virtualised
     list, where every row's top is computed and heights are assumed fixed. */
  function positioned(n) {
    if (/absolute|fixed/.test(getComputedStyle(n).position)) return true;
    const sib = n.parentElement && n.parentElement.children;
    if (!sib) return false;
    for (const c of sib) {
      if (c !== n && /absolute|fixed/.test(getComputedStyle(c).position)) return true;
    }
    return false;
  }

  /* The nearest ancestor that is actually clipping. Stops at a scroll container: that is the
     panel's own list, it is *supposed* to overflow, and relaxing it is what made the whole
     transcript disappear once already. */
  function clippingBox(el) {
    for (let n = el.parentElement, depth = 0; n && depth < 5; n = n.parentElement, depth++) {
      const cs = getComputedStyle(n);
      if (cs.overflowY === 'auto' || cs.overflowY === 'scroll') return null;
      if (n.getBoundingClientRect().height > 300) return null;   // a container, not a row
      if (overflows(n)) return n;
    }
    return null;
  }

  /* Relax every mechanism that can clip, on one element, rather than trying to work out which
     one is in play. Cheap, and it cannot reach past the row. */
  function relax(n) {
    if (n.dataset.trUnclipped) return;
    const cs = getComputedStyle(n);
    if (cs.display === '-webkit-box') n.style.display = 'block';
    n.style.webkitLineClamp = 'unset';
    n.style.maxHeight = 'none';
    n.style.height = 'auto';
    n.style.minHeight = '0';
    n.style.overflowY = 'visible';
    n.dataset.trUnclipped = '1';
  }

  /* ---------- the standalone reader ---------- */
  /* Two shapes of Telugu live on languagereactor.com and they want opposite treatment.

     A row of the text is a *line* — Telugu one side, the translation the other — so it takes
     romanization underneath, exactly the way a caption does. A sentence of English explanation
     with one Telugu word quoted inside it is not a line, and hanging a block under that
     paragraph puts the romanization several words away from what it romanizes; those get it
     inline, immediately after the script. The test is only whether the block has Latin letters
     in it, decided ONCE and remembered on the element: the moment romanization is added, every
     box has Latin in it, and re-testing would reclassify every line as prose on the next sweep.

     Neither shape replaces anything, which is the difference from the YouTube panel. On the
     site the whole point of LR is that every word is clickable, and the click target is the
     element holding the script — swap that text out and the dictionary, the colour-coded
     knownness and the save-word buttons all go with it. */
  function doReader(root) {
    if (!opts.reader) return;
    if (opts.readerMode === 'replace') return doPanel(root);

    const scope = root && root.isConnected ? root : document.body;
    const lines = new Map();

    teluguNodes(scope, null).forEach(node => {
      const box = lineBox(node);
      if (!box) return;
      let shape = box.getAttribute(SHAPE);
      if (!shape) {
        shape = /[A-Za-z]/.test(box.textContent) ? 'prose' : 'line';
        box.setAttribute(SHAPE, shape);
      }
      if (shape === 'prose') { annotateInline(node); return; }
      if (!lines.has(box)) lines.set(box, []);
      lines.get(box).push(node);
    });

    lines.forEach((nodes, box) => {
      const text = nodes.map(n => n.nodeValue.trim()).filter(Boolean).join(' ');
      if (!text) return;
      if (box.getAttribute(MARK) === text) return;   // same row, already done
      box.setAttribute(MARK, text);

      let line = box.querySelector(':scope > .tr-rom');
      if (!line) {
        line = document.createElement('div');
        line.className = 'tr-rom tr-reader';
        box.appendChild(line);
      }
      line.textContent = romanize(text);
    });
  }

  /* Romanization as a sibling right after the script, for Telugu quoted inside English prose.
     Tracked in the same WeakSet the panel uses: unlike a row, the text node survives, so
     nothing else would stop the next sweep annotating it again.

     A node that is nothing but Telugu is left alone and given a sibling. A node that mixes the
     two — an explanation sentence with a word quoted inside it — has to be taken apart instead,
     because romanize() passes Latin straight through: romanizing the whole node and appending
     it printed the entire English sentence a second time. Only the Telugu runs get an
     annotation; every other character is put back exactly as it was. */
  const TELUGU_RUN = /[\u0C00-\u0C7F]+(?:[ \u200c\u200d][\u0C00-\u0C7F]+)*/g;

  function annotateInline(node) {
    if (seen.has(node)) return;
    seen.add(node);
    const text = node.nodeValue;

    if (!/[A-Za-z]/.test(text)) {              // all Telugu: never touch the node itself
      const rom = romanize(text);
      if (rom === text) return;
      node.parentNode.insertBefore(after(rom), node.nextSibling);
      return;
    }

    const frag = document.createDocumentFragment();
    let at = 0;
    TELUGU_RUN.lastIndex = 0;
    for (let m; (m = TELUGU_RUN.exec(text)); ) {
      if (m.index > at) frag.append(text.slice(at, m.index));
      const run = document.createTextNode(m[0]);
      seen.add(run);
      frag.append(run, after(romanize(m[0])));
      at = m.index + m[0].length;
    }
    if (!at) return;                            // no run matched; leave it alone
    if (at < text.length) frag.append(text.slice(at));
    node.replaceWith(frag);
  }

  function after(rom) {
    const span = document.createElement('span');
    span.className = 'tr-rom-after';
    span.textContent = ' ' + rom.trim();
    return span;
  }

  /* ---------- run loop ----------
   * The panel used to be updated on a debounced observer: wait 250ms after the last mutation,
   * then re-scan everything. Both halves of that were wrong.
   *
   * Debouncing waits for quiet, and a playing video never goes quiet — Language Reactor keeps
   * touching the panel to track the active line, so each mutation reset the timer and the
   * romanization could stay un-applied for as long as playback continued. That is the lag
   * after clicking a word or reloading. A throttle runs *at least* every interval instead,
   * which is what a continuously-changing page needs.
   *
   * And re-scanning the whole panel meant walking every row to find the one that changed.
   * Only the added subtrees are scanned now, so a re-render costs work proportional to what
   * was re-rendered rather than to the length of the transcript.
   */
  const INTERVAL = 60;
  let timer = null, observer = null, sweep = null, lastRun = 0;
  const pending = new Set();

  function schedule() {
    if (sweep) return;
    const wait = Math.max(0, INTERVAL - (Date.now() - lastRun));
    sweep = setTimeout(() => {
      sweep = null;
      lastRun = Date.now();
      const roots = [...pending];
      pending.clear();
      const pass = LR ? doReader : doPanel;
      if (roots.length > 40) pass();             // a wholesale repaint; one sweep is cheaper
      else roots.forEach(r => pass(r));
    }, wait);
  }

  function start() {
    stop();
    if (!opts.enabled) return;
    // Captions are polled because they are re-rendered per cue. The reader is not: it changes
    // only when the page does, which the observer below already reports.
    if (!LR) timer = setInterval(doCaptions, 300);
    observer = new MutationObserver(muts => {
      for (const m of muts) {
        for (const n of m.addedNodes) {
          if (n.nodeType === 1) pending.add(n);
          else if (n.nodeType === 3 && n.parentElement) pending.add(n.parentElement);
        }
        // A row whose text was rewritten in place reports no added nodes, only characterData.
        if (m.type === 'characterData' && m.target.parentElement) pending.add(m.target.parentElement);
      }
      if (pending.size) schedule();
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    if (LR) { doReader(); return; }
    doCaptions();
    doPanel();
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (sweep) { clearTimeout(sweep); sweep = null; }
    if (observer) { observer.disconnect(); observer = null; }
    pending.clear();
  }

  /* Put the page back the way it was, so switching schemes does not need a reload — and a
     reload on YouTube loses your place in the video, which makes a setting feel expensive. */
  function revert() {
    seen = new WeakSet();
    document.querySelectorAll('.tr-rom').forEach(e => e.remove());
    document.querySelectorAll('.tr-rom-inline').forEach(e => e.remove());
    document.querySelectorAll('.tr-rom-after').forEach(e => e.remove());
    document.querySelectorAll(`[${SHAPE}]`).forEach(e => e.removeAttribute(SHAPE));
    document.querySelectorAll('.tr-script').forEach(e => {
      e.replaceWith(document.createTextNode(e.textContent));
    });
    document.querySelectorAll(`[${MARK}]`).forEach(e => {
      // A caption rewritten in place has to be restored from the copy kept in the attribute.
      if (opts.captionMode === 'replace') {
        const t = [...e.childNodes].find(n => n.nodeType === 3);
        if (t) t.nodeValue = e.getAttribute(MARK);
      }
      e.removeAttribute(MARK);
    });
    document.querySelectorAll('[data-tr-unclipped]').forEach(e => {
      e.style.webkitLineClamp = ''; e.style.maxHeight = ''; e.style.display = '';
      e.style.overflowY = ''; e.style.height = ''; e.style.minHeight = '';
      delete e.dataset.trUnclipped;
      delete e.dataset.trUnclipped;
    });
  }

  chrome.storage.sync.get(DEFAULTS, stored => {
    opts = { ...DEFAULTS, ...stored };
    start();
  });

  chrome.storage.onChanged.addListener(changes => {
    const next = { ...opts };
    let touched = false;
    for (const k in changes) if (k in next) { next[k] = changes[k].newValue; touched = true; }
    if (!touched) return;
    revert();               // undo using the OLD options, before they are replaced
    opts = next;
    start();
  });
})();
