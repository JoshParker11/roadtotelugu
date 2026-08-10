/* Shared state, scheduling and rendering for the Verb Lab.
 * No build step, no dependencies, everything in localStorage. */

const Lab = (() => {
  const K = { sel:'vlab.selection', scope:'vlab.scope', prog:'vlab.progress',
              ver:'vlab.verified', opt:'vlab.options', last:'vlab.lastSession' };

  const read  = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const today = () => Math.floor(Date.now() / 86400000);

  /* ---- scope presets: which paradigms a session covers ---- */
  const SCOPES = {
    core: { label:'The core five',
            blurb:'Habitual/future, present continuous, past, and both negatives — across all six persons.',
            forms:['future','present','past','negFuture','negPast'] },
    moods:{ label:'Core five + moods',
            blurb:'Adds the imperatives, prohibitives, let’s, must and can. This is the everyday working set.',
            forms:['future','present','past','negFuture','negPast','impFam','impPol','prohibFam','prohibPol','hort','must','can'] },
    all:  { label:'Everything',
            blurb:'Adds the purposive and the conditional. The conditional is the least settled form here.',
            forms:null }
  };

  /* ---- selection ---- */
  const getSel   = () => read(K.sel, ['cheyi','ra','tinu','vellu','undu']);
  const setSel   = v  => write(K.sel, v);
  const getScope = () => read(K.scope, 'core');
  const setScope = v  => write(K.scope, v);
  const getOpts  = () => Object.assign({ type:false, notice:true, len:40 }, read(K.opt, {}));
  const setOpts  = v  => write(K.opt, Object.assign(getOpts(), v));

  /* ---- Leitner-ish progress, keyed by verb|form|person ---- */
  const getProg = () => read(K.prog, {});
  const setProg = p  => write(K.prog, p);
  const GAPS = [0, 1, 3, 7, 16, 35];

  function grade(key, g) {                 // g: 0 missed, 1 shaky, 2 got it
    const p = getProg();
    const r = p[key] || { box:0, due:0, seen:0, wrong:0 };
    r.seen++;
    if (g === 2)      r.box = Math.min(r.box + 1, GAPS.length - 1);
    else if (g === 1) r.box = Math.max(r.box, 1);
    else            { r.box = 0; r.wrong++; }
    r.due = today() + GAPS[r.box];
    r.last = today();
    p[key] = r; setProg(p);
  }
  const stateOf = key => getProg()[key] || null;

  /* ---- session assembly ----
   * Due items first, then never-seen, then the rest — that is the spacing part.
   * Then shuffle inside those bands and de-cluster by verb, which is the interleaving
   * part: consecutive items should force a switch of verb rather than walking a
   * paradigm top to bottom. */
  function buildSession(items, len) {
    const p = getProg(), d = today();
    const band = it => {
      const r = p[it.key];
      if (!r) return 1;                    // new
      if (r.due <= d) return 0;            // due
      return 2;                            // ahead of schedule
    };
    const bands = [[], [], []];
    items.forEach(it => bands[band(it)].push(it));
    bands.forEach(shuffle);
    const picked = [...bands[0], ...bands[1], ...bands[2]].slice(0, len);
    return decluster(picked);
  }

  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /* Greedy reorder: never take an item from the same verb as the previous one
     unless nothing else is left. */
  function decluster(list) {
    const out = [], pool = list.slice();
    let prev = null;
    while (pool.length) {
      let i = pool.findIndex(x => x.verb !== prev);
      if (i === -1) i = 0;
      out.push(pool[i]); prev = pool[i].verb; pool.splice(i, 1);
    }
    return out;
  }

  /* ---- typed-answer checking: forgiving about diacritics, not about letters ---- */
  const FOLD = { 'ā':'a','ī':'i','ū':'u','ē':'e','ō':'o','ṭ':'t','ḍ':'d','ṇ':'n','ḷ':'l','ṁ':'m','ṣ':'s','ś':'s','ṛ':'r' };
  function fold(s) {
    return (s || '').toLowerCase().trim()
      .replace(/[āīūēōṭḍṇḷṁṣśṛ]/g, c => FOLD[c])
      .replace(/ch/g, 'c').replace(/nn/g, 'n').replace(/ll/g, 'l')
      .replace(/tt/g, 't').replace(/dd/g, 'd').replace(/pp/g, 'p').replace(/vv/g, 'v').replace(/cc/g, 'c')
      .replace(/[^a-z ]/g, '').replace(/\s+/g, ' ');
  }
  const matches = (typed, answer) => fold(typed) === fold(answer);

  /* ---- native-speaker verification, recorded per verb ---- */
  const getVerified = () => read(K.ver, {});
  function setVerified(id, on) {
    const v = getVerified();
    if (on) v[id] = today(); else delete v[id];
    write(K.ver, v);
  }

  const saveLast = s => write(K.last, s);
  const getLast  = () => read(K.last, null);

  function resetAll() { Object.values(K).forEach(k => localStorage.removeItem(k)); }

  return { SCOPES, getSel, setSel, getScope, setScope, getOpts, setOpts,
           getProg, grade, stateOf, buildSession, shuffle, matches, fold,
           getVerified, setVerified, saveLast, getLast, resetAll, today };
})();

/* ---------- shared rendering ---------- */

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));

/* A paradigm table for one verb: person rows, one column per selected paradigm. */
function paradigmTable(v, formIds) {
  const personForms = FORMS.filter(f => f.person && (!formIds || formIds.includes(f.id)));
  if (!personForms.length) return '';
  let h = '<div class="para-wrap"><table class="para"><thead><tr><th>Person</th>';
  personForms.forEach(f => { h += `<th>${esc(f.label)}</th>`; });
  h += '</tr></thead><tbody>';
  PERSONS.forEach((p, i) => {
    h += `<tr><td class="rowlab"><b>${esc(p.en)}</b>${esc(p.pron[0])} · <span class="tel">${esc(p.pron[1])}</span></td>`;
    personForms.forEach(f => {
      /* person-invariant forms are printed once and then marked, so the eye can see
         at a glance that the verb genuinely does not move */
      h += (f.invariant && i > 0)
        ? '<td><span class="same">↑ unchanged</span></td>'
        : `<td>${segCell(segment(v, f.id, i))}</td>`;
    });
    h += '</tr>';
  });
  return h + '</tbody></table></div>';
}

function segCell(seg) {
  if (!seg) return '—';
  if (seg.whole) return `<span class="r">${esc(seg.whole[0])}</span><span class="t">${esc(seg.whole[1])}</span>`;
  return `<span class="r"><span class="stemtxt">${esc(seg.stem[0])}</span><span class="endtxt">${esc(seg.end[0])}</span></span>` +
         `<span class="t"><span class="stemtxt">${esc(seg.stem[1])}</span><span class="endtxt">${esc(seg.end[1])}</span></span>`;
}

/* The one-per-verb forms (imperatives, must, can …) as cards. */
function singleCards(v, formIds) {
  const fs = FORMS.filter(f => !f.person && (!formIds || formIds.includes(f.id)));
  const out = fs.map(f => {
    const a = conjugate(v, f.id, 0);
    if (!a) return `<div class="single"><span>${esc(f.label)}</span><span class="r" style="color:var(--cream-dim)">— not natural for this verb</span></div>`;
    const seg = segment(v, f.id, 0);
    const reg = f.reg === 'respectful' ? '<b class="tagreg resp">respectful</b>'
              : f.reg === 'informal'   ? '<b class="tagreg inf">informal</b>' : '';
    const chk = (f.conf === 'check' || v.conf === 'check') ? '<b class="tagreg chk">check</b>' : '';
    return `<div class="single"><span>${esc(f.label)}${reg}${chk}</span>${segCell(seg).replace(/class="r"/, 'class="r"')}<span class="g">${esc(f.gloss)}</span></div>`;
  });
  return out.length ? `<div class="single-grid">${out.join('')}</div>` : '';
}

function stemStrip(v) {
  const bits = [['root','root',rootOf(v)], ['non-past', 'np', [v.np[0] + v.T[0] + '-', v.np[1] + v.T[1]]],
                ['past','pst',[v.pst[0] + '-', v.pst[1]]], ['negative','neg',[v.neg[0] + '-', v.neg[1]]],
                ['short-a','a',[v.a[0] + '-', v.a[1]]], ['infinitive','inf',[v.inf[0] + '-', v.inf[1]]]];
  return '<div class="stem-strip">' + bits.map(([lab, , pair]) =>
    `<div class="stem"><span>${lab}</span><b>${esc(pair[0])}</b><i>${esc(pair[1])}</i></div>`).join('') + '</div>';
}

function verbById(id) { return VERBS.find(v => v.id === id); }
