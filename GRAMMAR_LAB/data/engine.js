/* Conjugation engine.
 *
 * Builds the full paradigm from the stems in verbs.js. Person endings are regular across
 * every verb in Telugu, so they live here once; anything genuinely irregular is an `ov`
 * override on the verb.
 *
 * Both scripts are produced by plain concatenation. That works because the stems are stored
 * pre-composed for the ending that follows them: a stem taking a consonant-initial ending
 * carries a virama (చేస్ + తాను), a stem taking a vowel-initial ending does not (చేస + ాను),
 * and the vowel signs are combining characters.
 */

const PERSONS = [
  { id:'i',    pron:['nēnu','నేను'],            en:'I',            enSub:'I' },
  { id:'you',  pron:['nuvvu','నువ్వు'],          en:'you',          enSub:'you', reg:'informal' },
  { id:'he',   pron:['atanu','అతను'],           en:'he',           enSub:'he' },
  { id:'she',  pron:['āme','ఆమె'],              en:'she / it',     enSub:'she' },
  { id:'we',   pron:['manaṁ','మనం'],            en:'we',           enSub:'we' },
  { id:'they', pron:['mīru / vāḷḷu','మీరు / వాళ్ళు'], en:'you (respectful) / they', enSub:'they', reg:'respectful' }
];

/* endings, indexed the same as PERSONS */
const END = {
  //            I          you        he         she/it      we         you-pl/they
  nonPast: [['ānu','ాను'],['āvu','ావు'],['āḍu','ాడు'],['undi','ుంది'],['āṁ','ాం'],['āru','ారు']],
  cont:    [['unnānu','ున్నాను'],['unnāvu','ున్నావు'],['unnāḍu','ున్నాడు'],['ōndi','ోంది'],['unnāṁ','ున్నాం'],['unnāru','ున్నారు']],
  past:    [['ānu','ాను'],['āvu','ావు'],['āḍu','ాడు'],['indi','ింది'],['āṁ','ాం'],['āru','ారు']],
  neg:     [['nu','ను'],['vu','వు'],['ḍu','డు'],['du','దు'],['ṁ','ం'],['ru','రు']]
};

/* The paradigms, in teaching order. `person:true` means six cells; otherwise one. */
const FORMS = [
  { id:'future',  person:true,  label:'Habitual & future',   short:'will ___',
    gloss:'Does the double duty of English “I do” and “I will do”. Telugu draws no line between them.',
    en:p => `${p.enSub} will ${'§'}`, tier:1 },
  { id:'present', person:true,  label:'Present continuous',  short:'am ___ing',
    gloss:'Happening right now. Built on the same stem as the future, with -unnā- in place of -ā-.',
    en:p => `${p.enSub} ${beVerb(p)} ${'§ing'}`, tier:1 },
  { id:'past',    person:true,  label:'Past',                short:'___ed',
    gloss:'The past stem is the one that most often looks nothing like the root. This is the paradigm to over-learn.',
    en:p => `${p.enSub} ${'§past'}`, tier:1 },
  { id:'negFuture', person:true, label:'Negative habitual & future', short:"won't ___",
    gloss:'No helper word. The negative has its own stem and its own set of endings.',
    en:p => `${p.enSub} ${p.id==='he'||p.id==='she'?'does not':'will not'} ${'§'}`, tier:1 },
  /* Person-invariant in Telugu — the pronoun carries person and the verb does not move.
     Still drilled across all six persons on purpose: the commonest learner error is to
     inflect these, so seeing the same answer under six different subjects is the lesson. */
  { id:'negPast', person:true, invariant:true, label:'Negative past', short:"didn't ___",
    gloss:'One form for every person. Telugu marks who did not do it with the pronoun alone — nothing changes on the verb.',
    en:p => `${p.enSub} did not §`, tier:1 },
  /* Added after auditing the course's all-pronouns video, which teaches this alongside the
     positive present continuous. Not a suffix on the verb at all: -ḍaṁ makes a verbal noun
     ("the doing") and lēdu says it is absent. Same -ḍaṁ that the purposive puts in the
     dative, chēyaḍaṁ → chēyaḍāniki. Person-invariant, and dangerously close to the negative
     past: chēyalēdu "didn't do" vs chēyaḍaṁ lēdu "am not doing". */
  { id:'negPresent', person:true, invariant:true, label:'Negative present continuous',
    short:"am not ___ing",
    gloss:'Verbal noun in -ḍaṁ plus lēdu — literally “doing is not”. One form for every person. Do not confuse it with the negative past, which drops the -ḍaṁ.',
    en:p => `${p.enSub} ${beVerb(p)} not ${'§ing'}`, tier:1 },

  /* Video 21. Not really a separate tense: it is pōtunnānu "I am going" fused onto the verb as
     a suffix, with p softening to b. So it is literally the present continuous of "go", and it
     builds on the plain stem — the same one every negative uses — never on the s-stem.
     chēyabōtunnānu, not *chēsabōtunnānu. */
  { id:'immFuture', person:true, label:'Immediate future', short:'about to ___',
    gloss:'“Going to / about to.” The verb pōvu “go” fused on as a suffix, exactly as English uses “going to”. Built on the plain stem, so chēyi stays chēya- here.',
    en:p => `${p.enSub} ${beVerb(p)} about to ${'§'}`, tier:2 },

  { id:'impFam',  person:false, label:'Imperative — familiar', short:'do it!',
    gloss:'The bare root. Only for children, close friends, and people much younger than you. Getting this wrong is a social error, not a grammatical one.',
    en:() => `§ ! (to a close friend or child)`, tier:2, reg:'informal' },
  { id:'impPol',  person:false, label:'Imperative — polite',   short:'please do',
    gloss:'Your default. -ṇḍi is the same respectful ending you already know from raṇḍi and āgaṇḍi.',
    en:() => `please § (to anyone you respect)`, tier:2, reg:'respectful' },
  { id:'prohibFam', person:false, label:'Prohibitive — familiar', short:"don't do it",
    gloss:'Negative stem plus -ku.',
    en:() => `don't § (to a close friend or child)`, tier:2, reg:'informal' },
  { id:'prohibPol', person:false, label:'Prohibitive — polite',   short:"please don't",
    gloss:'Negative stem plus -kaṇḍi.',
    en:() => `please don't § (to anyone you respect)`, tier:2, reg:'respectful' },
  { id:'hort',    person:false, label:"Hortative — let's",   short:"let's ___",
    gloss:'Invites the listener along. Irregular enough that it is stored per verb rather than derived.',
    en:() => `let's §`, tier:2 },
  { id:'must',    person:true, invariant:true, label:'Obligation — must', short:'must ___',
    gloss:'-āli on the long infinitive. Person-invariant, like the negative past: who must do it is carried by the pronoun.',
    en:p => `${p.enSub} must §`, tier:2 },
  /* The modals, from the course's modal-verb video. Only can/cannot inflect for person; the
     other four are the same for every subject, which the video states outright. `cannot` is
     the inflected lēdu again — the same lēnu/lēvu/lēḍu/lēru set that uṇḍu's negative uses. */
  { id:'can',     person:true, label:'Ability — can',       short:'can ___',
    gloss:'-gala on the short-a stem, then the ordinary person endings. chēyagalanu, chēyagalavu, chēyagaladu.',
    en:p => `${p.enSub} can §`, tier:2 },
  { id:'cannot',  person:true, label:'Inability — cannot',  short:"can't ___",
    gloss:'-lē plus the person endings: chēyalēnu, chēyalēvu, chēyalēru. That is lēdu itself taking person markers, exactly as it does for uṇḍu.',
    en:p => `${p.enSub} cannot §`, tier:2 },
  { id:'mustNot', person:true, invariant:true, label:'Prohibition — must not', short:"must not ___",
    gloss:'-kūḍadu on the short-a stem. One form for every person. Stronger than the prohibitive -ku: this is “ought not”, not “don’t”.',
    en:p => `${p.enSub} must not §`, tier:2 },
  { id:'wantTo',  person:true, invariant:true, label:'Desire — want to', short:'want to ___',
    gloss:'The obligation form plus ani undi — literally “it is that [I] should”. Takes a dative subject: nāku chēyālani undi, never nēnu.',
    en:p => `${p.enSub} want${p.id === 'he' || p.id === 'she' ? 's' : ''} to §`, tier:2 },
  { id:'dontWant', person:true, invariant:true, label:'Desire — don’t want to', short:"don't want to ___",
    gloss:'Same frame with lēdu in place of undi. Also a dative subject.',
    en:p => `${p.enSub} ${p.id === 'he' || p.id === 'she' ? 'does' : 'do'} not want to §`, tier:2 },
  { id:'purpose', person:false, label:'Purposive — in order to', short:'to ___',
    gloss:'-ḍāniki, “for the purpose of”. The way to attach a reason to any sentence.',
    en:() => `in order to §`, tier:3 },
  { id:'cond',    person:true, invariant:true, label:'Conditional — if', short:'if ___',
    gloss:'-tē on the non-past stem, person-invariant. Confirmed by the conjunctions lesson: aṇṭē, endukaṇṭē and kāvālaṇṭē are all this form of anu “to say”, which is why the particle turns up everywhere.',
    en:p => `if ${p.enSub} ${p.id === 'he' || p.id === 'she' ? '§s' : '§'}`, tier:3 }
];

function beVerb(p){
  return p.id === 'i' ? 'am' : (p.id === 'he' || p.id === 'she') ? 'is' : 'are';
}

/* strip the long-ā of the infinitive back to a short a, in both scripts */
function shorten(pair){
  return [ pair[0].replace(/ā$/, 'a'), pair[1].replace(/ా$/, '') ];
}
/* Telugu writes the stem-final nasal of tinu, anu, vinu, uṇḍu and every -kō verb as an
   anusvara (తిం), which is pronounced — and by this project's convention romanized — as
   whatever nasal matches the following consonant. Before the retroflex ṭ of the tense
   marker that is ṇ, not n: తింటున్నాను is tiṇṭunnānu. The stems are stored with a plain n
   because the same anusvara surfaces as n before the dental d of the she/it past (తింది,
   tindi), so the choice can only be made once the ending is attached. Matches tools/te2rom.py. */
function assimilate(rom){
  return rom.replace(/n(?=[ṭḍ])/g, 'ṇ');
}
function join(...parts){
  return [ assimilate(parts.map(p => p[0]).join('')), parts.map(p => p[1]).join('') ];
}

/* One cell of the paradigm. personIndex is ignored for person-less forms. */
function conjugate(v, formId, pi){
  const f = FORMS.find(x => x.id === formId);
  const ov = v.ov && v.ov[formId];
  /* Overrides cover whole-form irregularities: any form that does not vary by person. An
     override may also be an array of six pairs, for the one case where a form is invariant
     for every other verb but not for this one — uṇḍu's negative, where lēdu itself takes
     person markers: lēnu, lēvu, lēḍu, lēdu, lēmu, lēru. */
  if (ov && (!f.person || f.invariant)) {
    return withPre(v, Array.isArray(ov[0]) ? ov[pi] : ov);
  }

  const out = (() => {
    switch (formId) {
      case 'future':    return join(v.np, v.T, END.nonPast[pi]);
      case 'present':   return join(v.np, v.T, END.cont[pi]);
      case 'past':      return pastCell(v, pi);
      case 'negFuture': return join(v.neg, END.neg[pi]);
      case 'negPast':   return join(v.neg, ['lēdu','లేదు']);
      case 'negPresent':return join(shorten(v.inf), ['ḍaṁ lēdu','డం లేదు']);
      /* bō always takes the dental t: it ends in a vowel, so v.T's retroflex never applies */
      case 'immFuture': return join(v.neg, ['bō','బో'], ['t','త'], END.cont[pi]);
      case 'impFam':    return v.root;   /* prefix is added by withPre below */
      case 'impPol':    return join(v.a, ['ṇḍi','ండి']);
      case 'prohibFam': return join(v.neg, ['ku','కు']);
      case 'prohibPol': return join(v.neg, ['kaṇḍi','కండి']);
      case 'hort':      return v.hort;
      case 'must':      return join(v.inf, ['li','లి']);
      case 'can':       return join(v.a, ['gala','గల'], END.neg[pi]);
      case 'cannot':    return join(v.a, ['lē','లే'], END.neg[pi]);
      case 'mustNot':   return join(v.a, ['kūḍadu','కూడదు']);
      case 'wantTo':    return join(v.inf, ['lani undi','లని ఉంది']);
      case 'dontWant':  return join(v.inf, ['lani lēdu','లని లేదు']);
      case 'purpose':   return join(shorten(v.inf), ['ḍāniki','డానికి']);
      case 'cond':      return join(v.np, v.T, ['ē','ే']);
      default:          return null;
    }
  })();
  return out ? withPre(v, out) : null;
}

/* Nasal-stem verbs (tinu, anu, vinu, uṇḍu and every -ko verb) build the she/it past on
   the non-past stem instead: tinnānu but tindi, unnānu but undi. */
function pastCell(v, pi){
  if (pi === 3 && v.T[0] === 'ṭ') return join(v.np, ['di','ది']);
  return join(v.pst, END.past[pi]);
}

function withPre(v, pair){
  return v.pre ? join(v.pre, pair) : pair;
}

/* The English cue for a cell, e.g. "she is eating", "please don't come".
 *
 * A verb may override the cue for a form via `cueOv`. This exists for uṇḍu, where the tense
 * labels genuinely do not map: unnānu is the ordinary present copula "I am", not a past, and
 * uṇṭundi is the general-fact present, not a future. Cueing them "I waited" / "it will wait"
 * would drill the wrong meaning into the most-used verb in the language. §subj and §be expand
 * to the pronoun and the right form of "to be". */
function cue(v, formId, pi){
  const f = FORMS.find(x => x.id === formId);
  const p = PERSONS[pi] || PERSONS[0];
  const ov = v.cueOv && v.cueOv[formId];
  if (ov) return ov.replace('§subj', p.enSub).replace('§be', beVerb(p));
  return f.en(p)
    .replace('§ing', v.en.ing)
    .replace('§past', v.en.past)
    .replace('§s', v.en.s || v.en.base + 's')
    .replace('§', v.en.base);
}

/* Every drillable cell of one verb. */
function cells(v, formIds){
  const out = [];
  for (const f of FORMS) {
    if (formIds && !formIds.includes(f.id)) continue;
    if (f.person) {
      PERSONS.forEach((p, i) => {
        const a = conjugate(v, f.id, i);
        if (a) out.push({ verb:v.id, form:f.id, person:i, key:`${v.id}|${f.id}|${i}`,
                          rom:a[0], tel:a[1], cue:cue(v, f.id, i),
                          conf: f.conf === 'check' || v.conf === 'check' ? 'check' : 'high' });
      });
    } else {
      const a = conjugate(v, f.id, 0);
      if (a) out.push({ verb:v.id, form:f.id, person:null, key:`${v.id}|${f.id}|x`,
                        rom:a[0], tel:a[1], cue:cue(v, f.id, 0),
                        conf: f.conf === 'check' || v.conf === 'check' ? 'check' : 'high' });
    }
  }
  return out;
}

/* Split a form into stem + ending so the paradigm tables can colour the morphology. */
function segment(v, formId, pi){
  const full = conjugate(v, formId, pi);
  if (!full) return null;
  const marker = ['future','present','cond'].includes(formId) ? v.T : null;
  let stem = null;
  if (['future','present','cond'].includes(formId)) stem = v.np;
  else if (formId === 'past') stem = (pi === 3 && v.T[0] === 'ṭ') ? v.np : v.pst;
  else if (['negFuture','negPast','prohibFam','prohibPol','immFuture'].includes(formId)) stem = v.neg;
  else if (['impPol','can','cannot','mustNot'].includes(formId)) stem = v.a;
  else if (['must','wantTo','dontWant'].includes(formId)) stem = v.inf;
  else if (['purpose','negPresent'].includes(formId)) stem = shorten(v.inf);
  if (!stem || (v.ov && v.ov[formId])) return { whole: full };
  const pre = v.pre ? v.pre[0] : '';
  const head = pre + stem[0] + (marker ? marker[0] : '');
  const headT = (v.pre ? v.pre[1] : '') + stem[1] + (marker ? marker[1] : '');
  if (!full[0].startsWith(head)) return { whole: full };
  return { stem:[head, headT], end:[full[0].slice(head.length), full[1].slice(headT.length)], full };
}

/* Does this form actually stay still for this verb? FORMS marks the general case; a verb may
   override it with a per-person array. The paradigm tables need this to know whether to print
   "↑ unchanged" or six distinct cells. */
function invariantFor(v, formId){
  const f = FORMS.find(x => x.id === formId);
  if (!f || !f.invariant) return false;
  const ov = v.ov && v.ov[formId];
  return !(ov && Array.isArray(ov[0]));
}

/* Headword as displayed: the compound verbs carry their invariant first word. */
function rootOf(v){ return withPre(v, v.root); }

if (typeof module !== 'undefined') module.exports = { PERSONS, FORMS, conjugate, cells, cue, segment, rootOf, invariantFor };
