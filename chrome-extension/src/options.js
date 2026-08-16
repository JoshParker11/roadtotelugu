const DEFAULTS = { enabled: true, scheme: 'iso', captions: true, panel: true,
                   hideScriptInPanel: true, panelSelector: '' };
const BOOLS = ['captions', 'panel', 'hideScriptInPanel'];

/* A live sample, because "colloquial" means nothing until you see what it does to a word you
   recognise. These are all in the deck. */
const SAMPLES = ['నేను', 'కూడా', 'ఆయన', 'తిను', 'ఇంట్లో', 'వెళ్ళు', 'చేస్తున్నాను'];

function paintDemo(scheme) {
  document.getElementById('demo').innerHTML = SAMPLES.map(s =>
    `<div><b>${s}</b><span>${scheme === 'colloquial' ? Colloquial.romanize(s) : Te2Rom.romanize(s)}</span></div>`
  ).join('');
}

function paintScheme(v) {
  document.querySelectorAll('#scheme button').forEach(b =>
    b.classList.toggle('on', b.dataset.scheme === v));
  paintDemo(v);
}

const say = m => {
  const el = document.getElementById('saved');
  el.textContent = m;
  clearTimeout(say._t);
  say._t = setTimeout(() => { el.textContent = ''; }, 1600);
};

chrome.storage.sync.get(DEFAULTS, o => {
  BOOLS.forEach(k => {
    const el = document.getElementById(k);
    el.checked = !!o[k];
    el.addEventListener('change', () => {
      chrome.storage.sync.set({ [k]: el.checked }); say('Saved.');
    });
  });
  const sel = document.getElementById('panelSelector');
  sel.value = o.panelSelector || '';
  sel.addEventListener('change', () => {
    chrome.storage.sync.set({ panelSelector: sel.value.trim() }); say('Saved.');
  });
  paintScheme(o.scheme);
});

document.getElementById('scheme').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  chrome.storage.sync.set({ scheme: b.dataset.scheme });
  paintScheme(b.dataset.scheme);
  say('Saved.');
});
