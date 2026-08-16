/* Annotate Telugu script on YouTube with romanization.
 *
 * TWO TARGETS, TWO BEHAVIOURS
 *   captions  the player's own caption line — romanization is ADDED underneath, because the
 *             script is what Language Reactor's click-a-word overlay is attached to and
 *             replacing it would break the tool this is meant to complement.
 *   panel     the Language Reactor transcript panel — romanization REPLACES the script, since
 *             that is a wall of text to read rather than a line to glance at.
 *
 * WHY IT SCANS TEXT NODES RATHER THAN KNOWN SELECTORS
 * YouTube's caption markup is stable enough to target directly. Language Reactor's is not
 * mine to depend on: it is a third-party extension that can restructure its panel in any
 * release, and a hard-coded class would fail silently the day it did. So the panel path finds
 * *any* text node containing Telugu inside a configurable root and annotates that. The default
 * root is broad; the options page takes a narrower CSS selector once you have one.
 *
 * Everything already touched is tracked in a WeakSet, so the MutationObserver that catches new
 * captions does not re-annotate the annotations it just made — the classic way this kind of
 * script ends up in an infinite loop.
 */
(() => {
  const TELUGU = /[ఀ-౿]/;
  const CAPTION_SEL = '.ytp-caption-segment';
  const MARK = 'data-tr-done';

  const DEFAULTS = {
    enabled: true,
    scheme: 'iso',           // 'iso' | 'colloquial'
    captions: true,
    panel: true,
    panelSelector: '',       // empty = scan the whole document outside the player
    hideScriptInPanel: true,
  };

  let opts = { ...DEFAULTS };
  const seen = new WeakSet();

  const romanize = t => opts.scheme === 'colloquial'
    ? Colloquial.romanize(t)
    : Te2Rom.romanize(t);

  /* ---------- captions: add a line underneath ---------- */
  function doCaptions() {
    if (!opts.captions) return;
    document.querySelectorAll(CAPTION_SEL).forEach(seg => {
      const text = seg.textContent || '';
      if (!TELUGU.test(text)) return;
      // The player rewrites the caption element's text on every cue, so compare against what
      // we last romanized rather than trusting a "done" flag.
      if (seg.getAttribute(MARK) === text) return;
      seg.setAttribute(MARK, text);

      let line = seg.nextElementSibling;
      if (!line || !line.classList.contains('tr-rom')) {
        line = document.createElement('div');
        line.className = 'tr-rom';
        seg.after(line);
      }
      line.textContent = romanize(text);
    });
  }

  /* ---------- panel: swap script for romanization ---------- */
  function panelRoot() {
    if (opts.panelSelector) {
      try { return document.querySelector(opts.panelSelector); } catch { return null; }
    }
    return document.body;
  }

  function inPlayer(node) {
    return !!(node.parentElement && node.parentElement.closest(
      '#movie_player, .html5-video-player, .ytp-caption-window-container'));
  }

  function doPanel() {
    if (!opts.panel) return;
    const root = panelRoot();
    if (!root) return;

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (!n.nodeValue || !TELUGU.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
        if (seen.has(n)) return NodeFilter.FILTER_REJECT;
        if (inPlayer(n)) return NodeFilter.FILTER_REJECT;   // captions are handled above
        const p = n.parentElement;
        if (!p || p.closest('.tr-rom, script, style, textarea, input')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    const targets = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) targets.push(n);

    targets.forEach(n => {
      seen.add(n);
      const original = n.nodeValue;
      const rom = romanize(original);
      if (rom === original) return;

      const span = document.createElement('span');
      span.className = 'tr-rom-inline';
      span.textContent = rom;
      // Keep the script in the DOM but hidden, so the original is one setting away and any
      // click handler the host attached to the parent still has its text to work with.
      const keep = document.createElement('span');
      keep.className = 'tr-script';
      keep.textContent = original;
      if (opts.hideScriptInPanel) keep.style.display = 'none';

      const frag = document.createDocumentFragment();
      frag.append(keep, span);
      seen.add(keep.firstChild);
      n.replaceWith(frag);
    });
  }

  /* ---------- run loop ----------
   * Captions change many times a minute; a MutationObserver on the whole document would fire
   * constantly on a YouTube page for reasons that have nothing to do with us. A short interval
   * for the caption line plus an observer for the panel is cheaper and steadier. */
  let timer = null, observer = null;

  function start() {
    stop();
    if (!opts.enabled) return;
    timer = setInterval(doCaptions, 300);
    observer = new MutationObserver(() => {
      clearTimeout(observer._t);
      observer._t = setTimeout(doPanel, 250);   // debounce: LR repaints its list in bursts
    });
    observer.observe(document.body, { childList: true, subtree: true });
    doCaptions();
    doPanel();
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (observer) { observer.disconnect(); observer = null; }
    document.querySelectorAll('.tr-rom').forEach(e => e.remove());
    document.querySelectorAll('.tr-script').forEach(e => { e.style.display = ''; });
  }

  chrome.storage.sync.get(DEFAULTS, stored => {
    opts = { ...DEFAULTS, ...stored };
    start();
  });

  /* Changing a setting must take effect without a reload — a reload on YouTube loses your
     place in the video, which makes the option feel expensive to try. */
  chrome.storage.onChanged.addListener(changes => {
    let touched = false;
    for (const k in changes) {
      if (k in opts) { opts[k] = changes[k].newValue; touched = true; }
    }
    if (!touched) return;
    document.querySelectorAll('.tr-rom, .tr-rom-inline').forEach(e => e.remove());
    document.querySelectorAll(`[${MARK}]`).forEach(e => e.removeAttribute(MARK));
    document.querySelectorAll('.tr-script').forEach(e => {
      e.style.display = opts.hideScriptInPanel ? 'none' : '';
    });
    start();
  });
})();
