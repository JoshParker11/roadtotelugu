# -*- coding: utf-8 -*-
"""Rebuild telugu_words.csv and telugu_sentences.csv from the Foundational Telugu website.

    python3 tools/build_csvs.py

Re-run after processing a new lesson. Rows keep their order (lesson 1 -> 6, scenario, songs),
so appended lessons get new W/S ids at the end. Nothing is written outside anki/.
"""
import re, os, csv, json, html, glob, collections

ROOT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'LEARNING_GUIDE')
ROOT   = os.path.normpath(ROOT)
OUTDIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def clean(x):

    x=re.sub(r'<br\s*/?>',' / ',x)
    x=re.sub(r'<[^>]+>','',x)
    x=html.unescape(x).replace('\xa0',' ')
    return re.sub(r'\s+',' ',x).strip()

def span(block, cls):
    """First <span class=cls> with balanced nesting."""
    m=re.search(r'<span class="%s"[^>]*>'%cls, block)
    if not m: return ''
    i=m.end(); depth=1; j=i
    pat=re.compile(r'<span\b|</span>')
    while depth>0:
        mm=pat.search(block,j)
        if not mm: return clean(block[i:])
        if mm.group(0).startswith('</'): depth-=1
        else: depth+=1
        j=mm.end()
    return clean(block[i:mm.start()])

def blocks(s, opentag, tag='div'):
    """crude balanced-tag extractor"""
    out=[]
    for m in re.finditer(opentag, s):
        i=m.end(); depth=1; j=i
        pat=re.compile(r'<%s\b|</%s>'%(tag,tag))
        while depth>0:
            mm=pat.search(s,j)
            if not mm: break
            if mm.group(0).startswith('</'): depth-=1
            else: depth+=1
            j=mm.end()
        out.append(s[i:mm.start()] if mm else s[i:i+2000])
    return out



def extract_words():
    rows=[]
    for f in sorted(glob.glob(ROOT+'/**/*.html',recursive=True)):
        s=open(f).read()
        for tm in re.finditer(r'<table class="anki">(.*?)</table>', s, re.S):
            body=tm.group(1)
            section=''
            for trm in re.finditer(r'<tr([^>]*)>(.*?)</tr>', body, re.S):
                attrs, tr = trm.group(1), trm.group(2)
                if '<th' in tr: continue
                if 'class="sec"' in attrs or 'colspan' in tr:
                    section=clean(tr); continue
                tds=re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
                if len(tds)<5: 
                    print('SHORT', os.path.relpath(f,ROOT), len(tds), clean(tr)[:80]); continue
                rows.append(dict(page=os.path.relpath(f,ROOT), section=section,
                                 en=clean(tds[0]), rom=clean(tds[1]), tel=clean(tds[2]),
                                 aud=clean(tds[3]), ex=clean(tds[4]), raw_en=tds[0]))

    return rows


def extract_sentences():
    rows=[]
    def add(**kw):
        kw.setdefault('label',''); kw.setdefault('note',''); kw.setdefault('level','')
        rows.append(kw)

    # A. scenario .say
    f='scenarios/how-was-your-day.html'; s=open(ROOT+'/'+f).read()
    for b in blocks(s, r'<div class="say[^"]*">'):
        add(src=f, kind='scenario', level=span(b,'lvl'), tel=span(b,'tel'), rom=span(b,'rom'),
            en=span(b,'en'), note=span(b,'why'))

    # B/C. phrase-row, template-row
    for f,cls,kind in [('lessons/lesson-03-greetings.html','phrase-row','phrase'),
                       ('lessons/lesson-02-introductions.html','template-row','template')]:
        s=open(ROOT+'/'+f).read()
        for b in blocks(s, r'<div class="%s">'%cls):
            lab=re.match(r'\s*<span>(.*?)</span>', b, re.S)
            add(src=f, kind=kind, label=clean(lab.group(1)) if lab else '',
                rom=span(b,'line'), tel=span(b,'tel'), en=span(b,'en'))

    # D. lesson-05 story-line
    f='lessons/lesson-05-possessives.html'; s=open(ROOT+'/'+f).read()
    for b in blocks(s, r'<div class="story-line">'):
        add(src=f, kind='mini-dialogue', tel=span(b,'tg'), rom=span(b,'rm'), en=span(b,'en'))

    # E. story-01
    f='stories/story-01-ravi-and-sita.html'; s=open(ROOT+'/'+f).read()
    for b in blocks(s, r'<article class="story-line">', 'article'):
        num=re.match(r'\s*<span>(\d+)</span>', b)
        mean=re.search(r'<summary>Meaning</summary>\s*<p>(.*?)</p>', b, re.S)
        add(src=f, kind='story', label='line '+(num.group(1) if num else ''),
            tel=span(b,'story-telugu'), rom=span(b,'story-roman'),
            en=clean(mean.group(1)) if mean else '')

    # F. .ex spans
    for f in sorted(glob.glob(ROOT+'/**/*.html', recursive=True)):
        s=open(f).read(); rel=os.path.relpath(f,ROOT)
        for b in blocks(s, r'<span class="ex">', 'span'):
            tel=span(b,'tel'); en=span(b,'en')
            lead=clean(re.sub(r'<span class="(tel|en)".*','',b,flags=re.S))
            add(src=rel, kind='example', rom=lead, tel=tel, en=en)

    # G. self-test .try li
    for f in sorted(glob.glob(ROOT+'/**/*.html', recursive=True)):
        s=open(f).read(); rel=os.path.relpath(f,ROOT)
        for m in re.finditer(r'<li><span class="q">(.*?)</span>\s*<span class="a">(.*?)</span>\s*</li>', s, re.S):
            raw=re.sub(r'<br\s*/?>',' / ',m.group(2))
            raw=html.unescape(re.sub(r'<[^>]+>','',raw))
            # answer and commentary are separated by a non-breaking space in the source
            parts=re.split(r'\u00a0+', raw)
            ans=re.sub(r'\s+',' ',parts[0]).strip()
            note=re.sub(r'\s+',' ',' '.join(parts[1:])).strip()
            if not note:
                mm=re.match(r'^(.*?)\s*(\([^()]*\))\s*$', ans)   # only a trailing parenthetical
                if mm: ans, note = mm.group(1).strip(), mm.group(2).strip()
            add(src=rel, kind='selftest', en=clean(m.group(1)), rom=ans, tel='', note=note)

    # H. prompt/answer
    for f in sorted(glob.glob(ROOT+'/**/*.html', recursive=True)):
        s=open(f).read(); rel=os.path.relpath(f,ROOT)
        for m in re.finditer(r'<span class="prompt">(.*?)</span>\s*<span class="answer">(.*?)</span>', s, re.S):
            a=clean(m.group(2)); note=''
            if ' — ' in a: a, note = a.split(' — ',1)
            add(src=rel, kind='production-prompt', en=clean(m.group(1)), rom=a.strip(), tel='', note=note.strip())

    # I. contrast-side
    for f in sorted(glob.glob(ROOT+'/**/*.html', recursive=True)):
        s=open(f).read(); rel=os.path.relpath(f,ROOT)
        for b in blocks(s, r'<div class="contrast-side">'):
            lab=re.search(r'<span>(.*?)</span>', b, re.S)
            st=re.search(r'<strong>(.*?)</strong>', b, re.S)
            p=re.search(r'<p>(.*?)</p>', b, re.S)
            if not st: continue
            raw=st.group(1)
            tel=span(raw,'telugu')
            rom=clean(re.sub(r'<span class="telugu">.*?</span>','',raw,flags=re.S))
            add(src=rel, kind='contrast', label=clean(lab.group(1)) if lab else '',
                rom=rom, tel=tel, en=clean(p.group(1)) if p else '')


    return rows


# ---- verified romanization -> Telugu script lexicon ----
PUNC='.,?!;:"“”’‌'

def toks(s):
    return [t for t in re.split(r'\s+', s.strip()) if t]
def strip(t): return t.strip(PUNC)

lex=collections.defaultdict(collections.Counter)

def learn(rom, tel):
    if not rom or not tel: return
    if any(c in rom for c in '→·/_()'): return
    r=[strip(x) for x in toks(rom)]; t=[strip(x) for x in toks(tel)]
    if len(r)!=len(t): return
    for a,b in zip(r,t):
        if a and b: lex[a.lower()][b]+=1

rows_w=extract_words()
rows_s=extract_sentences()
for r in rows_w:
    learn(r['rom'], r['tel'])
    learn(r['ex'], '')  # examples have no script
for r in rows_s:
    learn(r['rom'], r['tel'])
# also known-language.json
kl=json.load(open(os.path.join(ROOT,'data','known-language.json')))
for v in kl['vocabulary']+kl['storyIntroductions']:
    learn(v['romanized'], v['telugu'])
# stray inline pairs: <span class="mono">rom</span> ... <span class="telugu">tel</span> too noisy; skip

LAT=re.compile(r'[a-zāīūēōṭḍṇḷṁṣśñṅ]', re.I)
def render(rom):
    """Return (telugu, status)"""
    out=[]; missing=[]
    for t in toks(rom):
        core=strip(t)
        pre=t[:len(t)-len(t.lstrip(PUNC))]; post=t[len(t.rstrip(PUNC)):]
        if not core: out.append(t); continue
        if not LAT.search(core):      # digits/symbols
            out.append(t); continue
        cand=lex.get(core.lower())
        if cand:
            out.append(pre+cand.most_common(1)[0][0]+post)
        else:
            missing.append(core); out.append(pre+core+post)
    return ' '.join(out), missing



# ---- forms not printed in script anywhere on the site ----

SUPPLEMENT = {
 # base attested on site + the -ni "I am" marker (Lesson 2 rule; abbāyi అబ్బాయి → abbāyini అబ్బాయిని attested)
 'vidyārthini':'విద్యార్థిని', 'vidyārthivi':'విద్యార్థివి', 'vidyārthulamu':'విద్యార్థులము',
 'moguḍini':'మొగుడిని', 'āḍadini':'ఆడదిని', 'bhāratīyurālini':'భారతీయురాలిని',
 'alluḍini':'అల్లుడిని', 'manishini':'మనిషిని',
 # colloquial short forms of attested words (manamu మనము, namaskāraṁ నమస్కారం)
 'manam':'మనం', 'namaskāram':'నమస్కారం', 'konchem':'కొంచెం',
 # possessive stems (Lesson 5; vāḷḷu వాళ్ళు → vāḷḷa వాళ్ళ attested)
 'itani':'ఇతని', 'dīni':'దీని', 'vīḷḷa':'వీళ్ళ', 'vāṭi':'వాటి', 'mana':'మన',
 # plurals (Lesson 6 -lu; kāru కారు → kārlu కార్లు attested)
 'pustakālu':'పుస్తకాలు', 'vandalu':'వందలు', 'vēlu':'వేలు', 'pērlu':'పేర్లు',
 # fast-speech contractions taught in Lesson 5
 'pēreṇṭi':'పేరెంటి', 'ēnti':'ఏంటి', 'nēnammāyini':'నేనమ్మాయిని', 'nēnāḍadini':'నేనాడదిని',
 # proper nouns / loanwords
 'tāj':'తాజ్', 'mahal':'మహల్', 'india':'ఇండియా', 'ni':'ని',
}


for _k,_v in SUPPLEMENT.items(): lex[_k][_v]+=1
# the deep-dive pages use a stricter ISO spelling than the lessons; map the variants
# onto the spelling that is already attested in Telugu script elsewhere on the site
for _variant, _attested in {'ṭīcar':'ṭīcharu','maniṣi':'manishi','manci':'manchi'}.items():
    if _attested in lex: lex[_variant]=lex[_attested]


# ---- build ----
W, S = extract_words(), extract_sentences()

PAGE={'lessons/lesson-01-pronouns.html':('lesson-01','Lesson 1 · Pronouns & the missing "to be"'),
 'lessons/lesson-02-introductions.html':('lesson-02','Lesson 2 · Introductions'),
 'lessons/lesson-03-greetings.html':('lesson-03','Lesson 3 · Greetings & courtesy'),
 'lessons/lesson-04-family.html':('lesson-04','Lesson 4 · Family'),
 'lessons/lesson-05-possessives.html':('lesson-05','Lesson 5 · Possessives'),
 'lessons/lesson-06-numbers.html':('lesson-06','Lesson 6 · Numbers'),
 'scenarios/how-was-your-day.html':('scenario-how-was-your-day','Scenario · How was your day?'),
 'songs/gira-gira.html':('song-gira-gira','Song · Gira Gira'),
 'songs/saranga-dariya.html':('song-saranga-dariya','Song · Saranga Dariya'),
 'stories/story-01-ravi-and-sita.html':('story-01','Mini story 01 · Ravi and Sita'),
 'concepts/oka-one-and-a.html':('concept-oka','Deep dive · oka'),
 'concepts/registers-dialects-urdu.html':('concept-registers','Deep dive · registers & dialects')}
ORDER=list(PAGE)

def slug(x): return re.sub(r'[^a-z0-9]+','-',x.lower()).strip('-')

# ---------------- WORDS ----------------
POS_MAP=[('pronoun','pronoun'),('possessive','possessive'),('number','numeral'),('1 to 10','numeral'),
 ('teens','numeral'),('tens','numeral'),('ordinal','numeral'),('counting','numeral'),('large number','numeral'),
 ('verb','verb'),('family','family'),('grandparent','family'),('sibling','family'),('uncle','family'),
 ('aunt','family'),('spouse','family'),('children','family'),('grandchild','family'),('in-law','family'),
 ('profession','profession'),('greeting','phrase'),('courtesy','phrase'),('opening','phrase'),('closing','phrase'),
 ('grammar','grammar'),('body','noun'),('noun','noun'),('object','noun'),('poetic','poetic'),('urdu','urdu')]
def pos_of(section):
    s=section.lower()
    for k,v in POS_MAP:
        if k in s: return v
    return 'other'

kl=json.load(open(os.path.join(ROOT,'data','known-language.json')))
KLCAT={v['romanized'].lower(): v['category'] for v in kl['vocabulary']}

words=[]; seen={}
for page in ORDER:
    for r in W:
        if r['page']!=page: continue
        m=re.search(r'class="use ([a-z]+)"', r['raw_en'])
        use=m.group(1) if m else ''
        en=r['en']
        if use: en=re.sub(re.escape(use)+r'$','',en).strip()
        key=(r['rom'].lower(), en.lower())
        pid, plabel = PAGE[page]
        tier={'daily':'core','limited':'standard','poetic':'recognition','verify':'standard'}.get(use,'')
        if not tier:
            tier='core' if page.startswith('lessons') or page.startswith('scenarios') else 'standard'
        sec=r['section'].lower()
        if 'lower priority' in sec: tier='standard'          # the site's own labels
        if "recognise, don't" in sec or "don't card" in sec: tier='recognition'
        cat=KLCAT.get(r['rom'].lower(),'') or pos_of(r['section'])
        flag='verify-with-native' if use=='verify' else ''
        prev=seen.get(r['rom'].lower())
        if prev is not None and r['rom'].lower() not in ('aḍugu',):
            p=words[prev]
            p['AlsoSeenIn']=(p['AlsoSeenIn']+' '+pid).strip()
            if len(en)>len(p['English']): p['English']=en
            continue
        seen[r['rom'].lower()]=len(words)
        words.append(dict(English=en, Romanized=r['rom'], TeluguScript=r['tel'], Audio='',
            Example=r['ex'], Tags=' '.join(filter(None,[f'src::{pid}',f'cat::{slug(cat)}',f'tier::{tier}',
                'flag::verify' if flag else ''])),
            ID='', Source=plabel, Section=r['section'], Category=cat, Tier=tier,
            Flag=flag, AlsoSeenIn=''))
for i,w in enumerate(words,1): w['ID']=f'W{i:04d}'

# ---------------- SENTENCES ----------------
RESPECT=re.compile(r'\b(mīru|mī|gāru|aṇḍi)\b|(aṇḍi|ṇḍi|āru|nnārā|āru\?)$|(andi|aṇḍi)\b')
def register_cue(rom):
    r=' '+rom.lower()+' '
    if re.search(r'\b(nuvvu|nī|nīku|vāḍu|vāḍi|vīḍu)\b', r): return 'informal'
    if re.search(r'\b(mīru|mī|gāru)\b', r) or re.search(r'(nnārā|chēsāru|unnāru)', r): return 'respectful'
    for t in (strip(x).lower() for x in toks(rom)):
        if t.endswith('ṇḍi'): return 'respectful'          # aṇḍi, raṇḍi, ivvaṇḍi, āgaṇḍi
        if t.endswith('andi') and len(t)>=7: return 'respectful'  # vaddandi, lēdandi — not 'mandi'
    return ''

TITLE={'scenario':'scenario','phrase':'phrase','template':'frame','mini-dialogue':'dialogue',
       'story':'story','contrast':'contrast','production-prompt':'drill','selftest':'drill','example':'example'}

def is_meta(en, rom):
    """A card is a production card only if the answer is a Telugu utterance:
    at least one token has to be a word the site itself teaches."""
    a=rom.strip()
    if re.match(r'^(no\.|yes\.|malformed|urdu-origin|\d)', a.lower()): return True
    if re.match(r'^(which|break down|give the near)\b', en.strip().lower()): return True
    return not any(strip(t).lower() in lex for t in toks(a))

def clean_en(en, kind):
    e=en.strip()
    e=re.sub(r'^[—–-]\s*','',e)
    if kind=='contrast':
        m=re.match(r'^[“"](.+?)[”"]\s*(.*)$', e)
        if m: return m.group(1).strip(), m.group(2).strip()
        m=re.match(r'^(Literally\s+[“"].+?[”"])\.?\s*(.*)$', e)
        if m: return m.group(1).strip(), m.group(2).strip()
    if kind=='example':
        m=re.match(r'^[“"](.+?)[”"]\s*(.*)$', e)
        if m: return m.group(1).strip(), m.group(2).strip()
    return e, ''

sents=[]
for page in ORDER:
    for r in S:
        if r['src']!=page: continue
        kind=r['kind']; rom=r['rom'].strip(); tel=r['tel'].strip(); en=r['en'].strip()
        if not rom or not en: continue
        if '→' in rom: continue
        if kind=='example' and len([t for t in toks(rom) if t])<2: continue
        if kind=='example' and '·' in rom: continue
        if kind=='contrast' and len(toks(rom))<2: continue
        if page=='concepts/registers-dialects-urdu.html' and kind=='production-prompt': continue
        en2, extra = clean_en(en, kind)
        if kind=='example' and not re.match(r'^[A-Z0-9"“]', en2):
            continue  # the English is a side note, not a meaning — no usable prompt
        note=' '.join(x for x in [extra, r.get('note','')] if x).strip()
        note=re.sub(r'^\(|\)$','',note).strip()
        status='verbatim'
        if not tel:
            g, miss = render(rom)
            if not miss: tel, status = g, 'assembled'
            else: tel, status = '', 'needs-script'
        reg=register_cue(rom)
        meta=is_meta(en2, rom)
        pid, plabel = PAGE[page]
        sents.append(dict(EnglishPrompt=en2, EnglishAudio='', TeluguScript=tel, Romanization=rom,
            TeluguAudio='', Notes=note,
            Tags=' '.join(filter(None,[f'src::{pid}',f'type::{TITLE[kind]}',
                f'reg::{reg}' if reg else '', 'mode::recognition' if meta else 'mode::production',
                'flag::needs-script' if status=='needs-script' else '',
                'flag::assembled' if status=='assembled' else ''])),
            ID='', Source=plabel, Kind=TITLE[kind], RegisterCue=reg,
            CardMode='recognition' if meta else 'production', ScriptStatus=status,
            Level=r.get('level',''), Label=r.get('label','')))

def prompt_score(s_):
    """Prefer a clean English meaning over lesson-internal commentary."""
    e=s_['EnglishPrompt']; n=0
    if s_['CardMode']=='production': n+=6
    if re.match(r'^[A-Z"“]', e): n+=3
    if re.search(r'\bLesson \d', e): n-=5
    if re.search(r'^(Give|Say|Now say|Which|Break down)\b', e): n-=2
    if re.search(r'[.?!]$|["”]', e): n+=2
    # commentary about a sentence is not a prompt for producing it
    if re.search(r'\b(neutral answer|possible when|answer to|relevant|context|merely|'
                 r'do not insert|the point may|presented|deliberately)\b', e, re.I): n-=6
    n+=min(len(e),40)/80.0
    return n

# dedupe on normalized romanization, merge notes
FOLD=str.maketrans('āīūēōṭḍṇḷṣśñṅṛ','aiueotdnlssnnr')
def norm(s):
    s=s.lower().translate(FOLD).replace('ṁ','m').replace('r̥','r')
    s=re.sub(r'(ch|c)','c',s)
    return re.sub(r'[^a-z ]','',s).strip()
out=[]; idx={}
for s_ in sents:
    k=norm(s_['Romanization'])
    if k in idx:
        p=out[idx[k]]
        if prompt_score(s_) > prompt_score(p):
            p['EnglishPrompt'], s_['EnglishPrompt'] = s_['EnglishPrompt'], p['EnglishPrompt']
            p['CardMode']=s_['CardMode']
        n=re.sub(r'\W+','',s_['Notes'].lower())
        if s_['Notes'] and n and n not in re.sub(r'\W+','',p['Notes'].lower()):
            p['Notes']=(p['Notes']+' · '+s_['Notes']).strip(' ·')
        if not p['TeluguScript'] and s_['TeluguScript']:
            p['TeluguScript']=s_['TeluguScript']; p['ScriptStatus']=s_['ScriptStatus']
        continue
    idx[k]=len(out); out.append(s_)
sents=out
for i,s_ in enumerate(sents,1): s_['ID']=f'S{i:04d}'

# add register cue into the English prompt where the Telugu is grammatically marked
for s_ in sents:
    if s_['CardMode']!='production': continue
    r=s_['RegisterCue']; e=s_['EnglishPrompt']
    if r and not re.search(r'formal|informal|respect|polite|elder|colleague|stranger|friend|familiar', e, re.I):
        if '/' in s_['Romanization']: continue
        s_['EnglishPrompt']=f"{e} [{'respectful' if r=='respectful' else 'informal'}]" 

WCOLS=['English','Romanized','TeluguScript','Audio','Example','Tags','ID','Source','Section','Category','Tier','Flag','AlsoSeenIn']
SCOLS=['EnglishPrompt','EnglishAudio','TeluguScript','Romanization','TeluguAudio','Notes','Tags','ID','Source','Kind','RegisterCue','CardMode','ScriptStatus','Level','Label']
def write(path, cols, rows):
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
write(os.path.join(OUTDIR,'telugu_words.csv'), WCOLS, words)
write(os.path.join(OUTDIR,'telugu_sentences.csv'), SCOLS, sents)
print('words', len(words), collections.Counter(w['Tier'] for w in words))
print('sentences', len(sents))
print(' mode', collections.Counter(s['CardMode'] for s in sents))
print(' script', collections.Counter(s['ScriptStatus'] for s in sents))
print(' kind', collections.Counter(s['Kind'] for s in sents))
print(' reg', collections.Counter(s['RegisterCue'] for s in sents))
