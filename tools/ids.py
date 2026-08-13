# -*- coding: utf-8 -*-
"""Stable note ids.

WHY THIS EXISTS
The masters used to hand Anki their row number as the GUID — W0001, W0002. That is fine until
the master changes length. Dropping one bad entry renumbers every row after it, so W0519 stops
meaning తను and starts meaning నివసిస్తున్నారు. Anki matches on GUID, finds the note, and
*overwrites it with a different word* while keeping its scheduling. Measured on one real
rebuild: **1,431 of 1,927 shared guids pointed at a different word.**

That is worse than duplicates, because nothing looks wrong. It is also almost certainly where
the orphaned notes in the collection came from.

So the id is derived from content instead of position. The key is the Telugu script, which is
what anchors every other join in this pipeline; entries that have no script fall back to their
folded romanization. Same word, same id, forever — regardless of what else enters or leaves the
master, what order sources merge in, or whether a row above it was dropped.

The positional `id` column stays, because study order is genuinely useful and W0001 is readable
in a way a hash is not. It is just no longer what Anki is told to match on.
"""
import hashlib
import re

_FOLD = str.maketrans('āīūēōṭḍṇḷṁṣśṛ', 'aiueotdnlmssr')


def fold(s):
    """Same normalisation the masters use for script-less keys."""
    return re.sub(r'[^a-z]', '', (s or '').lower().translate(_FOLD))


def guid(prefix, telugu, roman=''):
    """Content-derived, collision-resistant, stable across rebuilds.

    prefix is 'W' or 'S' so a word and a sentence can never collide even if a one-word
    sentence and its headword share a spelling.
    """
    key = (telugu or '').strip() or 'rom:' + fold(roman)
    h = hashlib.sha1(f'{prefix}:{key}'.encode('utf-8')).hexdigest()
    return prefix + h[:12]


def assign(rows, prefix):
    """Set rows[i]['guid'], and raise if two rows would share one.

    A collision here means two entries the pipeline considers distinct have the same anchor,
    which is a data problem worth stopping for rather than a hash problem worth widening.
    """
    seen = {}
    for r in rows:
        g = guid(prefix, r.get('telugu', ''), r.get('roman', ''))
        if g in seen:
            other = seen[g]
            raise SystemExit(
                f'guid collision {g}:\n'
                f'  {r.get("telugu","")!r} / {r.get("roman","")!r}\n'
                f'  {other.get("telugu","")!r} / {other.get("roman","")!r}\n'
                'Two entries share an anchor — deduplicate them in the master.')
        seen[g] = r
        r['guid'] = g
    return rows
