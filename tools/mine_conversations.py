# -*- coding: utf-8 -*-
"""Mine the family conversation transcripts for vocabulary candidates.

    python3 tools/mine_conversations.py

These transcripts are the lowest-confidence source in the project and are treated as such:

  * They carry no Telugu script, and romanization -> script is the unreliable direction
    (87% in testing), so nothing here can be promoted to a card automatically.
  * The romanization is ad-hoc and phonetic ("vasthundhi", "cheppindu"), not the project
    convention, so it cannot be merged on romanization either.
  * They are heavily code-mixed; a large share of rows are simply English.

So the output is not sentences. It is a frequency-ranked list of Telugu-looking tokens that
do NOT already appear in the word master — candidates for a native speaker to give script
and a gloss to. High frequency across real family speech is a genuine signal that the
existing lists, built from textbooks and English frequency data, will have missed.

PRIVACY: the inputs are recordings of family at home and stay in sources/private/ (gitignored).
Only single tokens leave this script, and any token matching a name seen in the transcripts,
or any digit, is dropped. No sentence, and nothing identifying, is ever written to disk.
"""
import csv, glob, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, 'sources', 'private', 'conversations')
OUT = os.path.join(ROOT, 'review', 'convo-vocab-candidates.tsv')
WORDS = os.path.join(ROOT, 'data', 'master_words.tsv')

# People, places and brands that appear in the recordings. Never emitted.
NAMES = {
 'ashok','aashok','sampath','nagesh','leela','shailu','shailaja','neha','sneha','josh',
 'sindhu','ravi','harish','rohan','pavan','bhupathi','reddy','morgan','pappu','paavuri',
 'amma','nana','naanna','baabu','gokila','agurchand','ganesh','nagar','hyderabad','india',
 'redmond','costco','safeway','instacart','swiggy','blinkit','doordash','uber','amazon',
 'sephora','barnes','noble','ugadhi','telugu','telangana','american','americansni','ram',
 'gopal','varma','ipad','kid','kids',
}

STOP_EN = {
 'the','a','an','and','or','but','if','so','to','of','in','on','at','for','with','from','by',
 'is','are','was','were','be','been','being','it','its','this','that','these','those','i',
 'you','he','she','we','they','me','him','her','us','them','my','your','his','their','our',
 'not','no','yes','do','does','did','done','have','has','had','will','would','can','could',
 'should','just','like','what','why','how','when','where','who','which','all','some','any',
 'one','two','more','most','very','too','also','then','than','now','here','there','out','up',
 'down','about','into','over','after','before','again','only','even','still','because','okay',
 'ok','yeah','oh','ah','uh','hey','well','good','know','think','get','got','go','going','went',
 'come','came','say','said','tell','told','see','saw','look','want','need','make','made','put',
 'take','took','give','gave','time','day','right','thing','things','people','back','way','much',
 'many','little','big','old','new','years','year','minutes','mean','really','something','nothing',
 'everything','someone','everyone','anything','other','same','next','last','first','sure','thank',
 'thanks','please','sorry','hold','wait','let','lot','bit','kind','sort','actually','probably',
 'maybe','always','never','every','both','each','own','while','though','since','until','without',
 'cake','cakes','chips','bread','phone','house','home','work','staff','job','business','money',
 'kid','baby','sleep','hungry','eat','ate','food','water','plate','knife','photo','video',
 'doctor','medicine','research','podcast','psychologist','daycare','teacher','parent','parents',
 'birthday','apartment','construction','wood','marble','door','window','windows','size','standard',
 'special','needs','license','trained','months','month','week','weeks','night','morning','shift',
 'slice','spoon','order','ordered','delivery','deliver','expensive','cheap','stock','shop','store',
 'section','bakery','garlic','lemon','custard','pie','strawberry','blueberry','pineapple','curry',
 'leaves','ghee','oil','salt','yogurt','dal','chili','spicy','sweet','tart','soft','dry','flavor',
}


def fold(s):
    s = (s or '').lower().translate(str.maketrans('āīūēōṭḍṇḷṁṣśṛ', 'aiueotdnlmssr'))
    s = re.sub(r'[^a-z]', '', s)
    for a, b in (('th','t'),('dh','d'),('bh','b'),('gh','g'),('kh','k'),('ph','p'),
                 ('ch','c'),('sh','s'),('aa','a'),('ee','i'),('oo','u'),('ii','i'),
                 ('uu','u'),('y','i'),('w','v')):
        s = s.replace(a, b)
    return re.sub(r'(.)\1+', r'\1', s)


def known_index():
    exact, stems = set(), set()
    if not os.path.exists(WORDS):
        return exact, stems
    for r in csv.DictReader(open(WORDS, encoding='utf-8'), delimiter='\t'):
        for piece in (r['roman'] or '').split():
            f = fold(piece)
            if f:
                exact.add(f)
                if len(f) >= 4:
                    stems.add(f[:4])
    return exact, stems


def main():
    files = sorted(glob.glob(os.path.join(SRC, '*.csv')))
    if not files:
        print('no transcripts in sources/private/conversations/'); return
    exact, stems = known_index()

    rows_total = rows_english = 0
    counts, examples = Counter(), {}
    for path in files:
        for r in csv.reader(open(path, encoding='utf-8')):
            if len(r) < 2 or r[0].strip().lower() == 'telugu':
                continue
            rows_total += 1
            te, en = r[0].strip(), r[1].strip()
            if te == en:                     # the row is simply English
                rows_english += 1
                continue
            for raw in re.split(r"[^A-Za-z']+", te):
                t = raw.strip("'").lower()
                if len(t) < 3 or t in STOP_EN or t in NAMES:
                    continue
                f = fold(t)
                if not f or f in exact or (len(f) >= 4 and f[:4] in stems):
                    continue
                counts[t] += 1
                examples.setdefault(t, os.path.basename(path))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['token_as_heard', 'count', 'telugu_script', 'english', 'keep'])
        for tok, n in counts.most_common():
            if n < 2:                        # a single noisy occurrence is not evidence
                continue
            w.writerow([tok, n, '', '', ''])

    kept = sum(1 for t, n in counts.items() if n >= 2)
    print(f'transcripts     : {len(files)} files, {rows_total} rows')
    print(f'  pure English  : {rows_english} rows dropped')
    print(f'  candidate tokens (unknown, seen 2+ times): {kept}')
    print(f'  -> {os.path.relpath(OUT, ROOT)}')
    print('\n  top 25:')
    top = [(t, n) for t, n in counts.most_common() if n >= 2][:25]
    print('   ', ', '.join(f'{t}({n})' for t, n in top))


if __name__ == '__main__':
    main()
