/* Export, import and merge this browser's learning state.
 *
 * WHY MERGE AND NOT OVERWRITE
 * Two devices are both real. Reading on the phone in the morning and the laptop at night means
 * each holds progress the other has never seen, and "import" that clobbers is a trap: it works
 * until the first time you do it in the wrong direction and lose a day's work. So the only
 * operation is a merge, and it is safe to run in either direction, twice, or out of order.
 *
 * WHAT DECIDES A CONFLICT
 * WordLevels stores [level, date] per word, so the newer mark wins on its own evidence. Only
 * when two marks share a date — the same word touched on both devices the same day — does it
 * fall back to keeping the further-along one, because the alternative is asking a question
 * nobody can answer from the data.
 *
 * Deliberate downgrades are the one thing this cannot preserve across a same-day conflict: if
 * you demote a word on the phone and promote it on the laptop on the same date, the promotion
 * wins. Dropping to a per-word clock instead of a date would fix it and is not worth the bytes
 * for a case that resolves itself the next time you mark the word.
 *
 * THE CODE IS SELF-DESCRIBING
 * A version, a checksum and a timestamp ride inside it. Pasting a truncated or foreign string
 * is the likely failure — long codes get mangled by chat apps and mail clients — and it should
 * say so rather than silently importing half a vocabulary.
 */
const Sync = (() => {
  const KEYS = ['rtt.msLevel', 'rtt.msSnap', 'rtt.msAct', 'rtt.msMeaning',
                'rtt.msRead', 'rtt.msGoal', 'rtt.known', 'rtt.hard'];
  const VERSION = 1;

  const readKey = k => { try { return JSON.parse(localStorage.getItem(k)) ?? null; } catch { return null; } };
  const writeKey = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };

  /* FNV-1a over the payload. Not security — a paste that lost its tail should be caught before
     it is merged, and a 32-bit check is plenty for that. */
  function sum(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
    return h.toString(36);
  }

  const b64 = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const unb64 = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));

  async function deflate(str) {
    if (typeof CompressionStream !== 'function') return null;
    const cs = new CompressionStream('deflate-raw');
    const w = cs.writable.getWriter();
    w.write(new TextEncoder().encode(str)); w.close();
    return new Uint8Array(await new Response(cs.readable).arrayBuffer());
  }
  async function inflate(bytes) {
    const ds = new DecompressionStream('deflate-raw');
    const w = ds.writable.getWriter();
    w.write(bytes); w.close();
    return new TextDecoder().decode(await new Response(ds.readable).arrayBuffer());
  }

  function snapshot() {
    const data = {};
    for (const k of KEYS) { const v = readKey(k); if (v !== null) data[k] = v; }
    return { v: VERSION, at: new Date().toISOString().slice(0, 19) + 'Z', d: data };
  }

  async function exportCode() {
    const body = JSON.stringify(snapshot());
    const packed = await deflate(body);
    /* z = compressed, j = plain JSON where the browser has no CompressionStream. The reader
       must not care which it was handed. */
    return packed ? `RTT1z.${sum(body)}.${b64(packed)}`
                  : `RTT1j.${sum(body)}.${b64(new TextEncoder().encode(body))}`;
  }

  async function parse(code) {
    const m = /^RTT1([zj])\.([0-9a-z]+)\.([A-Za-z0-9\-_]+)$/.exec((code || '').trim());
    if (!m) throw new Error('That does not look like a sync code.');
    let bytes, body;
    try { bytes = unb64(m[3]); } catch { throw new Error('The code is damaged — copy all of it.'); }
    try {
      body = m[1] === 'z' ? await inflate(bytes) : new TextDecoder().decode(bytes);
    } catch {
      /* A truncated code fails in the decompressor before the checksum can report it, and the
         browser's message for that is "Failed to fetch" — which says nothing about what went
         wrong or what to do. Long codes get mangled by chat apps and mail clients; this is the
         likely failure, so it must name itself. */
      throw new Error('The code is incomplete — it was cut off. Copy the whole thing, or use the file.');
    }
    if (sum(body) !== m[2]) throw new Error('The code is damaged or incomplete — copy all of it.');
    const parsed = JSON.parse(body);
    if (parsed.v !== VERSION) throw new Error(`That code is version ${parsed.v}; this reader speaks ${VERSION}.`);
    return parsed;
  }

  /* Which of two marks to keep. Newer date wins; a tie keeps the further-along one. */
  const RANK = { '1': 1, '2': 2, '3': 3, '4': 4, k: 5, x: 5 };
  function pick(mine, theirs) {
    if (!mine) return theirs;
    if (!theirs) return mine;
    const [ml, md] = mine, [tl, td] = theirs;
    if (md !== td) return md > td ? mine : theirs;
    return (RANK[tl] || 0) > (RANK[ml] || 0) ? theirs : mine;
  }

  /* Count what a merge would do, without doing it. An import is the one action here that can
     surprise you, so it says what it will change before it changes it. */
  function plan(incoming) {
    const mine = readKey('rtt.msLevel') || {};
    const theirs = (incoming.d && incoming.d['rtt.msLevel']) || {};
    let added = 0, advanced = 0, kept = 0;
    for (const g of Object.keys(theirs)) {
      if (!mine[g]) { added++; continue; }
      if (pick(mine[g], theirs[g]) === theirs[g] && theirs[g][0] !== mine[g][0]) advanced++;
      else kept++;
    }
    const myMean = readKey('rtt.msMeaning') || {};
    const theirMean = (incoming.d && incoming.d['rtt.msMeaning']) || {};
    const notes = Object.keys(theirMean).filter(g => !myMean[g]).length;
    return { added, advanced, kept, notes, from: incoming.at,
             theirTotal: Object.keys(theirs).length, myTotal: Object.keys(mine).length };
  }

  function merge(incoming) {
    const d = incoming.d || {};

    const mine = readKey('rtt.msLevel') || {};
    const theirs = d['rtt.msLevel'] || {};
    for (const g of Object.keys(theirs)) mine[g] = pick(mine[g], theirs[g]);
    writeKey('rtt.msLevel', mine);

    /* A note you wrote is never thrown away by a sync. Where both sides have one and they
       differ, both are kept — losing a sentence you wrote about a word is worse than a card
       that briefly says two things. */
    const myMean = readKey('rtt.msMeaning') || {};
    for (const [g, t] of Object.entries(d['rtt.msMeaning'] || {})) {
      if (!myMean[g]) myMean[g] = t;
      else if (myMean[g] !== t && !myMean[g].includes(t)) myMean[g] = `${myMean[g]} / ${t}`;
    }
    writeKey('rtt.msMeaning', myMean);

    const myRead = readKey('rtt.msRead') || {};
    Object.assign(myRead, d['rtt.msRead'] || {});
    writeKey('rtt.msRead', myRead);

    /* Per day, the higher figure: both devices were reading, and the day's real total is at
       least the larger of the two. */
    const mySnap = readKey('rtt.msSnap') || {};
    for (const [day, v] of Object.entries(d['rtt.msSnap'] || {})) {
      const cur = mySnap[day];
      if (!cur || (v && v.k > cur.k)) mySnap[day] = v;
    }
    writeKey('rtt.msSnap', mySnap);

    const myAct = readKey('rtt.msAct') || {};
    for (const [day, n] of Object.entries(d['rtt.msAct'] || {})) {
      myAct[day] = Math.max(myAct[day] || 0, n || 0);
    }
    writeKey('rtt.msAct', myAct);

    const goal = d['rtt.msGoal'];
    if (goal && (!readKey('rtt.msGoal') || goal > readKey('rtt.msGoal'))) writeKey('rtt.msGoal', goal);

    /* rtt.known is a mirror of the levels, shared with the deck and the old reader. Rebuilt
       from the merged levels rather than merged on its own, so the two cannot disagree. */
    const known = {};
    for (const [g, v] of Object.entries(mine)) if (v && v[0] === 'k') known[g] = 1;
    writeKey('rtt.known', known);

    return plan(incoming);
  }

  return { exportCode, parse, plan, merge, KEYS };
})();
