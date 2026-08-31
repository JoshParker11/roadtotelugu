# -*- coding: utf-8 -*-
"""Define the remaining course vocabulary through the Batch API, in context.

    python3 tools/ic_gloss_batch.py --plan              # what it would ask, and the cost
    python3 tools/ic_gloss_batch.py --submit            # send it (needs ANTHROPIC_API_KEY)
    python3 tools/ic_gloss_batch.py --collect <batch_id>  # -> intensive/vocab.tsv

WHY NOT A DICTIONARY
Measured, not assumed. Of the words still unglossed, 59% end in an inflectional ending, and a
headword dictionary has no entry for an inflected form — the finding PRACTICE.md already
recorded about the podcast reader. The remaining 41% were probed against both English and
Telugu Wiktionary through their APIs: **5% hit rate on the forty most frequent**. These are
conversational forms from a 1970s Hyderabad textbook, and open dictionaries do not carry them.

WHY NOT MORE MORPHOLOGY
Also measured. Peeling a full Telugu inflectional inventory recursively, requiring every stem
to be a word we already know, resolved 9% — and produced garbage on the way: రంగా came apart
as ర + ం + గా. Aggressive segmentation invents structure, and plausible-looking nonsense is
worse here than a blank.

WHAT IS LEFT IS PER-WORD JUDGEMENT WITH CONTEXT, WHICH IS WHAT THE MODEL IS FOR
Each request carries one word, the Telugu sentence it appears in, and that sentence's published
English translation. That is the same evidence a person would use, and it is why this can be
asked in bulk rather than researched one at a time.

EVERY ANSWER LANDS AS status=draft
Nothing checks these. ms_vocab.py has said so since it was written and it is still true — the
reader marks a draft card as unreviewed, and that is the honest state until a native speaker
reads it.
"""
import argparse
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
IC = os.path.join(ROOT, 'intensive')
CARDS = os.path.join(IC, 'vocab.tsv')
BATCH_ID = os.path.join(IC, '.batch_id')     # so --collect needs no copy-paste
READER = os.path.join(ROOT, 'reader', 'data', 'intensive.js')
MODEL = 'claude-opus-5'

SYSTEM = (
    "You gloss Telugu words for an English-speaking learner's reading tool.\n"
    "You are given one word, the Telugu sentence it appears in, and that sentence's published "
    "English translation.\n\n"
    "Return the meaning THAT WORD carries in THAT sentence — not the whole sentence, and not a "
    "list of everything the word can mean.\n"
    "For an inflected form, give the meaning and name the dictionary form it comes from.\n"
    "If the string is not a Telugu word — OCR debris, a stray mark, a fragment — set pos to "
    "'ocr-junk' and leave gloss empty. Do not invent a meaning to fill the field.\n"
    "Keep gloss under 60 characters. pos is a short label such as noun, verb, adverb, "
    "postposition, name, or a form description like 'verb — past, 3sg fem'."
)

SCHEMA = {
    'type': 'json_schema',
    'schema': {
        'type': 'object',
        'properties': {
            'gloss': {'type': 'string'},
            'pos': {'type': 'string'},
        },
        'required': ['gloss', 'pos'],
        'additionalProperties': False,
    },
}


def pending():
    """Unglossed words, most frequent first, each with the sentence it first appears in."""
    with open(READER, encoding='utf-8') as f:
        s = f.read()
    i = s.index('window.IC_DATA = ') + len('window.IC_DATA = ')
    d = json.loads(s[i:s.index('\n', i)].rstrip(';'))
    lex = d['lex']
    has = lambda l: bool((l.get('en') or '').strip() or l.get('sn') or l.get('p')
                         or l.get('head') or l.get('junk'))
    freq = collections.Counter()
    ctx = {}
    for st in d['stories']:
        for ln in st['lines']:
            te = ''.join(t[0] for t in ln['t'])
            for w, k, ix in ln['t']:
                if ix < 0:
                    continue
                freq[ix] += 1
                if ix not in ctx:
                    ctx[ix] = (te, ln.get('en', ''))
    out = [(freq[i], lex[i], ctx.get(i, ('', ''))) for i, l in enumerate(lex) if not has(l)]
    out.sort(key=lambda x: -x[0])
    return out


def requests_for(items):
    reqs = []
    for f, l, (te_sent, en_sent) in items:
        reqs.append({
            'custom_id': l['g'],
            'params': {
                'model': MODEL,
                'max_tokens': 200,
                'system': SYSTEM,
                'output_config': {'format': SCHEMA, 'effort': 'low'},
                'messages': [{'role': 'user', 'content':
                              f'word: {l["te"]}\nsentence: {te_sent}\ntranslation: {en_sent}'}],
            },
        })
    return reqs


def cmd_plan(args):
    items = pending()[:args.limit] if args.limit else pending()
    reqs = requests_for(items)
    # A rough token estimate. Telugu is not Latin — it costs more tokens per character than the
    # English beside it — so this deliberately errs high rather than quoting a number that only
    # holds for ASCII.
    chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in reqs)
    tin = chars / 2.5
    tout = len(reqs) * 45
    # Batch API is half price. Opus 5 is $5/$25 per MTok.
    cost = (tin / 1e6 * 5 + tout / 1e6 * 25) * 0.5
    print(f'{len(reqs)} words to define')
    print(f'  ~{tin/1000:.0f}K input tokens, ~{tout/1000:.0f}K output')
    print(f'  ~${cost:.2f} on {MODEL} through the Batch API (half price)')
    print(f'  ~${(tin/1e6*1 + tout/1e6*5)*0.5:.2f} if you pass --model claude-haiku-4-5 instead')
    print('\nfirst three requests:')
    for r in reqs[:3]:
        print('  ' + r['params']['messages'][0]['content'].replace('\n', ' | ')[:110])


def client():
    try:
        import anthropic
    except ImportError:
        sys.exit('pip3 install anthropic')
    return anthropic.Anthropic()


def cmd_submit(args):
    import anthropic
    from anthropic.types.messages.batch_create_params import Request
    items = pending()[:args.limit] if args.limit else pending()
    reqs = requests_for(items)
    c = client()
    batch = c.messages.batches.create(
        requests=[Request(custom_id=r['custom_id'], params=r['params']) for r in reqs])
    with open(BATCH_ID, 'w', encoding='utf-8') as f:
        f.write(batch.id + '\n')
    print(f'submitted {len(reqs)} requests\n  batch id: {batch.id}\n  status: {batch.processing_status}')
    print('\nwhen it has finished (usually well under an hour):')
    print('  python3 tools/ic_gloss_batch.py --collect')


def resolve_id(given):
    if given:
        return given
    if not os.path.exists(BATCH_ID):
        sys.exit('no remembered batch id — pass one explicitly')
    return open(BATCH_ID, encoding='utf-8').read().strip()


def describe(batch):
    c = getattr(batch, 'request_counts', None)
    if not c:
        return batch.processing_status
    done = c.succeeded + c.errored + c.canceled + c.expired
    total = done + c.processing
    pct = f'{done / total:.0%}' if total else '—'
    bits = [f'{c.succeeded} done']
    if c.errored:
        bits.append(f'{c.errored} errored')
    if c.expired:
        bits.append(f'{c.expired} expired')
    if c.canceled:
        bits.append(f'{c.canceled} canceled')
    if c.processing:
        bits.append(f'{c.processing} still running')
    return f'{batch.processing_status} · {pct} · ' + ', '.join(bits)


def cmd_status(args):
    """Where the batch is, without touching vocab.tsv."""
    bid = resolve_id(args.status)
    b = client().messages.batches.retrieve(bid)
    print(f'{bid}\n  {describe(b)}')
    if b.processing_status == 'ended':
        print('\nready — python3 tools/ic_gloss_batch.py --collect')


def cmd_wait(args):
    """Poll until it ends, then ingest. The one command you can walk away from."""
    import time
    bid = resolve_id(args.wait)
    c = client()
    while True:
        b = c.messages.batches.retrieve(bid)
        print(f'  {describe(b)}', flush=True)
        if b.processing_status == 'ended':
            break
        time.sleep(30)
    args.collect = bid
    cmd_collect(args)


def cmd_collect(args):
    c = client()
    batch = c.messages.batches.retrieve(args.collect)
    if batch.processing_status != 'ended':
        counts = getattr(batch, 'request_counts', None)
        print(f'batch {args.collect} is {batch.processing_status} — not ready yet')
        if counts:
            print(f'  {counts}')
        return
    by_te = {}
    with open(READER, encoding='utf-8') as f:
        s = f.read()
    i = s.index('window.IC_DATA = ') + len('window.IC_DATA = ')
    for l in json.loads(s[i:s.index('\n', i)].rstrip(';'))['lex']:
        by_te[l['g']] = l['te']

    rows, errors = [], 0
    # Results come back in ANY order — key on custom_id, never on position.
    for res in c.messages.batches.results(args.collect):
        if res.result.type != 'succeeded':
            errors += 1
            continue
        try:
            payload = json.loads(res.result.message.content[0].text)
        except Exception:
            errors += 1
            continue
        te = by_te.get(res.custom_id)
        if not te:
            continue
        junk = payload.get('pos') == 'ocr-junk' or not payload.get('gloss', '').strip()
        rows.append({'te': te, 'gloss': '' if junk else payload['gloss'].strip(),
                     'pos': '' if junk else payload.get('pos', '').strip(),
                     'status': 'ocr-junk' if junk else 'draft'})

    existing = []
    if os.path.exists(CARDS):
        with open(CARDS, encoding='utf-8') as f:
            existing = list(csv.DictReader(f, delimiter='\t'))
    have = {r['te'] for r in existing}
    added = [r for r in rows if r['te'] not in have]      # hand-written cards win
    with open(CARDS, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, delimiter='\t', fieldnames=['te', 'gloss', 'pos', 'status'])
        w.writeheader(); w.writerows(existing + added)
    print(f'{len(added)} new cards ({sum(1 for r in added if r["status"] == "ocr-junk")} '
          f'marked ocr-junk), {len(rows) - len(added)} already had a hand-written card, '
          f'{errors} failed')
    print('then: python3 tools/build_ic_reader.py --all')


def main():
    global MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--submit', action='store_true')
    ap.add_argument('--collect', nargs='?', const='', metavar='BATCH_ID',
                    help='ingest results; the id is remembered from --submit')
    ap.add_argument('--status', nargs='?', const='', metavar='BATCH_ID',
                    help='how far along the batch is; touches nothing')
    ap.add_argument('--wait', nargs='?', const='', metavar='BATCH_ID',
                    help='poll every 30s until it ends, then collect')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--model', default=MODEL)
    args = ap.parse_args()
    MODEL = args.model
    if args.status is not None:
        cmd_status(args)
    elif args.wait is not None:
        cmd_wait(args)
    elif args.collect is not None:
        if not args.collect:
            if not os.path.exists(BATCH_ID):
                sys.exit('no remembered batch id — pass it: --collect <batch_id>')
            args.collect = open(BATCH_ID, encoding='utf-8').read().strip()
        cmd_collect(args)
    elif args.submit:
        cmd_submit(args)
    else:
        cmd_plan(args)


if __name__ == '__main__':
    main()
