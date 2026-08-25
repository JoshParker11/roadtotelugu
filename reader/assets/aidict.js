/* The AI dictionary — LingQ's "Lexa" pattern, opt-in and per-word.
 *
 * WHY LIVE CALLS, WHEN THE REST OF THE SITE IS BAKED
 * The precompute-everything plan (BRIEF §8) still stands for anything shipped at scale. But a
 * contextual explanation is per-(word, sentence), a word recurs across dozens of sentences,
 * and precomputing every pair costs real money before knowing which ones will ever be read.
 * So this is the opposite trade, made explicit: nothing is generated until a specific word in
 * a specific sentence is asked about, and every answer is cached so it is paid for once.
 *
 * THE KEY IS YOURS AND STAYS HERE
 * This is a static site with no backend, so a live call needs a key in the browser. The key
 * is entered by the user, stored only in this browser's localStorage, and sent only to
 * api.anthropic.com. It is never committed, never proxied, never sent anywhere else. That is
 * an acceptable shape *only* because this is a single-user personal tool — the UI says so
 * rather than assuming it.
 *
 * Answers are model output, not checked translation. Nothing here goes through check_ms.py,
 * so a wrong explanation looks exactly like a right one — the banner on the tab says so.
 */
const AiDict = (() => {
  const KEY = 'rtt.msApiKey';
  const CACHE = 'rtt.msAI';
  const MODEL = 'claude-opus-5';
  const MAXCACHE = 400;

  const getKey = () => { try { return localStorage.getItem(KEY) || ''; } catch { return ''; } };
  const setKey = k => { try { k ? localStorage.setItem(KEY, k.trim()) : localStorage.removeItem(KEY); } catch {} };

  /* The shared frame, LingQ-style: one system sentence, tailored to this project's own
     register and terminology decisions instead of LingQ's generic wording. */
  const SYSTEM =
    'You are a dictionary assistant for one adult beginner learning Telugu. The corpus is ' +
    'standard written Telugu (వ్యావహారికం, standard dialect, not Telangana forms). Answer in ' +
    'English. Use the same grammatical vocabulary as a standard Telugu course (case endings ' +
    'like -కి/-లో/-తో, habitual/future vs past vs present continuous, the -ాడు/-ుంది/-ారు ' +
    'person endings). Show Telugu in Telugu script first with an ISO-style romanization in ' +
    'parentheses (ā ī ū ē ō, ṭ ḍ ṇ ḷ, ṣ ś). Be concise and concrete; no preamble.';

  const PROMPTS = {
    explain: (w, ctx, en) =>
      `Explain the word "${w}" as it is used in this sentence:\n\n${ctx}\n(English: ${en})\n\n` +
      'What does it mean here, what is its dictionary form if inflected, and what nuance does it carry? 3–5 sentences.',
    examples: (w, ctx) =>
      `Give three short, natural example sentences using "${w}" (or its dictionary form), at a beginner level, ` +
      `different from this one:\n\n${ctx}\n\nFor each: Telugu script, romanization, English. Keep vocabulary simple.`,
    grammar: (w, ctx, en) =>
      `Break down the morphology of "${w}" in this sentence:\n\n${ctx}\n(English: ${en})\n\n` +
      'Identify the stem and each suffix or ending with its function (case, tense, person). ' +
      'If it is a single unanalyzable word, say so briefly instead of inventing structure.',
  };

  const readCache = () => { try { return JSON.parse(localStorage.getItem(CACHE)) || {}; } catch { return {}; } };
  function writeCache(c) {
    const keys = Object.keys(c);
    if (keys.length > MAXCACHE) {
      keys.sort((a, b) => (c[a].d || '') < (c[b].d || '') ? -1 : 1)
          .slice(0, keys.length - MAXCACHE).forEach(k => delete c[k]);
    }
    try { localStorage.setItem(CACHE, JSON.stringify(c)); } catch {}
  }

  const cacheKey = (tab, g, lineGuid) => `${tab}|${g}|${lineGuid}`;
  const cached = (tab, g, lineGuid) => (readCache()[cacheKey(tab, g, lineGuid)] || {}).t || null;

  async function ask(tab, g, lineGuid, word, ctx, en) {
    const hit = cached(tab, g, lineGuid);
    if (hit) return hit;
    const key = getKey();
    if (!key) throw new Error('no-key');

    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': key,
        'anthropic-version': '2023-06-01',
        'anthropic-beta': 'server-side-fallback-2026-07-01',
        /* Anthropic's CORS opt-in. Deliberate: single-user page, user's own key. */
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1024,
        fallbacks: 'default',
        system: SYSTEM,
        messages: [{ role: 'user', content: PROMPTS[tab](word, ctx, en) }],
      }),
    });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { msg = (await res.json()).error.message || msg; } catch {}
      throw new Error(msg);
    }
    const data = await res.json();
    if (data.stop_reason === 'refusal') {
      throw new Error('The model declined this request' +
        (data.stop_details && data.stop_details.explanation ? `: ${data.stop_details.explanation}` : '.'));
    }
    const text = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n').trim();
    if (!text) throw new Error('Empty response.');
    const c = readCache();
    c[cacheKey(tab, g, lineGuid)] = { t: text, d: new Date().toISOString().slice(0, 10) };
    writeCache(c);
    return text;
  }

  return { hasKey: () => !!getKey(), setKey, ask, cached, MODEL };
})();
