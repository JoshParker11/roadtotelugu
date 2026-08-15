/* Telugu root verbs — stem inventory.
 *
 * Source of the 35 roots: English-Telugu-+RootVerbs.pdf (bhashafy.com), read from the
 * rendered pages because the PDF's text layer mangles the Telugu.
 *
 * WHY STEMS AND NOT FORMS
 * Telugu person endings are regular; what varies verb to verb is a small set of stems.
 * Storing stems means one correction fixes a whole paradigm, and a native speaker reviews
 * ~10 items per verb instead of ~40. engine.js turns these into the full paradigm.
 *
 * FIELDS  (each is [romanized, telugu-script])
 *   root   the dictionary / familiar-imperative form, exactly as the PDF gives it
 *   np     non-past stem, before the t/ṭ marker      chēs- → chēs·t·ānu
 *   T      the tense marker this verb takes: t or ṭ  (ṭ after nasal stems)
 *   pst    past stem, takes vowel-initial endings    chēs- → chēs·ānu
 *   neg    negative + prohibitive stem               chēya- → chēya·nu, chēya·ku
 *   a      short-a stem: polite imperative, "can"    chēya- → chēya·ṇḍi
 *   inf    long-ā infinitive: "must"                 chēyā- → chēyā·li
 *   hort   hortative "let's ___", irregular enough to store whole; null = not natural
 *   pre    optional invariant first word (compound verbs)
 *   ov     per-cell overrides where the pattern genuinely breaks
 *
 * conf: 'high'  = the pattern is regular and I'm confident
 *       'check' = irregular, or a form I'd want confirmed before drilling it
 * Nothing here has been checked by a native speaker yet. See review.html.
 */

const VERBS = [
  { id:'cheyi', en:{base:'do', ing:'doing', past:'did', s:'does'}, gloss:'do, make',
    root:['chēyi','చేయి'], cls:'s-stem', conf:'high',
    np:['chēs','చేస్'], T:['t','త'], pst:['chēs','చేస'],
    neg:['chēya','చేయ'], a:['chēya','చేయ'], inf:['chēyā','చేయా'],
    hort:['chēddāṁ','చేద్దాం'],
    note:'The workhorse verb. Any English verb can be pressed into Telugu with it — “drive chēstānu”, “call chēstānu”. Learn this paradigm first; several others copy its shape.' },

  { id:'ra', en:{base:'come', ing:'coming', past:'came'}, gloss:'come',
    root:['rā','రా'], cls:'irregular', conf:'high',
    np:['vas','వస్'], T:['t','త'], pst:['vachch','వచ్చ'],
    neg:['rā','రా'], a:['rāva','రావ'], inf:['rāvā','రావా'],
    hort:null,
    ov:{ impPol:['raṇḍi','రండి'], can:['rāgalanu','రాగలను'] },
    note:'Suppletive: the non-past and past stems (vas-, vachch-) look nothing like the root rā. rādu “doesn’t/won’t come” is the one in “Telugu rādu.” The polite imperative is raṇḍi, not *rāvaṇḍi.' },

  { id:'kurcho', en:{base:'sit', ing:'sitting', past:'sat'}, gloss:'sit, sit down',
    root:['kūrchō','కూర్చో'], cls:'-ko reflexive', conf:'high',
    np:['kūrchun','కూర్చుం'], T:['ṭ','ట'], pst:['kūrchunn','కూర్చున్న'],
    neg:['kūrchō','కూర్చో'], a:['kūrchō','కూర్చో'], inf:['kūrchōvā','కూర్చోవా'],
    hort:['kūrchundāṁ','కూర్చుందాం'] },

  { id:'tinu', en:{base:'eat', ing:'eating', past:'ate'}, gloss:'eat',
    root:['tinu','తిను'], cls:'n-stem', conf:'high',
    np:['tin','తిం'], T:['ṭ','ట'], pst:['tinn','తిన్న'],
    neg:['tina','తిన'], a:['tina','తిన'], inf:['tinā','తినా'],
    hort:['tindāṁ','తిందాం'],
    note:'tinalēdu “haven’t eaten” already appears in your scenario deck. tinnārā? “have you eaten?” is the greeting you will hear most often.' },

  { id:'tagu', en:{base:'drink', ing:'drinking', past:'drank'}, gloss:'drink',
    root:['tāgu','తాగు'], cls:'u-stem', conf:'high',
    np:['tāgu','తాగు'], T:['t','త'], pst:['tāg','తాగ'],
    neg:['tāga','తాగ'], a:['tāga','తాగ'], inf:['tāgā','తాగా'],
    hort:['tāgudāṁ','తాగుదాం'] },

  { id:'vellu', en:{base:'go', ing:'going', past:'went', s:'goes'}, gloss:'go',
    root:['veḷḷu','వెళ్ళు'], cls:'irregular', conf:'high',
    np:['veḷ','వెళ్'], T:['t','త'], pst:['veḷḷ','వెళ్ళ'],
    neg:['veḷḷa','వెళ్ళ'], a:['veḷḷa','వెళ్ళ'], inf:['veḷḷā','వెళ్ళా'],
    hort:['veḷdāṁ','వెళ్దాం'],
    note:'The PDF also gives pō పో. Both are current; veḷḷu is the safer default and pō turns up in fixed expressions (pōdāṁ “let’s go”, pōnī “let it be”).' },

  { id:'paduko', en:{base:'sleep', ing:'sleeping', past:'slept'}, gloss:'sleep, lie down',
    root:['paḍukō','పడుకో'], cls:'-ko reflexive', conf:'high',
    np:['paḍukun','పడుకుం'], T:['ṭ','ట'], pst:['paḍukunn','పడుకున్న'],
    neg:['paḍukō','పడుకో'], a:['paḍukō','పడుకో'], inf:['paḍukōvā','పడుకోవా'],
    hort:['paḍukundāṁ','పడుకుందాం'] },

  { id:'nerpinchu', en:{base:'teach', ing:'teaching', past:'taught', s:'teaches'}, gloss:'teach',
    root:['nērpinchu','నేర్పించు'], cls:'-inchu causative', conf:'high',
    np:['nērpis','నేర్పిస్'], T:['t','త'], pst:['nērpinch','నేర్పించ'],
    neg:['nērpincha','నేర్పించ'], a:['nērpincha','నేర్పించ'], inf:['nērpinchā','నేర్పించా'],
    hort:['nērpiddāṁ','నేర్పిద్దాం'],
    note:'-inchu verbs all drop to -is- in the non-past: nērpinchu → nērpistānu. Same shape as vāyinchu and prēminchu.' },

  { id:'nerchuko', en:{base:'learn', ing:'learning', past:'learnt'}, gloss:'learn',
    root:['nērchukō','నేర్చుకో'], cls:'-ko reflexive', conf:'high',
    np:['nērchukun','నేర్చుకుం'], T:['ṭ','ట'], pst:['nērchukunn','నేర్చుకున్న'],
    neg:['nērchukō','నేర్చుకో'], a:['nērchukō','నేర్చుకో'], inf:['nērchukōvā','నేర్చుకోవా'],
    hort:['nērchukundāṁ','నేర్చుకుందాం'],
    note:'nērpinchu is teaching someone else; nērchukō is the -ko reflexive, learning for yourself. The pair is the clearest illustration of what -ko does.' },

  { id:'chaduvuko', en:{base:'study', ing:'studying', past:'studied', s:'studies'}, gloss:'study',
    root:['chaduvukō','చదువుకో'], cls:'-ko reflexive', conf:'high',
    np:['chaduvukun','చదువుకుం'], T:['ṭ','ట'], pst:['chaduvukunn','చదువుకున్న'],
    neg:['chaduvukō','చదువుకో'], a:['chaduvukō','చదువుకో'], inf:['chaduvukōvā','చదువుకోవా'],
    hort:['chaduvukundāṁ','చదువుకుందాం'] },

  { id:'chaduvu', en:{base:'read', ing:'reading', past:'read'}, gloss:'read',
    root:['chaduvu','చదువు'], cls:'three-stem', conf:'high',
    np:['chaduvu','చదువు'], T:['t','త'], pst:['chadiv','చదివ'],
    neg:['chadava','చదవ'], a:['chadava','చదవ'], inf:['chadavā','చదవా'],
    hort:['chaduvudāṁ','చదువుదాం'],
    note:'The three-stem pattern in its clearest form: chaduvu / chadiv- / chadav-. The vowel shifts u → i in the past and u → a in the negative. naḍavu, naḍupu and eguru do the same thing.' },

  { id:'rayi', en:{base:'write', ing:'writing', past:'wrote'}, gloss:'write',
    root:['rāyi','రాయి'], cls:'s-stem', conf:'high',
    np:['rās','రాస్'], T:['t','త'], pst:['rās','రాస'],
    neg:['rāya','రాయ'], a:['rāya','రాయ'], inf:['rāyā','రాయా'],
    hort:['rāddāṁ','రాద్దాం'],
    note:'The PDF gives the formal spelling vrāyi వ్రాయి. Say and write rāyi. Identical in shape to chēyi.' },

  { id:'matladu', en:{base:'speak', ing:'speaking', past:'spoke'}, gloss:'speak, talk',
    root:['māṭlāḍu','మాట్లాడు'], cls:'u-stem', conf:'high',
    np:['māṭlāḍu','మాట్లాడు'], T:['t','త'], pst:['māṭlāḍ','మాట్లాడ'],
    neg:['māṭlāḍa','మాట్లాడ'], a:['māṭlāḍa','మాట్లాడ'], inf:['māṭlāḍā','మాట్లాడా'],
    hort:['māṭlāḍadāṁ','మాట్లాడదాం'],
    note:'Telugu māṭlāḍatānu “I speak Telugu” — the sentence that will do you the most social work of anything on this page.' },

  { id:'cheppu', en:{base:'tell', ing:'telling', past:'told'}, gloss:'tell',
    root:['cheppu','చెప్పు'], cls:'u-stem', conf:'high',
    np:['chep','చెప్'], T:['t','త'], pst:['chepp','చెప్ప'],
    neg:['cheppa','చెప్ప'], a:['cheppa','చెప్ప'], inf:['cheppā','చెప్పా'],
    hort:['chepdāṁ','చెప్దాం'],
    note:'Non-past cheptānu is the colloquial form; textbooks and coastal speech use chebutānu చెబుతాను. Both are understood everywhere.' },

  { id:'anu', en:{base:'say', ing:'saying', past:'said'}, gloss:'say',
    root:['anu','అను'], cls:'n-stem', conf:'high',
    np:['an','అం'], T:['ṭ','ట'], pst:['ann','అన్న'],
    neg:['ana','అన'], a:['ana','అన'], inf:['anā','అనా'],
    hort:['andāṁ','అందాం'],
    note:'anṭānu also does the job of English “I mean / I’d say”, and anṭē is how you ask what something means: “X anṭē ēmiṭi?”' },

  { id:'tisuko', en:{base:'take', ing:'taking', past:'took'}, gloss:'take',
    root:['tīsukō','తీసుకో'], cls:'-ko reflexive', conf:'high',
    np:['tīsukun','తీసుకుం'], T:['ṭ','ట'], pst:['tīsukunn','తీసుకున్న'],
    neg:['tīsukō','తీసుకో'], a:['tīsukō','తీసుకో'], inf:['tīsukōvā','తీసుకోవా'],
    hort:['tīsukundāṁ','తీసుకుందాం'] },

  { id:'ivvu', en:{base:'give', ing:'giving', past:'gave'}, gloss:'give',
    root:['ivvu','ఇవ్వు'], cls:'irregular', conf:'high',
    np:['is','ఇస్'], T:['t','త'], pst:['ichch','ఇచ్చ'],
    neg:['ivva','ఇవ్వ'], a:['ivva','ఇవ్వ'], inf:['ivvā','ఇవ్వా'],
    hort:['iddāṁ','ఇద్దాం'],
    note:'Three different-looking stems: ivvu / is- / ichch-. ivvaṇḍi “please give” already appears in your oka deep dive.' },

  { id:'chudu', en:{base:'see', ing:'seeing', past:'saw'}, gloss:'see, look, watch',
    root:['chūḍu','చూడు'], cls:'s-stem', conf:'high',
    np:['chūs','చూస్'], T:['t','త'], pst:['chūs','చూస'],
    neg:['chūḍa','చూడ'], a:['chūḍa','చూడ'], inf:['chūḍā','చూడా'],
    hort:['chūddāṁ','చూద్దాం'],
    note:'chūddāṁ “let’s see” is also the all-purpose way to defer a decision, exactly like the English.' },

  { id:'vinu', en:{base:'hear', ing:'hearing', past:'heard'}, gloss:'hear, listen',
    root:['vinu','విను'], cls:'n-stem', conf:'high',
    np:['vin','విం'], T:['ṭ','ట'], pst:['vinn','విన్న'],
    neg:['vina','విన'], a:['vina','విన'], inf:['vinā','వినా'],
    hort:['vindāṁ','విందాం'] },

  { id:'padu', en:{base:'sing', ing:'singing', past:'sang'}, gloss:'sing',
    root:['pāḍu','పాడు'], cls:'u-stem', conf:'high',
    np:['pāḍu','పాడు'], T:['t','త'], pst:['pāḍ','పాడ'],
    neg:['pāḍa','పాడ'], a:['pāḍa','పాడ'], inf:['pāḍā','పాడా'],
    hort:['pāḍudāṁ','పాడుదాం'] },

  { id:'natyam', en:{base:'dance', ing:'dancing', past:'danced'}, gloss:'dance',
    root:['chēyi','చేయి'], cls:'compound with chēyi', conf:'high',
    pre:['nṛtyaṁ ','నృత్యం '],
    np:['chēs','చేస్'], T:['t','త'], pst:['chēs','చేస'],
    neg:['chēya','చేయ'], a:['chēya','చేయ'], inf:['chēyā','చేయా'],
    hort:['chēddāṁ','చేద్దాం'],
    note:'A noun plus chēyi — the noun never changes, only chēyi conjugates. In ordinary Hyderabad speech people mostly say “ḍāns chēstānu”. Learn the mechanism here, not the word nāṭyaṁ.' },

  { id:'nilabadu', en:{base:'stand', ing:'standing', past:'stood'}, gloss:'stand, stand up',
    root:['nilabaḍu','నిలబడు'], cls:'-aḍu intransitive', conf:'high',
    np:['nilabaḍu','నిలబడు'], T:['t','త'], pst:['nilabaḍḍ','నిలబడ్డ'],
    neg:['nilabaḍa','నిలబడ'], a:['nilabaḍa','నిలబడ'], inf:['nilabaḍā','నిలబడా'],
    hort:['nilabaḍadāṁ','నిలబడదాం'],
    note:'The -aḍu intransitives double the ḍ in the past: nilabaḍu → nilabaḍḍānu. Note that māṭlāḍu and pāḍu do not, despite also ending in -ḍu.' },

  { id:'nadavu', en:{base:'walk', ing:'walking', past:'walked'}, gloss:'walk',
    root:['naḍavu','నడవు'], cls:'three-stem', conf:'high',
    np:['naḍus','నడుస్'], T:['t','త'], pst:['naḍich','నడిచ'],
    neg:['naḍava','నడవ'], a:['naḍava','నడవ'], inf:['naḍavā','నడవా'],
    hort:['naḍuddāṁ','నడుద్దాం'] },

  { id:'parugettu', en:{base:'run', ing:'running', past:'ran'}, gloss:'run',
    root:['parugettu','పరుగెత్తు'], cls:'u-stem', conf:'check',
    np:['parugettu','పరుగెత్తు'], T:['t','త'], pst:['parugett','పరుగెత్త'],
    neg:['parugetta','పరుగెత్త'], a:['parugetta','పరుగెత్త'], inf:['parugettā','పరుగెత్తా'],
    hort:null,
    note:'Flagged. The regular non-past parugettutānu is clumsy and speakers commonly use parigeḍatānu పరిగెడతాను instead. Worth settling with a native speaker before drilling.' },

  { id:'adu', en:{base:'play', ing:'playing', past:'played'}, gloss:'play (a game)',
    root:['āḍu','ఆడు'], cls:'u-stem', conf:'high',
    np:['āḍu','ఆడు'], T:['t','త'], pst:['āḍ','ఆడ'],
    neg:['āḍa','ఆడ'], a:['āḍa','ఆడ'], inf:['āḍā','ఆడా'],
    hort:['āḍudāṁ','ఆడుదాం'] },

  { id:'vayinchu', en:{base:'play music', ing:'playing music', past:'played music', s:'plays music'}, gloss:'play an instrument',
    root:['vāyinchu','వాయించు'], cls:'-inchu causative', conf:'high',
    np:['vāyis','వాయిస్'], T:['t','త'], pst:['vāyinch','వాయించ'],
    neg:['vāyincha','వాయించ'], a:['vāyincha','వాయించ'], inf:['vāyinchā','వాయించా'],
    hort:['vāyiddāṁ','వాయిద్దాం'] },

  { id:'preminchu', en:{base:'love', ing:'loving', past:'loved'}, gloss:'love',
    root:['prēminchu','ప్రేమించు'], cls:'-inchu causative', conf:'high',
    np:['prēmis','ప్రేమిస్'], T:['t','త'], pst:['prēminch','ప్రేమించ'],
    neg:['prēmincha','ప్రేమించ'], a:['prēmincha','ప్రేమించ'], inf:['prēminchā','ప్రేమించా'],
    hort:null,
    note:'Romantic love. Liking a thing is a different construction entirely (nāku iṣṭaṁ), so do not reach for prēminchu to say you like the food.' },

  { id:'gentu', en:{base:'jump', ing:'jumping', past:'jumped'}, gloss:'jump',
    root:['gentu','గెంతు'], cls:'u-stem', conf:'high',
    np:['gentu','గెంతు'], T:['t','త'], pst:['gent','గెంత'],
    neg:['genta','గెంత'], a:['genta','గెంత'], inf:['gentā','గెంతా'],
    hort:['gentudāṁ','గెంతుదాం'] },

  { id:'visiru', en:{base:'throw', ing:'throwing', past:'threw'}, gloss:'throw',
    root:['visiru','విసిరు'], cls:'three-stem', conf:'check',
    np:['visuru','విసురు'], T:['t','త'], pst:['visir','విసిర'],
    neg:['visara','విసర'], a:['visara','విసర'], inf:['visarā','విసరా'],
    hort:null,
    note:'Flagged. The three-stem alternation is expected here but everyday speech usually adds the completive: visirēstānu విసిరేస్తాను. Confirm before drilling.' },

  { id:'kottu', en:{base:'hit', ing:'hitting', past:'hit'}, gloss:'hit, strike, knock',
    root:['koṭṭu','కొట్టు'], cls:'irregular', conf:'high',
    np:['koḍa','కొడ'], T:['t','త'], pst:['koṭṭ','కొట్ట'],
    neg:['koṭṭa','కొట్ట'], a:['koṭṭa','కొట్ట'], inf:['koṭṭā','కొట్టా'],
    hort:['koḍadāṁ','కొడదాం'],
    note:'The ṭṭ softens to ḍ in the non-past only: koṭṭu but koḍatānu. Also the verb for knocking on a door and for a clock striking the hour.' },

  { id:'pattuko', en:{base:'hold', ing:'holding', past:'held'}, gloss:'hold, catch, grab',
    root:['paṭṭukō','పట్టుకో'], cls:'-ko reflexive', conf:'high',
    np:['paṭṭukun','పట్టుకుం'], T:['ṭ','ట'], pst:['paṭṭukunn','పట్టుకున్న'],
    neg:['paṭṭukō','పట్టుకో'], a:['paṭṭukō','పట్టుకో'], inf:['paṭṭukōvā','పట్టుకోవా'],
    hort:['paṭṭukundāṁ','పట్టుకుందాం'] },

  { id:'nadupu', en:{base:'drive', ing:'driving', past:'drove'}, gloss:'drive, operate',
    root:['naḍupu','నడుపు'], cls:'three-stem', conf:'check',
    np:['naḍupu','నడుపు'], T:['t','త'], pst:['naḍip','నడిప'],
    neg:['naḍapa','నడప'], a:['naḍapa','నడప'], inf:['naḍapā','నడపా'],
    hort:null,
    note:'Flagged. Literally “cause to walk” — the causative of naḍavu, and it covers running a business as well as driving a car. For a car most Hyderabad speakers just say “ḍraiv chēstānu”.' },

  { id:'eguru', en:{base:'fly', ing:'flying', past:'flew', s:'flies'}, gloss:'fly',
    root:['eguru','ఎగురు'], cls:'three-stem', conf:'check',
    np:['eguru','ఎగురు'], T:['t','త'], pst:['egir','ఎగిర'],
    neg:['egara','ఎగర'], a:['egara','ఎగర'], inf:['egarā','ఎగరా'],
    hort:null,
    note:'Flagged. This is a bird or a kite flying. Travelling by plane is “flight-lō veḷtānu”.' },

  { id:'agu', en:{base:'stop', ing:'stopping', past:'stopped'}, gloss:'stop, wait, halt',
    root:['āgu','ఆగు'], cls:'u-stem', conf:'high',
    np:['āgu','ఆగు'], T:['t','త'], pst:['āg','ఆగ'],
    neg:['āga','ఆగ'], a:['āga','ఆగ'], inf:['āgā','ఆగా'],
    hort:['āgudāṁ','ఆగుదాం'],
    note:'āgaṇḍi “please wait / hold on” is already in your sentence deck, from the oka deep dive.' },

  { id:'undu', en:{base:'wait', ing:'waiting', past:'waited', s:'waits'}, gloss:'be, exist, stay, wait',
    root:['uṇḍu','ఉండు'], cls:'irregular', conf:'high',
    np:['un','ఉం'], T:['ṭ','ట'], pst:['unn','ఉన్న'],
    neg:['uṇḍa','ఉండ'], a:['uṇḍa','ఉండ'], inf:['uṇḍā','ఉండా'],
    hort:['undāṁ','ఉందాం'],
    /* lēdu is not one word here. The conjugation PDF and course video 22 both give it person
       markers — "nēnu lēnu, nuvvu lēvu, vāḍu lēḍu, mēmu lēmu, mīru lēru" — and these are
       high-frequency: lēru "they aren't in / aren't available" is what you hear on the phone.
       Every other verb's negative past is genuinely invariant, so this is stored as a
       six-cell override rather than by changing the paradigm. */
    ov:{ negPast:[['lēnu','లేను'], ['lēvu','లేవు'], ['lēḍu','లేడు'],
                  ['lēdu','లేదు'], ['lēmu','లేము'], ['lēru','లేరు']] },
    /* Lesson 12 / course video 23. This verb's tense labels do not mean what they say, and it
       is too important to leave mislabelled. The row the engine calls `past` is the ordinary
       present copula — nēnu santōṣangā unnānu "I am happy", right now — and the row it calls
       `future` is the general-fact present: Hyderabad vēḍigā uṇṭundi "Hyderabad is hot (as a
       rule)". Telugu splits "is" into observation vs property, and those two rows are the
       split. The forms are right; only the labels were wrong. */
    cueOv:{ past:    '§subj §be ___  (right now — an observation)',
            future:  '§subj §be ___  (in general — a standing fact)',
            present: '§subj §be staying / living ___',
            /* Without this the generic cue reads "did not wait", which lēnu/lēdu/lēru
               emphatically do not mean — they are the negative of the present copula, the
               "aren't in / aren't available" of the ov note directly above. Same reason the
               other three are overridden: the forms are right, the labels lie. */
            negPast: '§subj §be not  (not there / not available)' },
    note:'The most important verb here, and its tense labels lie. “Past” unnānu is the everyday present “I am”; “habitual/future” uṇṭundi is the general-fact present. Telugu splits English “is” into an observation now (undi) and a permanent property (uṇṭundi) — Taj Mahal andangā undi vs andangā uṇṭundi. Both rows are cells in this table; read the cues, not the column headings. Negative past is simply lēdu, not *uṇḍalēdu.' },
  /* ---- Added from the course's extended verb list (lesson 15). ------------------------
     Stems are derived from the class patterns established above, not from a source that
     lists them, so anything whose past stem is not predictable from its class carries
     conf:'check'. review.html is where those get confirmed. */

  { id:'navvu', en:{base:'laugh', ing:'laughing', past:'laughed'}, gloss:'laugh',
    root:['navvu','నవ్వు'], cls:'u-stem', conf:'high',
    np:['navvu','నవ్వు'], T:['t','త'], pst:['navv','నవ్వ'],
    neg:['navva','నవ్వ'], a:['navva','నవ్వ'], inf:['navvā','నవ్వా'],
    hort:['navvudāṁ','నవ్వుదాం'],
    note:'Also the noun for a laugh or a smile.' },

  { id:'tavvu', en:{base:'dig', ing:'digging', past:'dug'}, gloss:'dig',
    root:['tavvu','తవ్వు'], cls:'u-stem', conf:'high',
    np:['tavvu','తవ్వు'], T:['t','త'], pst:['tavv','తవ్వ'],
    neg:['tavva','తవ్వ'], a:['tavva','తవ్వ'], inf:['tavvā','తవ్వా'],
    hort:['tavvudāṁ','తవ్వుదాం'] },

  { id:'idu', en:{base:'swim', ing:'swimming', past:'swam'}, gloss:'swim',
    root:['īdu','ఈదు'], cls:'u-stem', conf:'high',
    np:['īdu','ఈదు'], T:['t','త'], pst:['īd','ఈద'],
    neg:['īda','ఈద'], a:['īda','ఈద'], inf:['īdā','ఈదా'],
    hort:['īdudāṁ','ఈదుదాం'] },

  { id:'vadu', en:{base:'use', ing:'using', past:'used'}, gloss:'use',
    root:['vāḍu','వాడు'], cls:'u-stem', conf:'high',
    np:['vāḍu','వాడు'], T:['t','త'], pst:['vāḍ','వాడ'],
    neg:['vāḍa','వాడ'], a:['vāḍa','వాడ'], inf:['vāḍā','వాడా'],
    hort:['vāḍudāṁ','వాడుదాం'],
    note:'Spelled and pronounced exactly like vāḍu “he”. Only position separates them: a pronoun opens the sentence, a verb closes it. nēnu vāḍutānu “I will use it” vs vāḍu chēstāḍu “he will do it”.' },

  { id:'padufall', en:{base:'fall', ing:'falling', past:'fell'}, gloss:'fall, drop',
    root:['paḍu','పడు'], cls:'-aḍu intransitive', conf:'high',
    np:['paḍu','పడు'], T:['t','త'], pst:['paḍḍ','పడ్డ'],
    neg:['paḍa','పడ'], a:['paḍa','పడ'], inf:['paḍā','పడా'],
    hort:null,
    note:'Minimal pair with pāḍu “sing”, already in this list — paḍānu “I fell” vs pāḍānu “I sang”, one vowel apart. Doubles the ḍ in the past like nilabaḍu. Also the verb for rain: varṣaṁ paḍutōndi.' },

  { id:'tirugu', en:{base:'roam', ing:'roaming', past:'roamed'}, gloss:'roam, wander, turn',
    root:['tirugu','తిరుగు'], cls:'three-stem', conf:'high',
    np:['tirugu','తిరుగు'], T:['t','త'], pst:['tirig','తిరిగ'],
    neg:['tiraga','తిరగ'], a:['tiraga','తిరగ'], inf:['tiragā','తిరగా'],
    hort:['tirugudāṁ','తిరుగుదాం'],
    note:'The same u/i/a three-stem shape as chaduvu. Covers wandering about, going around, and a wheel turning.' },

  { id:'kadugu', en:{base:'wash', ing:'washing', past:'washed'}, gloss:'wash',
    root:['kaḍugu','కడుగు'], cls:'three-stem', conf:'high',
    np:['kaḍugu','కడుగు'], T:['t','త'], pst:['kaḍig','కడిగ'],
    neg:['kaḍaga','కడగ'], a:['kaḍaga','కడగ'], inf:['kaḍagā','కడగా'],
    hort:['kaḍugudāṁ','కడుగుదాం'] },

  { id:'eduvu', en:{base:'cry', ing:'crying', past:'cried'}, gloss:'cry, weep',
    root:['ēḍuvu','ఏడువు'], cls:'three-stem', conf:'check',
    np:['ēḍus','ఏడుస్'], T:['t','త'], pst:['ēḍch','ఏడ్చ'],
    neg:['ēḍava','ఏడవ'], a:['ēḍava','ఏడవ'], inf:['ēḍavā','ఏడవా'],
    hort:null,
    note:'Flagged. Three stems that share little: ēḍus- / ēḍch- / ēḍava-. ēḍustunnāḍu and ēḍchāḍu are both common; confirm the rest.' },

  { id:'aruvu', en:{base:'scream', ing:'screaming', past:'screamed'}, gloss:'scream, shout',
    root:['aruvu','అరువు'], cls:'three-stem', conf:'check',
    np:['aruvu','అరువు'], T:['t','త'], pst:['arich','అరిచ'],
    neg:['arava','అరవ'], a:['arava','అరవ'], inf:['aravā','అరవా'],
    hort:null,
    note:'Flagged. The past arichānu is certain; the non-past is also heard as arustānu.' },

  { id:'nettu', en:{base:'push', ing:'pushing', past:'pushed'}, gloss:'push',
    root:['neṭṭu','నెట్టు'], cls:'irregular', conf:'check',
    np:['neḍa','నెడ'], T:['t','త'], pst:['neṭṭ','నెట్ట'],
    neg:['neṭṭa','నెట్ట'], a:['neṭṭa','నెట్ట'], inf:['neṭṭā','నెట్టా'],
    hort:['neḍadāṁ','నెడదాం'],
    note:'Flagged. Assumed to soften ṭṭ → ḍ in the non-past like koṭṭu, giving neḍatānu; neṭṭutānu is also heard.' },

  { id:'kalchu', en:{base:'burn', ing:'burning', past:'burnt'}, gloss:'burn, set alight',
    root:['kālchu','కాల్చు'], cls:'-chu', conf:'check',
    np:['kālus','కాలుస్'], T:['t','త'], pst:['kālch','కాల్చ'],
    neg:['kālcha','కాల్చ'], a:['kālcha','కాల్చ'], inf:['kālchā','కాల్చా'],
    hort:null,
    note:'Flagged. Transitive — burning something. The intransitive “it is burning” is kālutōndi. Also grilling and roasting food.' },

  { id:'modalettu', en:{base:'start', ing:'starting', past:'started'}, gloss:'start, begin',
    root:['modaleṭṭu','మొదలెట్టు'], cls:'peṭṭu compound', conf:'check',
    np:['modaleḍa','మొదలెడ'], T:['t','త'], pst:['modaleṭṭ','మొదలెట్ట'],
    neg:['modaleṭṭa','మొదలెట్ట'], a:['modaleṭṭa','మొదలెట్ట'], inf:['modaleṭṭā','మొదలెట్టా'],
    hort:['modaleḍadāṁ','మొదలెడదాం'],
    note:'Flagged. Built on peṭṭu “put”, which softens like koṭṭu. modalu is “beginning”, so literally “put a beginning”.' },

  { id:'lekkapettu', en:{base:'count', ing:'counting', past:'counted'}, gloss:'count',
    root:['lekkapeṭṭu','లెక్కపెట్టు'], cls:'peṭṭu compound', conf:'check',
    np:['lekkapeḍa','లెక్కపెడ'], T:['t','త'], pst:['lekkapeṭṭ','లెక్కపెట్ట'],
    neg:['lekkapeṭṭa','లెక్కపెట్ట'], a:['lekkapeṭṭa','లెక్కపెట్ట'], inf:['lekkapeṭṭā','లెక్కపెట్టా'],
    hort:['lekkapeḍadāṁ','లెక్కపెడదాం'],
    note:'Flagged, same peṭṭu shape as modaleṭṭu. lekka is “a count”, so literally “put a count”.' },

  { id:'tinipinchu', en:{base:'feed', ing:'feeding', past:'fed'}, gloss:'feed (someone)',
    root:['tinipinchu','తినిపించు'], cls:'-inchu causative', conf:'high',
    np:['tinipis','తినిపిస్'], T:['t','త'], pst:['tinipinch','తినిపించ'],
    neg:['tinipincha','తినిపించ'], a:['tinipincha','తినిపించ'], inf:['tinipinchā','తినిపించా'],
    hort:['tinipiddāṁ','తినిపిద్దాం'],
    note:'The causative of tinu “eat” — literally “cause to eat”. tinu and tinipinchu side by side are the clearest example of -inchu in the whole list: what you do versus what you make someone else do.' },

  { id:'vivarinchu', en:{base:'explain', ing:'explaining', past:'explained'}, gloss:'explain',
    root:['vivarinchu','వివరించు'], cls:'-inchu causative', conf:'high',
    np:['vivaris','వివరిస్'], T:['t','త'], pst:['vivarinch','వివరించ'],
    neg:['vivarincha','వివరించ'], a:['vivarincha','వివరించ'], inf:['vivarinchā','వివరించా'],
    hort:['vivariddāṁ','వివరిద్దాం'] },

  { id:'alochinchu', en:{base:'think', ing:'thinking', past:'thought'}, gloss:'think, consider',
    root:['ālōchinchu','ఆలోచించు'], cls:'-inchu causative', conf:'high',
    np:['ālōchis','ఆలోచిస్'], T:['t','త'], pst:['ālōchinch','ఆలోచించ'],
    neg:['ālōchincha','ఆలోచించ'], a:['ālōchincha','ఆలోచించ'], inf:['ālōchinchā','ఆలోచించా'],
    hort:['ālōchiddāṁ','ఆలోచిద్దాం'],
    note:'Thinking as in pondering or considering. “I think that…” as an opinion is anukuṇṭānu, a different verb.' },

  { id:'ajnapinchu', en:{base:'command', ing:'commanding', past:'commanded'}, gloss:'command, order',
    root:['ājñāpinchu','ఆజ్ఞాపించు'], cls:'-inchu causative', conf:'high',
    np:['ājñāpis','ఆజ్ఞాపిస్'], T:['t','త'], pst:['ājñāpinch','ఆజ్ఞాపించ'],
    neg:['ājñāpincha','ఆజ్ఞాపించ'], a:['ājñāpincha','ఆజ్ఞాపించ'], inf:['ājñāpinchā','ఆజ్ఞాపించా'],
    hort:null,
    note:'Formal and Sanskritic — courtrooms and scripture, not kitchens. For everyday “tell someone to do something”, use cheppu.' },

  { id:'vasanachudu', en:{base:'smell', ing:'smelling', past:'smelt'}, gloss:'smell (something)',
    root:['chūḍu','చూడు'], cls:'compound with chūḍu', conf:'high',
    pre:['vāsana ','వాసన '],
    np:['chūs','చూస్'], T:['t','త'], pst:['chūs','చూస'],
    neg:['chūḍa','చూడ'], a:['chūḍa','చూడ'], inf:['chūḍā','చూడా'],
    hort:['chūddāṁ','చూద్దాం'],
    note:'Literally “look at the smell”. chūḍu is doing the work of “perceive” here rather than “see”.' },

  { id:'arthamchesuko', en:{base:'understand', ing:'understanding', past:'understood'},
    gloss:'understand',
    root:['chēsukō','చేసుకో'], cls:'compound, -kō reflexive', conf:'high',
    pre:['arthaṁ ','అర్థం '],
    np:['chēsukun','చేసుకుం'], T:['ṭ','ట'], pst:['chēsukunn','చేసుకున్న'],
    neg:['chēsukō','చేసుకో'], a:['chēsukō','చేసుకో'], inf:['chēsukōvā','చేసుకోవా'],
    hort:null,
    note:'Literally “make meaning for oneself” — arthaṁ is “meaning”, and -kō marks it as done for yourself. The everyday negative is the fixed phrase nāku arthaṁ kālēdu “I didn’t understand”, which uses a different verb again. Learn that one whole.' }
];


if (typeof module !== 'undefined') module.exports = { VERBS };
