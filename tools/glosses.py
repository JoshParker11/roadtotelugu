# -*- coding: utf-8 -*-
"""Choose one English gloss per entry instead of concatenating every source's wording.

Four sources describing the same card produced fronts like

    I'm fine.; I’m fine.; I am fine.; I feel good
    own (his/her own); his

which is friction on every single review. Three of those four are the same sentence typed
differently, and "his" is simply a worse gloss than "own (his/her own)".

The rule:

1. Normalise for comparison — straight quotes, expanded contractions, no trailing
   punctuation, lowercase. That collapses the first three above into one.
2. The best-sourced gloss becomes the card front. Source order is set by the caller; the
   course pages win because their glosses carry the register cues ("you (informal — close
   friends/family only)") that the raw wordlists lack.
3. A remaining gloss is only added to the front if it is a genuinely different sense —
   no content word in common with the primary. aḍugu "step, foot" / "to ask" keeps both;
   "small" / "little" / "tiny" does not.
4. Everything else drops to the notes, so it is still on the card but not in the prompt.
"""
import re

CONTRACTIONS = [
    (r"\bi'm\b", 'i am'), (r"\bit's\b", 'it is'), (r"\bthat's\b", 'that is'),
    (r"\bdon't\b", 'do not'), (r"\bdoesn't\b", 'does not'), (r"\bdidn't\b", 'did not'),
    (r"\bcan't\b", 'cannot'), (r"\bwon't\b", 'will not'), (r"\bisn't\b", 'is not'),
    (r"\baren't\b", 'are not'), (r"\bwasn't\b", 'was not'), (r"\bi've\b", 'i have'),
    (r"\bi'll\b", 'i will'), (r"\byou're\b", 'you are'), (r"\bwe're\b", 'we are'),
    (r"\bthey're\b", 'they are'), (r"\bwhat's\b", 'what is'), (r"\blet's\b", 'let us'),
    (r"\bhaven't\b", 'have not'), (r"\bhasn't\b", 'has not'), (r"\bshouldn't\b", 'should not'),
]

STOP = {'a', 'an', 'the', 'to', 'of', 'in', 'on', 'at', 'for', 'with', 'is', 'am', 'are',
        'was', 'were', 'be', 'do', 'does', 'did', 'it', 'i', 'you', 'he', 'she', 'we',
        'they', 'my', 'your', 'his', 'her', 'their', 'our', 'not', 'and', 'or', 'that',
        'this', 'one', 'some', 'any', 'so', 'as', 'by', 'from'}


def normalise(g):
    """Comparison key. 'I’m fine.' and 'I am fine' collapse to the same string."""
    s = (g or '').lower().replace('’', "'").replace('‘', "'")
    s = s.replace('“', '"').replace('”', '"')
    for pat, rep in CONTRACTIONS:
        s = re.sub(pat, rep, s)
    s = re.sub(r'\s+', ' ', s).strip(' .!,;')
    return s


def content_words(g):
    """Meaning-bearing words, ignoring any parenthetical aside."""
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', normalise(g))
    return {w for w in re.findall(r"[a-z']+", s) if w not in STOP and len(w) > 1}


def resolve(entries, max_senses=2, prefer_detail=False):
    """entries: [(priority, gloss)] with lower priority = better source.

    Returns (front, extras) — the card front, and the glosses that were displaced.
    """
    seen, ordered = set(), []
    for pri, g in sorted(entries, key=lambda e: e[0]):
        g = (g or '').strip()
        if not g:
            continue
        key = normalise(g)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append((pri, g))
    if not ordered:
        return '', []

    if prefer_detail:
        # among the best-sourced glosses, the one carrying a register or usage cue wins
        best = min(p for p, _ in ordered)
        tier = [g for p, g in ordered if p == best]
        primary = max(tier, key=lambda g: (('(' in g), len(g)))
    else:
        primary = ordered[0][1]

    front, extras = [primary], []
    base = content_words(primary)
    # A gloss that already carries a usage cue is the curated one; piling synonyms after it
    # only lengthens the prompt. "you (formal / plural — the safe default)" needs no help.
    settled = '(' in primary
    for _, g in ordered:
        if g == primary:
            continue
        cw = content_words(g)
        distinct = bool(cw) and not (cw & base)   # no content words at all => a rewording
        if distinct and not settled and len(front) < max_senses:
            front.append(g)
            base |= cw
        else:
            extras.append(g)
    return '; '.join(front), extras
