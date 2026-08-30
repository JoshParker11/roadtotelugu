/* The popup is the fast path: the four switches worth flipping mid-video. Anything that needs
   typing lives in options.html instead. */
const DEFAULTS = { enabled: true, scheme: 'iso', captions: true, panel: true,
                   hideScriptInPanel: true, panelScale: 100, reader: true };
const BOOLS = ['enabled', 'captions', 'panel', 'hideScriptInPanel', 'reader'];

chrome.storage.sync.get(DEFAULTS, o => {
  BOOLS.forEach(k => {
    const el = document.getElementById(k);
    el.checked = !!o[k];
    el.addEventListener('change', () => chrome.storage.sync.set({ [k]: el.checked }));
  });
  const sc = document.getElementById('panelScale');
  sc.value = o.panelScale || 100;
  document.getElementById('scaleval').textContent = sc.value + '%';
  sc.addEventListener('input', () => {
    document.getElementById('scaleval').textContent = sc.value + '%';
    chrome.storage.sync.set({ panelScale: +sc.value });
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
