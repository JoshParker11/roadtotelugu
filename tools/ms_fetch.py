# -*- coding: utf-8 -*-
"""Pull the LingQ Mini Stories from LingQ into ministories/source/api/, as raw JSON.

    export LINGQ_API_KEY=...            # from https://www.lingq.com/accounts/apikey/
    python3 tools/ms_fetch.py --probe   # fetch ONE lesson, print its shape, write nothing else
    python3 tools/ms_fetch.py           # fetch the collection + all 62 lessons
    python3 tools/ms_fetch.py --force   # re-fetch lessons already on disk

WHY THIS ONLY DUMPS, AND NEVER PARSES
The v3 API is undocumented — lingq.com/apidocs covers v2 and 404s for the rest. We know the
auth header and we know the collection path exists (it answers 401, not 404, unauthenticated),
but not what a lesson payload actually contains. So this script's entire job is to get the bytes
onto disk exactly as served. ms_segment.py does the interpreting.

That split matters because the two halves fail differently. Fetching is 63 network round-trips
against someone else's rate limiter; parsing is a guess about field names that we will get wrong
at least once. Keeping them separate means a wrong guess costs a re-run of the parser over local
files, not 63 more requests. Run --probe first and read the shape before trusting anything.

THE KEY IS NEVER STORED
Read from the environment, never written to disk, never echoed, never committed. If it is unset
this exits with instructions rather than prompting, so it is safe in a pipeline.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
API = os.path.join(MS, 'source', 'api')
CATALOG = os.path.join(MS, 'CATALOG.tsv')

BASE = 'https://www.lingq.com/api/v3/en'
COLLECTION = '2377874'          # LingQ Mini Stories - American English
PAUSE = 1.0                     # seconds between requests; we are a guest on their box
TIMEOUT = 60                    # 30 was not enough for some of their endpoints


def key():
    k = os.environ.get('LINGQ_API_KEY', '').strip()
    if not k:
        sys.exit('LINGQ_API_KEY is not set.\n'
                 '  1. log in to LingQ, open https://www.lingq.com/accounts/apikey/\n'
                 '  2. export LINGQ_API_KEY=<the key>\n'
                 'The key is read from the environment and never written to disk.')
    return k


def get(path):
    url = path if path.startswith('http') else f'{BASE}/{path}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Token {key()}',
        'Accept': 'application/json',
        'User-Agent': 'roadtotelugu/ministories (personal study)',
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')[:400]
        if e.code in (401, 403):
            sys.exit(f'HTTP {e.code} on {url}\nThe key was rejected. Re-copy it from '
                     f'https://www.lingq.com/accounts/apikey/\n{body}')
        sys.exit(f'HTTP {e.code} on {url}\n{body}')


def shape(obj, prefix='', depth=0):
    """Print the payload's structure without printing the payload."""
    if depth > 2:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            kind = type(v).__name__
            hint = ''
            if isinstance(v, str):
                hint = f' len={len(v)}'
            elif isinstance(v, list):
                hint = f' n={len(v)}'
            print(f'  {prefix}{k}: {kind}{hint}')
            if isinstance(v, (dict, list)) and k not in ('cards',):
                shape(v, prefix + k + '.', depth + 1)
    elif isinstance(obj, list) and obj:
        shape(obj[0], prefix + '[0].', depth + 1)


def collection():
    """Collection metadata. Note it does NOT contain the lesson list — only lessonsCount."""
    path = os.path.join(API, '_collection.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    data = get(f'collections/{COLLECTION}/')
    os.makedirs(API, exist_ok=True)
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return data


def lesson_list():
    """The 62 lessons, from the paginated sub-resource.

    The obvious guess — that collections/<id>/ carries its own lessons — is wrong: that payload
    is metadata only and reports lessonsCount without ever listing them. The list lives at
    collections/<id>/lessons/, paginated in the usual count/next/previous/results envelope.
    Cached, because it is the map every other step walks.
    """
    path = os.path.join(API, '_lessons.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    rows, url = [], f'collections/{COLLECTION}/lessons/'
    while url:
        page = get(url)
        rows.extend(page['results'])
        url = page.get('next')
        if url:
            time.sleep(PAUSE)
    os.makedirs(API, exist_ok=True)
    json.dump(rows, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return rows


def backfill_catalog(rows):
    """Write each lesson's LingQ id into CATALOG.tsv.

    Join on the lesson NUMBER, not the title. LingQ titles begin with the number ("1a - Mike Is
    a Cook, Part 1") while the catalog was built with that prefix split into its own columns, so
    a title-to-title join matches nothing. The number is exact and survives any later retitling;
    the normalised title is kept only as a fallback for a row whose prefix is malformed.

    Any row that fails to match is reported rather than silently skipped — a missing id means
    ms_segment.py quietly falls through to the paste path, which you would not otherwise notice.
    """
    def numkey(title):
        m = re.match(r'\s*(\d+)\s*([a-c]?)\s*-', title or '')
        return f'{int(m.group(1)):02d}{m.group(2).lower()}' if m else None

    def titlekey(title):
        t = re.sub(r'^\s*\d+\s*[a-c]?\s*-\s*', '', title or '')
        return re.sub(r'[^a-z0-9]+', '', t.lower())

    by_num = {}
    by_title = {}
    for r in rows:
        by_num.setdefault(numkey(r['title']), str(r['id']))
        by_title.setdefault(titlekey(r['title']), str(r['id']))

    with open(CATALOG, encoding='utf-8') as f:
        cat = list(csv.DictReader(f, delimiter='\t'))
    fields = list(cat[0].keys())
    missed = []
    for c in cat:
        lid = by_num.get(c['id']) or by_title.get(titlekey(c['title']))
        if lid:
            c['lesson_id'] = lid
        else:
            missed.append(c['id'])
    with open(CATALOG, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fields, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(cat)
    if missed:
        print('WARNING: no lesson id matched for: ' + ' '.join(missed))
    return len(cat) - len(missed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', action='store_true',
                    help='fetch the collection and one lesson, print their shape, stop')
    ap.add_argument('--force', action='store_true', help='re-fetch lessons already on disk')
    args = ap.parse_args()

    os.makedirs(API, exist_ok=True)
    meta = collection()
    rows = lesson_list()
    print(f"{meta.get('title')}: {meta.get('lessonsCount')} lessons, {len(rows)} listed")
    n = backfill_catalog(rows)
    print(f'catalog: {n} lesson ids filled in')
    lessons = [(str(r['id']), r.get('title', '')) for r in rows]

    if args.probe:
        lid, title = lessons[0]
        print(f'\n--- lesson {lid} ({title}) shape ---')
        shape(get(f'lessons/{lid}/'))
        print('\nProbe only; nothing else written. Check the field names above against '
              'ms_segment.py before the full run.')
        return

    for i, (lid, title) in enumerate(lessons, 1):
        path = os.path.join(API, f'{lid}.json')
        if os.path.exists(path) and not args.force:
            print(f'{i:>3}/{len(lessons)} {lid} cached')
            continue
        payload = get(f'lessons/{lid}/')
        json.dump(payload, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'{i:>3}/{len(lessons)} {lid} {title[:50]}')
        time.sleep(PAUSE)

    # Record the ids next to the titles we already catalogued, so ms_segment can join on them.
    print(f'\nwrote {len(lessons)} payloads to ministories/source/api/')
    print('next: python3 tools/ms_segment.py')


if __name__ == '__main__':
    main()
