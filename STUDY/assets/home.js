/* The dashboard. One question: how far through the course vocabulary am I, and what is next.
 *
 * Deliberately narrow. Everything else the project can do is real and stays reachable, but it
 * is behind a fold, because the plan is Anki plus the reader until the course words run out
 * and a home page that lists eight tools is a home page that makes you choose between them.
 *
 * COURSE WORDS ARE THE ONLY DENOMINATOR HERE.
 * The deck holds 2,103 scheduled words, but 1,563 of those came from frequency lists and old
 * decks and are parked. Measuring progress against the full deck would make a finished course
 * look a quarter done — so every number on this page counts only the 540 words the course
 * itself taught.
 */
(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const nf = n => n.toLocaleString('en-US');

  const F = WORD_DATA.fields;
  const WORDS = WORD_DATA.words.map(r => { const o = {}; F.forEach((k, i) => o[k] = r[i]); return o; });
  const isCourse = w => /\b(lesson|site)\b/.test(w.source || '');
  const COURSE = WORDS.filter(w => w.order && isCourse(w));

  function render() {
    const known = Progress.getKnown();
    const hard = Progress.getHard();
    const configured = Progress.isConfigured();
    const introduced = configured ? Progress.introducedCount() : 0;

    const met = COURSE.filter(w => w.order <= introduced);
    const kn = COURSE.filter(w => known[w.guid]);
    const hd = COURSE.filter(w => hard[w.guid]);
    const pct = COURSE.length ? Math.round(kn.length / COURSE.length * 100) : 0;

    $('#bar').innerHTML =
      `<span class="b-known" style="flex:${kn.length || 0}"></span>` +
      `<span class="b-met" style="flex:${Math.max(met.length - kn.length, 0)}"></span>` +
      `<span class="b-rest" style="flex:${Math.max(COURSE.length - met.length, 0)}"></span>`;

    $('#headline').innerHTML = configured
      ? `<b>${nf(kn.length)}</b> of ${nf(COURSE.length)} course words known · <b>${pct}%</b>`
      : `<b>${nf(COURSE.length)}</b> course words waiting`;

    $('#nums').innerHTML = [
      ['Day', configured ? nf(Progress.dayNumber()) : '—', configured ? dayLabel() : 'no start date'],
      ['Met', nf(met.length), 'seen in Anki'],
      ['Known', nf(kn.length), 'marked by hand'],
      ['Needs work', nf(hd.length), 'flagged'],
      ['Left', nf(COURSE.length - met.length), 'not yet met'],
    ].map(([k, v, s]) => `<div class="num"><span>${k}</span><strong>${v}</strong><i>${s}</i></div>`).join('');

    $('#setup-warn').hidden = configured;

    /* Today's course words, which is the only "do this now" the page offers. */
    const day = Progress.dayNumber();
    const today = configured ? COURSE.filter(w => w.day === day) : [];
    $('#today-wrap').hidden = !configured;
    $('#today-when').textContent = configured ? `day ${day}` : '';
    $('#today').innerHTML = today.length
      ? today.map(w => `<div class="tw${known[w.guid] ? ' k' : ''}">
          <span class="en">${esc(w.english)}</span>
          <span class="rom">${esc(w.roman)}</span>
          <span class="tg">${esc(w.telugu)}</span></div>`).join('')
      : `<p class="empty">No course words scheduled for today — the day's fifteen are further
         down the deck. <a href="STUDY/words.html">See the queue</a>.</p>`;

    renderLessons(known, introduced);
  }

  function dayLabel() {
    const d = Progress.dateOfDay(Progress.dayNumber());
    return d ? d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }) : '';
  }

  /* Each lesson with how much of its vocabulary is known — so the list doubles as the progress
     report rather than being a plain set of links. */
  function renderLessons(known, introduced) {
    const byLesson = new Map();
    COURSE.forEach(w => {
      if (!w.lesson) return;
      const e = byLesson.get(w.lesson) || { total: 0, known: 0, met: 0 };
      e.total++;
      if (known[w.guid]) e.known++;
      if (w.order <= introduced) e.met++;
      byLesson.set(w.lesson, e);
    });

    $('#lessons').innerHTML = LESSON_DATA.map(([num, title, file, count]) => {
      const st = byLesson.get(num) || { total: count, known: 0, met: 0 };
      const p = st.total ? Math.round(st.known / st.total * 100) : 0;
      return `<a class="lrow" href="LEARNING_GUIDE/lessons/${esc(file)}">
        <span class="lnum">${esc(num)}</span>
        <span class="ltitle">${esc(title)}</span>
        <span class="lbar"><i style="width:${p}%"></i></span>
        <span class="lnums">${st.total ? `${st.known}/${st.total}` : '—'}</span></a>`;
    }).join('');
  }

  Progress.onChange(render);
  render();
})();
