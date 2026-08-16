/* Annotate Telugu script on YouTube with romanization.
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

  const DEFAULTS = {
    enabled: true,
    scheme: 'iso',              // 'iso' | 'colloquial'
    captions: true,
    captionMode: 'under',       // 'under' | 'replace'
    panel: true,
    panelSelector: '',
    hideScriptInPanel: true,
    relaxClipping: true,
  };

  let opts = { ...DEFAULTS };
  const seen = new WeakSet();

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
        if (p.closest('.tr-rom, .tr-rom-inline, script, style, textarea, input, [contenteditable]')) {
          return NodeFilter.FILTER_REJECT;
        }
        if (!!p.closest(PLAYER) !== wantPlayer) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    for (let n = walker.nextNode(); n; n = walker.nextNode()) out.push(n);
    return out;
  };

  /* ---------- captions ---------- */
  function doCaptions() {
    if (!opts.captions) return;
    const player = document.querySelector('#movie_player') || document.body;

    teluguNodes(player, true).forEach(node => {
      const host = node.parentElement;
      if (!host) return;
      const text = node.nodeValue;

      if (opts.captionMode === 'replace') {
        // Writing the node in place keeps whatever wraps it — including LR's per-word spans if
        // it has split the line — so the layout survives even though the letters change.
        if (host.getAttribute(MARK) === text) return;
        host.setAttribute(MARK, text);
        node.nodeValue = romanize(text);
        return;
      }

      // 'under': one extra line per caption host, refreshed when the cue changes.
      if (host.getAttribute(MARK) === text) return;
      host.setAttribute(MARK, text);
      let line = host.querySelector(':scope > .tr-rom');
      if (!line) {
        line = document.createElement('div');
        line.className = 'tr-rom';
        host.appendChild(line);
      }
      line.textContent = romanize(host.getAttribute(MARK));
    });
  }

  /* ---------- panel ---------- */
  function panelRoot() {
    if (opts.panelSelector) {
      try { return document.querySelector(opts.panelSelector); } catch { return null; }
    }
    return document.body;
  }

  function doPanel() {
    if (!opts.panel) return;
    teluguNodes(panelRoot(), false).forEach(node => {
      if (seen.has(node)) return;
      const original = node.nodeValue;
      const rom = romanize(original);
      if (rom === original) { seen.add(node); return; }

      const span = document.createElement('span');
      span.className = 'tr-rom-inline';
      span.textContent = rom;

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

  /* Romanization runs longer than the script it replaces — often by half again — so rows that
     were sized for Telugu clip it. LR's own classes are off limits, so instead: walk up from a
     line we just changed and relax whatever is doing the clipping, on that element only.
     Bounded to a few levels so a stray `overflow:hidden` high up in the page is left alone. */
  function unclip(el) {
    for (let n = el.parentElement, depth = 0; n && depth < 5; n = n.parentElement, depth++) {
      if (n.dataset.trUnclipped) return;
      const cs = getComputedStyle(n);
      let touched = false;
      if (cs.webkitLineClamp && cs.webkitLineClamp !== 'none') {
        n.style.webkitLineClamp = 'unset'; touched = true;
      }
      if (cs.maxHeight && cs.maxHeight !== 'none') { n.style.maxHeight = 'none'; touched = true; }
      if (/^\d/.test(cs.height) && cs.overflow !== 'visible') {
        n.style.height = 'auto'; n.style.minHeight = '0'; touched = true;
      }
      if (cs.overflow === 'hidden' || cs.overflowY === 'hidden') {
        // Only the vertical clip — leaving overflow-x alone keeps horizontal scrollers working.
        n.style.overflowY = 'visible'; touched = true;
      }
      if (cs.whiteSpace === 'nowrap') { n.style.whiteSpace = 'normal'; touched = true; }
      if (touched) n.dataset.trUnclipped = '1';
    }
  }

  /* ---------- run loop ---------- */
  let timer = null, observer = null;

  function start() {
    stop();
    if (!opts.enabled) return;
    // Captions change several times a minute; polling is steadier and cheaper than observing
    // a page that mutates constantly for reasons unrelated to us.
    timer = setInterval(doCaptions, 300);
    observer = new MutationObserver(() => {
      clearTimeout(observer._t);
      observer._t = setTimeout(doPanel, 250);   // LR repaints its list in bursts
    });
    observer.observe(document.body, { childList: true, subtree: true });
    doCaptions();
    doPanel();
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (observer) { observer.disconnect(); observer = null; }
  }

  /* Put the page back the way it was, so switching schemes does not need a reload — and a
     reload on YouTube loses your place in the video, which makes a setting feel expensive. */
  function revert() {
    document.querySelectorAll('.tr-rom').forEach(e => e.remove());
    document.querySelectorAll('.tr-rom-inline').forEach(e => e.remove());
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
      e.style.webkitLineClamp = ''; e.style.maxHeight = ''; e.style.height = '';
      e.style.minHeight = ''; e.style.overflowY = ''; e.style.whiteSpace = '';
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
