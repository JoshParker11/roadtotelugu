/* The vocabulary queue page. Reads WORD_DATA (data/words.js) and Progress (progress.js).
 *
 * Rendering: the whole list is one innerHTML assignment, rebuilt on filter/search/grouping
 * changes. 2,200 rows costs a few tens of milliseconds, which is cheaper in both code and
 * bugs than virtualising, and this page is opened once per session, not scrolled in a loop.
 * Marking, which *does* happen in a loop, never re-renders: it patches the one row it
 * touched. That also keeps a row from vanishing under the cursor the moment you mark it —
 * filters re-apply on the next deliberate filter change, not mid-scan.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  /* rows are arrays; hydrate once */
  const F = WORD_DATA.fields;
  const WORDS = WORD_DATA.words.map(r => {
    const o = {}; F.forEach((k, i) => o[k] = r[i]); return o;
  });
  const UNLOCKS = WORD_DATA.unlocks;
  const LAST_DAY = WORD_DATA.counts.lastDay;

  /* Search folds diacritics so "nenu" finds nēnu and "vellu" finds veḷḷu — nobody types the
     macrons into a search box, and refusing to match them makes the box useless. */
  const FOLD = { 'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ḷ': 'l', 'ṁ': 'm', 'ṣ': 's', 'ś': 's', 'ṛ': 'r' };
  const fold = s => (s || '').toLowerCase().replace(/[āīūēōṭḍṇḷṁṣśṛ]/g, c => FOLD[c]);
  WORDS.forEach(w => { w.hay = fold(w.roman + ' ' + w.english + ' ' + w.island + ' ' + w.pos) + ' ' + w.telugu; });

  const BY_GUID = new Map(WORDS.map(w => [w.guid, w]));

  /* ---------- view state (not persisted; it is a lens, not a decision) ---------- */
  let filter = 'all', group = 'day', query = '';

  /* One definition per filter, used by both the list and the chip counts. When those were two
     switch statements they disagreed about whether a known word still counts as introduced,
     and the chip said 45 while the list showed 44. */
  const FILTERS = [
    ['all',    'All',            () => true],
    ['today',  'Today',          (w, c) => !!w.day && w.day === c.day],
    ['seen',   'Introduced',     (w, c) => !!w.order && w.order <= c.introduced],
    ['todo',   'Not yet known',  (w, c) => !!w.order && w.order <= c.introduced && !c.known[w.guid]],
    ['known',  'Known',          (w, c) => !!c.known[w.guid]],
    ['hard',   'Needs work',     (w, c) => !!c.hard[w.guid]],
    ['queued', 'Upcoming',       (w, c) => !!w.order && w.order > c.introduced],
    ['held',   'Held out',       w => !w.order],
  ];
  const PRED = Object.fromEntries(FILTERS.map(([id, , fn]) => [id, fn]));

  /* Snapshot the things every predicate needs, once per render, instead of recomputing the
     day number and re-reading the marks for each of 2,200 rows. */
  const ctx = () => ({ day: Progress.dayNumber(), introduced: Progress.introducedCount(),
                       known: Progress.getKnown(), hard: Progress.getHard() });

  const matchesQuery = w => !query || w.hay.includes(query);

  /* ---------- stats ---------- */
  const nf = n => n.toLocaleString('en-US');

  function renderStats() {
    const s = Progress.summary(WORDS);
    const configured = Progress.isConfigured();
    const cap = Math.min(s.introduced, WORD_DATA.counts.scheduled);

    $('#st-day').innerHTML = configured
      ? `<strong class="amber">Day ${nf(s.day)}</strong><i>${dayDateLabel(s.day)}</i>`
      : `<strong class="amber">—</strong><i>set a start date</i>`;
    $('#st-seen').innerHTML =
      `<strong>${nf(cap)}</strong><i>of ${nf(WORD_DATA.counts.scheduled)} · ${pct(cap, WORD_DATA.counts.scheduled)}</i>`;
    $('#st-known').innerHTML =
      `<strong class="moss">${nf(s.known)}</strong><i>${s.knownAhead ? nf(s.knownAhead) + ' ahead of schedule' : 'marked by hand'}</i>`;
    $('#st-hard').innerHTML =
      `<strong class="${s.hard ? 'flame' : ''}">${nf(s.hard)}</strong><i>flagged to revisit</i>`;
    $('#st-sent').innerHTML =
      `<strong>${nf(sentencesUpTo(s.day))}</strong><i>of ${nf(WORD_DATA.counts.sentencesDated)} readable</i>`;

    const left = WORD_DATA.counts.scheduled - cap;
    $('#st-left').innerHTML = left > 0
      ? `<strong>${nf(Math.ceil(left / Progress.getSetup().rate))}</strong><i>days of new words left</i>`
      : `<strong class="moss">0</strong><i>queue complete</i>`;
  }

  const pct = (a, b) => b ? Math.round(a / b * 100) + '%' : '0%';
  const sentencesUpTo = day => {
    let n = 0;
    for (const k in UNLOCKS) if (+k <= day) n += UNLOCKS[k];
    return n;
  };

  function dayDateLabel(d) {
    const dt = Progress.dateOfDay(d);
    if (!dt) return '';
    return dt.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  /* ---------- setup ---------- */
  function renderSetup() {
    const s = Progress.getSetup();
    $('#in-start').value = s.start;
    $('#in-rate').value = s.rate;
    $('#in-skip').value = s.skip;
    $('#setup').classList.toggle('unset', !Progress.isConfigured());
    const d = Progress.dayNumber();
    $('#setup-read').innerHTML = Progress.isConfigured()
      ? `Today is <b>day ${d}</b> — the schedule says words <b>1–${nf(Math.min(d * s.rate, WORD_DATA.counts.scheduled))}</b> have been introduced. ` +
        `The full queue runs to day <b>${LAST_DAY}</b>.`
      : `Nothing is marked as introduced until a start date is set. Day 1 is the first day you took new cards.`;
  }

  /* ---------- today ---------- */
  function renderToday() {
    const d = Progress.dayNumber(), host = $('#today-list'), head = $('#today-when');
    if (!Progress.isConfigured()) {
      head.textContent = '';
      host.innerHTML = `<p class="empty">Set a start date above and today's fifteen words appear here.</p>`;
      return;
    }
    if (d < 1) {
      head.textContent = 'not started yet';
      host.innerHTML = `<p class="empty">The start date is in the future. Day 1 is ${dayDateLabel(1)}.</p>`;
      return;
    }
    if (d > LAST_DAY) {
      head.textContent = `day ${d}`;
      host.innerHTML = `<p class="empty">Past the end of the queue — all ${nf(WORD_DATA.counts.scheduled)} scheduled words have been introduced.</p>`;
      return;
    }
    const today = WORDS.filter(w => w.day === d);
    head.textContent = `day ${d} · ${dayDateLabel(d)} · ${UNLOCKS[d] || 0} sentences unlock`;
    host.innerHTML = today.map(w => {
      const st = Progress.stateOf(w);
      return `<div class="twd ${st === 'known' ? 'is-known' : st === 'hard' ? 'is-hard' : ''}" data-g="${esc(w.guid)}">
        <span class="en">${esc(w.english)}</span>
        <span class="rom">${esc(w.roman)}</span>
        <span class="tg">${esc(w.telugu)}</span></div>`;
    }).join('');
  }

  /* ---------- the list ---------- */
  function groupsFor(rows) {
    const map = new Map();
    if (group === 'day') {
      rows.forEach(w => {
        const k = w.day || 0;
        if (!map.has(k)) map.set(k, []);
        map.get(k).push(w);
      });
      return [...map.entries()].sort((a, b) => (a[0] || 1e9) - (b[0] || 1e9));
    }
    rows.forEach(w => {
      const k = w.island || 'Unsorted';
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(w);
    });
    return [...map.entries()].sort((a, b) =>
      (a[0] === 'Unsorted') - (b[0] === 'Unsorted') || b[1].length - a[1].length);
  }

  function groupHead(key, list) {
    const today = Progress.dayNumber();
    const allKnown = list.every(w => Progress.isKnown(w.guid));
    const btn = `<button class="gmark" data-group="${esc(key)}" data-on="${allKnown ? '0' : '1'}">${allKnown ? 'clear known' : 'all known'}</button>`;
    if (group !== 'day') {
      return `<div class="group-head"><b>${esc(key)}</b>
        <span class="gmeta">${list.length} word${list.length === 1 ? '' : 's'}</span>${btn}</div>`;
    }
    const d = +key;
    if (!d) return `<div class="group-head"><b>Not scheduled</b>
      <span class="gmeta">${list.length} held out of the deck</span>${btn}</div>`;
    const cls = Progress.isConfigured() ? (d === today ? 'now' : d < today ? 'past' : '') : '';
    const when = Progress.isConfigured() ? ` · ${dayDateLabel(d)}` : '';
    return `<div class="group-head ${cls}"><b>Day ${d}</b>
      <span class="gmeta">${list.length} word${list.length === 1 ? '' : 's'}${when} · ${UNLOCKS[d] || 0} sentences unlock</span>${btn}</div>`;
  }

  function rowHTML(w) {
    const st = Progress.stateOf(w);
    const known = Progress.isKnown(w.guid), hard = Progress.isHard(w.guid);
    const tags = [];
    if (group !== 'day' && w.day) tags.push(`<span class="tag day">day ${w.day}</span>`);
    if (w.lesson) tags.push(`<span class="tag">lesson ${esc(w.lesson)}</span>`);
    if (group === 'day' && w.island) tags.push(`<span class="tag">${esc(w.island)}</span>`);
    if (w.flags) tags.push(`<span class="tag held">${esc(w.flags)}</span>`);
    return `<div class="wrow ${st}" data-g="${esc(w.guid)}">
      <div class="marks">
        <button class="mk known${known ? ' on' : ''}" data-act="known" aria-pressed="${known}" title="I know this word">✓</button>
        <button class="mk hard${hard ? ' on' : ''}" data-act="hard" aria-pressed="${hard}" title="Flag to revisit">!</button>
      </div>
      <div class="ord">${w.order || '—'}</div>
      <div class="en">${esc(w.english)}</div>
      <div class="rom">${esc(w.roman)}</div>
      <div class="tg">${esc(w.telugu)}</div>
      <div class="meta">${tags.join('')}</div>
    </div>`;
  }

  function renderList() {
    const c = ctx(), pred = PRED[filter];
    const rows = WORDS.filter(w => pred(w, c) && matchesQuery(w));
    $('#count').innerHTML = `<b>${nf(rows.length)}</b> of ${nf(WORDS.length)}`;
    const host = $('#list');
    if (!rows.length) {
      host.innerHTML = `<p class="empty">Nothing matches. ${query ? 'Try a different search.' : 'Try another filter.'}</p>`;
      return;
    }
    host.innerHTML = groupsFor(rows)
      .map(([k, list]) => groupHead(k, list) + list.map(rowHTML).join(''))
      .join('');
  }

  function renderChips() {
    const c = ctx();
    const n = Object.fromEntries(FILTERS.map(([id]) => [id, 0]));
    WORDS.forEach(w => FILTERS.forEach(([id, , fn]) => { if (fn(w, c)) n[id]++; }));
    $('#filters').innerHTML = FILTERS.map(([id, label]) =>
      `<button class="chip${filter === id ? ' on' : ''}" data-filter="${id}">${label}<b>${nf(n[id])}</b></button>`).join('');
  }

  /* Marking patches one row rather than re-rendering, so a long marking pass does not
     re-lay-out two thousand rows fifteen times. */
  function patch(guid) {
    const w = BY_GUID.get(guid);
    document.querySelectorAll(`.wrow[data-g="${CSS.escape(guid)}"]`).forEach(el => {
      el.className = 'wrow ' + Progress.stateOf(w);
      const k = Progress.isKnown(guid), h = Progress.isHard(guid);
      const kb = el.querySelector('.mk.known'), hb = el.querySelector('.mk.hard');
      kb.classList.toggle('on', k); kb.setAttribute('aria-pressed', k);
      hb.classList.toggle('on', h); hb.setAttribute('aria-pressed', h);
    });
    document.querySelectorAll(`.twd[data-g="${CSS.escape(guid)}"]`).forEach(el => {
      el.classList.toggle('is-known', Progress.isKnown(guid));
      el.classList.toggle('is-hard', Progress.isHard(guid));
    });
  }

  /* ---------- events ---------- */
  $('#list').addEventListener('click', e => {
    const mk = e.target.closest('.mk');
    if (mk) {
      const guid = mk.closest('.wrow').dataset.g;
      mk.dataset.act === 'known' ? Progress.toggleKnown(guid) : Progress.toggleHard(guid);
      patch(guid); renderStats(); renderChips(); renderToday();
      return;
    }
    const gm = e.target.closest('.gmark');
    if (gm) {
      const head = gm.closest('.group-head');
      const guids = [];
      for (let el = head.nextElementSibling; el && el.classList.contains('wrow'); el = el.nextElementSibling) {
        guids.push(el.dataset.g);
      }
      Progress.markMany(guids, 'known', gm.dataset.on === '1');
      guids.forEach(patch);
      gm.dataset.on = gm.dataset.on === '1' ? '0' : '1';
      gm.textContent = gm.dataset.on === '1' ? 'all known' : 'clear known';
      renderStats(); renderChips(); renderToday();
    }
  });

  $('#filters').addEventListener('click', e => {
    const c = e.target.closest('.chip');
    if (!c) return;
    filter = c.dataset.filter; renderChips(); renderList();
  });

  $('#grouping').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    group = b.dataset.group;
    $('#grouping').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
    renderList();
  });

  let t;
  $('#search').addEventListener('input', e => {
    clearTimeout(t);
    const v = fold(e.target.value.trim());
    t = setTimeout(() => { query = v; renderList(); }, 130);
  });

  ['#in-start', '#in-rate', '#in-skip'].forEach(sel => {
    $(sel).addEventListener('change', () => {
      Progress.setSetup({ start: $('#in-start').value, rate: $('#in-rate').value, skip: $('#in-skip').value });
      renderSetup(); renderStats(); renderToday(); renderChips(); renderList();
    });
  });

  $('#btn-today').addEventListener('click', () => {
    $('#in-start').value = Progress.todayISO();
    $('#in-start').dispatchEvent(new Event('change'));
  });

  /* ---------- backup drawer ---------- */
  const say = (msg, bad) => { const el = $('#say'); el.textContent = msg; el.classList.toggle('bad', !!bad); };

  $('#btn-export').addEventListener('click', () => {
    $('#io').value = Progress.exportState();
    $('#io').select();
    say('Copy this, or use Download. Paste it into the box on another device and press Load.');
  });

  $('#btn-download').addEventListener('click', () => {
    const blob = new Blob([Progress.exportState()], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `telugu-progress-${Progress.todayISO()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    say('Downloaded.');
  });

  $('#btn-import').addEventListener('click', () => {
    try {
      const r = Progress.importState($('#io').value);
      renderSetup(); renderStats(); renderToday(); renderChips(); renderList();
      say(`Loaded — ${r.known} known, ${r.hard} flagged. Merged with what was already here.`);
    } catch (err) {
      say('Could not read that: ' + err.message, true);
    }
  });

  $('#btn-reset').addEventListener('click', () => {
    if (!confirm('Clear the start date and every mark in this browser? This cannot be undone.')) return;
    Progress.reset();
    renderSetup(); renderStats(); renderToday(); renderChips(); renderList();
    say('Cleared.');
  });

  /* Day headers stick below the filter bar, whose height depends on how many rows the chips
     wrap onto — which depends on the viewport. Measure it rather than guessing a constant. */
  const controls = document.querySelector('.controls');
  function measureStick() {
    const nav = document.querySelector('.site-nav').getBoundingClientRect().height;
    document.documentElement.style.setProperty('--navh', nav + 'px');
    document.documentElement.style.setProperty('--stick', (nav + controls.getBoundingClientRect().height - 4) + 'px');
  }
  if (window.ResizeObserver) new ResizeObserver(measureStick).observe(controls);
  window.addEventListener('resize', measureStick);

  /* ---------- boot ---------- */
  $('#generated').textContent = WORD_DATA.generated;
  renderSetup(); renderStats(); renderToday(); renderChips(); renderList();
  measureStick();
})();
