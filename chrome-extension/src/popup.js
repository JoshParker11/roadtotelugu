/* The popup is the fast path: the four switches worth flipping mid-video. Anything that needs
   typing lives in options.html instead. */
const DEFAULTS = { enabled: true, scheme: 'iso', captions: true, panel: true,
                   hideScriptInPanel: true };
const BOOLS = ['enabled', 'captions', 'panel', 'hideScriptInPanel'];

chrome.storage.sync.get(DEFAULTS, o => {
  BOOLS.forEach(k => {
    const el = document.getElementById(k);
    el.checked = !!o[k];
    el.addEventListener('change', () => chrome.storage.sync.set({ [k]: el.checked }));
  });
  paintScheme(o.scheme);
});

function paintScheme(v) {
  document.querySelectorAll('#scheme button').forEach(b =>
    b.classList.toggle('on', b.dataset.scheme === v));
}

document.getElementById('scheme').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  chrome.storage.sync.set({ scheme: b.dataset.scheme });
  paintScheme(b.dataset.scheme);
});

document.getElementById('more').addEventListener('click', e => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});
