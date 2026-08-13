# -*- coding: utf-8 -*-
"""Daily practice log — the objective half filled in for you.

    python3 tools/session_log.py            # start today's entry (opens $EDITOR)
    python3 tools/session_log.py --show     # today's numbers, write nothing
    python3 tools/session_log.py --summary  # streak and totals across the log

Vocabulary and sentences already have a complete audit trail: every word is in a master with
its source, and every decision is in the git history. Daily *practice* has none — and that is
the half that matters for explaining later how you actually got there.

The reason this is a script and not just a notes file: you will not reliably record "47
reviews in 11 minutes at 84% retention", but your collection already knows. So the numbers are
read from the Anki revlog and the prose is left to you. Writing "what I could not say" is the
one field worth being disciplined about — it is the bridge from practice back into the fix
pipeline and into questions for a native speaker.

Entries append to log/YYYY-MM.md. Plain markdown; nothing here parses it back except --summary.
"""
import argparse, json, os, re, shutil, sqlite3, subprocess, sys, tempfile
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
LOGDIR = os.path.join(ROOT, 'log')
COL = os.path.expanduser('~/Library/Application Support/Anki2/User 1/collection.anki2')

EASE = {1: 'again', 2: 'hard', 3: 'good', 4: 'easy'}


def snapshot():
    """Read-only copy — the live collection is never opened for writing."""
    if not os.path.exists(COL):
        return None, None
    tmp = tempfile.mkdtemp()
    snap = os.path.join(tmp, 'c.anki2')
    shutil.copy2(COL, snap)
    for ext in ('-wal', '-shm'):
        if os.path.exists(COL + ext):
            shutil.copy2(COL + ext, snap + ext)
    db = sqlite3.connect(f'file:{snap}?mode=ro', uri=True)
    db.create_collation('unicase', lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))
    db.row_factory = sqlite3.Row
    return db, tmp


def rollover_hour(db):
    """Anki's day boundary — default 4am, so a late session counts as the same day."""
    try:
        v = db.execute("select val from config where key='rollover'").fetchone()
        if v:
            return int(json.loads(v['val']))
    except Exception:
        pass
    return 4


def day_bounds(db, when):
    h = rollover_hour(db)
    start = datetime(when.year, when.month, when.day, h)
    return int(start.timestamp() * 1000), int((start + timedelta(days=1)).timestamp() * 1000)


def stats_for(db, when):
    lo, hi = day_bounds(db, when)
    rows = list(db.execute(
        'select revlog.ease, revlog.type, revlog.time, notes.mid '
        'from revlog join cards on cards.id = revlog.cid join notes on notes.id = cards.nid '
        'where revlog.id >= ? and revlog.id < ?', (lo, hi)))
    if not rows:
        return {'total': 0}
    names = {r['id']: r['name'] for r in db.execute('select id, name from notetypes')}
    by_type, by_deck = {}, {}
    for r in rows:
        by_type[r['type']] = by_type.get(r['type'], 0) + 1
        n = names.get(r['mid'], '?')
        by_deck[n] = by_deck.get(n, 0) + 1
    graded = [r for r in rows if r['ease']]
    again = sum(1 for r in graded if r['ease'] == 1)
    return {
        'total': len(rows),
        'new': by_type.get(0, 0),
        'review': by_type.get(1, 0),
        'relearn': by_type.get(2, 0),
        'minutes': round(sum(r['time'] for r in rows) / 60000, 1),
        'retention': round(100 * (1 - again / len(graded))) if graded else None,
        'by_notetype': dict(sorted(by_deck.items(), key=lambda kv: -kv[1])),
    }


def render(when, s):
    lines = [f'## {when.isoformat()} · {when.strftime("%A")}', '']
    if s['total']:
        bits = [f"**{s['total']} cards** in {s['minutes']} min"]
        if s['retention'] is not None:
            bits.append(f"{s['retention']}% retention")
        bits.append(f"{s['new']} new · {s['review']} review" +
                    (f" · {s['relearn']} relearn" if s['relearn'] else ''))
        lines += ['**Anki** — ' + ' · '.join(bits), '',
                  '  ' + ' · '.join(f'{k}: {v}' for k, v in s['by_notetype'].items()), '']
    else:
        lines += ['**Anki** — nothing reviewed.', '']
    lines += [
        '**Verb Lab** — <!-- verbs drilled, score, what felt automatic and what did not -->', '',
        '**What I did** —', '', '',
        '**What I could not say** —', '',
        '<!-- the useful one. Anything you reached for and missed, in English is fine.',
        '     This becomes questions for a native speaker and rows in review/. -->', '',
        '**Questions** —', '', '',
        '**Notes** —', '', '', '---', '']
    return '\n'.join(lines)


def logfile(when):
    os.makedirs(LOGDIR, exist_ok=True)
    p = os.path.join(LOGDIR, when.strftime('%Y-%m.md'))
    if not os.path.exists(p):
        with open(p, 'w', encoding='utf-8') as f:
            f.write(f'# Practice log — {when.strftime("%B %Y")}\n\n'
                    'Newest at the bottom. Generated by `tools/session_log.py`.\n\n---\n\n')
    return p


def summary():
    entries = []
    for fn in sorted(os.listdir(LOGDIR)) if os.path.isdir(LOGDIR) else []:
        if not fn.endswith('.md'):
            continue
        for m in re.finditer(r'^## (\d{4}-\d{2}-\d{2}).*?(?=^## |\Z)',
                             open(os.path.join(LOGDIR, fn), encoding='utf-8').read(),
                             re.S | re.M):
            body = m.group(0)
            cards = re.search(r'\*\*(\d+) cards\*\* in ([\d.]+) min', body)
            entries.append((date.fromisoformat(m.group(1)),
                            int(cards.group(1)) if cards else 0,
                            float(cards.group(2)) if cards else 0.0))
    if not entries:
        print('no entries yet'); return
    entries.sort()
    days = {e[0] for e in entries}
    streak, d = 0, date.today()
    if d not in days:
        d -= timedelta(days=1)
    while d in days:
        streak += 1; d -= timedelta(days=1)
    print(f'entries      : {len(entries)}  ({entries[0][0]} → {entries[-1][0]})')
    print(f'current streak: {streak} day{"s" if streak != 1 else ""}')
    print(f'cards logged : {sum(e[1] for e in entries)}')
    print(f'hours logged : {round(sum(e[2] for e in entries) / 60, 1)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--show', action='store_true', help='print today\'s numbers, write nothing')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--date', help='YYYY-MM-DD, defaults to today')
    a = ap.parse_args()

    if a.summary:
        return summary()

    when = date.fromisoformat(a.date) if a.date else date.today()
    db, tmp = snapshot()
    s = stats_for(db, when) if db else {'total': 0}
    if tmp:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)

    if a.show:
        print(json.dumps(s, indent=1, ensure_ascii=False)); return

    p = logfile(when)
    existing = open(p, encoding='utf-8').read()
    if f'## {when.isoformat()}' in existing:
        print(f'{os.path.relpath(p, ROOT)} already has an entry for {when} — opening it')
    else:
        with open(p, 'a', encoding='utf-8') as f:
            f.write(render(when, s))
        print(f'appended {when} to {os.path.relpath(p, ROOT)}')
        if s['total']:
            print(f"  {s['total']} cards, {s['minutes']} min" +
                  (f", {s['retention']}% retention" if s['retention'] is not None else ''))
    editor = os.environ.get('EDITOR')
    if editor:
        subprocess.call([editor, p])
    else:
        print('  set $EDITOR to have it open automatically, or edit the file directly')


if __name__ == '__main__':
    main()
