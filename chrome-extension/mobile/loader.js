/* The mobile payload: everything the extension gets from Chrome, rebuilt for a bookmarklet.
 *
 * WHY THIS EXISTS AT ALL
 * Neither phone can run the extension. Chrome for Android has never supported extensions, and
 * Chrome for iOS is WebKit with no extension API. What every mobile browser *can* do is run a
 * bookmark whose address is javascript:, which loads this file into the page you are looking at.
 *
 * WHY IT LOADS src/ RATHER THAN BUNDLING IT
 * A bundle would be a fourth copy of te2rom.js. There are already three, and check_te2rom.py
 * exists because three was one too many. This loads the same files the extension loads, from the
 * Pages deploy of this repo, so there is nothing to rebuild and nothing to drift: fix content.js,
 * push, and the phone has the fix on the next tap.
 *
 * WHY THE PHONE IS ALLOWED TO DO THIS
 * languagereactor.com sends no Content-Security-Policy — no header, no meta tag — so a script
 * element pointing at another origin is not blocked. If that ever changes this file stops
 * loading and the page is simply un-annotated; nothing breaks and nothing is lost, because the
 * text itself lives in the LR account and is never modified.
 */
(() => {
  const me = document.currentScript;
  const src = (me && me.src) || '';
  const base = src.replace(/\/mobile\/loader\.js.*$/, '/src/');
  const q = (k, d) => { try { return new URL(src).searchParams.get(k) || d; } catch (e) { return d; } };
  const scheme = q('scheme', 'iso');
  const bust = q('v', '');

  /* Settings live in localStorage on languagereactor.com's own origin, which is the closest
     thing to chrome.storage.sync a page script has. Per-device, not synced — but the only
     setting that matters on a phone is which scheme, and the bookmark you tapped decides that. */
  const KEY = 'tr-opts';
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  const write = o => { try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} };

  /* A second tap is not a second install. Same bookmark: turn it off, and again to turn it back
     on. The other bookmark: switch scheme. Both go through storage rather than doing anything
     themselves, because content.js already reverts and re-applies on a storage change — that is
     how the popup's switches work on the desktop, and it is the reason this file needs no
     teardown code of its own. */
  if (window.__trLoaded) {
    const cur = read();
    if ((cur.scheme || 'iso') !== scheme) window.chrome.storage.sync.set({ scheme, enabled: true });
    else window.chrome.storage.sync.set({ enabled: cur.enabled === false });
    return;
  }
  window.__trLoaded = true;
  window.__trReader = true;

  const listeners = [];
  const c = window.chrome || (window.chrome = {});
  if (!c.storage) {
    c.storage = {
      sync: {
        get(defaults, cb) { cb(Object.assign({}, defaults, read())); },
        set(obj, cb) {
          write(Object.assign(read(), obj));
          const changes = {};
          for (const k in obj) changes[k] = { newValue: obj[k] };
          listeners.forEach(f => f(changes));
          if (cb) cb();
        },
      },
      onChanged: { addListener: f => listeners.push(f) },
    };
  }
  c.storage.sync.set({ scheme, enabled: true });

  const url = f => base + f + (bust ? '?v=' + encodeURIComponent(bust) : '');

  const css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = url('content.css');
  document.head.appendChild(css);

  /* In order, and waiting for each: content.js reads Te2Rom and Colloquial the moment it runs,
     and those are `const` at the top level of their files — a second copy would throw on
     redeclaration rather than quietly winning, so order is not a preference here. */
  ['te2rom.js', 'colloquial.js', 'content.js'].reduce(
    (p, f) => p.then(() => new Promise((ok, no) => {
      const s = document.createElement('script');
      s.src = url(f);
      s.onload = ok;
      s.onerror = () => no(new Error('could not load ' + f));
      document.head.appendChild(s);
    })),
    Promise.resolve()
  ).catch(e => {
    window.__trLoaded = false;          // let the next tap try again
    alert('Telugu Romanizer: ' + e.message);
  });
})();
