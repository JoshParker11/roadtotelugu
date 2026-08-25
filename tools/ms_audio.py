# -*- coding: utf-8 -*-
"""Generate Telugu TTS audio for the Mini Stories, one file per segment, via Azure Neural TTS.

    export AZURE_SPEECH_KEY=...
    export AZURE_SPEECH_REGION=...        # e.g. eastus — must match the resource's region
    python3 tools/ms_audio.py --probe               # one segment, print status, write nothing else
    python3 tools/ms_audio.py --num 1                # a whole story
    python3 tools/ms_audio.py --num 1 --voice mohan   # male voice instead of the default female
    python3 tools/ms_audio.py --estimate              # character/cost estimate, no audio generated

WHY AZURE, AND WHY THESE PARTICULAR VOICES
See ministories/DECISIONS.md #8. Short version: te-IN-ShrutiNeural and te-IN-MohanNeural are
purpose-built Telugu voices trained on native Telangana/Andhra Pradesh speaker recordings, not a
general multilingual model doing its best on a language it wasn't specifically tuned for. That
distinction matters more here than usual — you cannot yet judge Telugu pronunciation by ear, so
"purpose-built and GA" beats "impressive but unverified for this language."

ONE FILE PER SEGMENT, KEYED BY GUID
Matches every other artefact in this project. ministories/audio/<guid>.mp3 lines up with the same
guid in work/*.tsv, so a segment's English, Telugu, romanization and audio are always one lookup
apart. It also means a single mispronounced sentence costs one re-generated file, not a whole
lesson re-recorded — and the same files are directly reusable as Anki audio clips later without
re-cutting anything.

RE-RUNNING MUST NEVER RE-SPEND MONEY
Existing files are never regenerated. This is the same rule as everywhere else in this project,
restated for a resource that costs real money instead of just work: skip anything already on
disk, and say so, rather than silently re-billing 2,805 segments because the script was re-run.
--force is required to regenerate a specific file (e.g. after a translation correction).

WHY SSML AND NOT PLAIN TEXT
A bare string sent to the REST API gets Azure's default rate and pausing, which reads noticeably
faster than is comfortable for a beginner. SSML's <prosody rate="..."> slows it down; this matters
more here than in a general-purpose TTS use because the whole point of the Mini Stories is being
able to actually hear the story/retell/question structure, not just have it technically spoken.
"""
import argparse
import csv
import glob
import os
import sys
import time
import urllib.error
import urllib.request
import xml.sax.saxutils as sx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MS = os.path.join(ROOT, 'ministories')
WORK = os.path.join(MS, 'work')
AUDIO = os.path.join(MS, 'audio')
CATALOG = os.path.join(MS, 'CATALOG.tsv')

VOICES = {'shruti': 'te-IN-ShrutiNeural', 'mohan': 'te-IN-MohanNeural'}
RATE = '-12%'          # slower than default; beginner-paced, not audiobook-paced
PAUSE = 0.1             # seconds between requests


def creds():
    key = os.environ.get('AZURE_SPEECH_KEY', '').strip()
    region = os.environ.get('AZURE_SPEECH_REGION', '').strip()
    if not key or not region:
        sys.exit(
            'AZURE_SPEECH_KEY and/or AZURE_SPEECH_REGION is not set.\n'
            '  1. portal.azure.com -> create a "Speech" resource (free tier available)\n'
            '  2. copy KEY 1 and the Location/Region from its "Keys and Endpoint" page\n'
            '  3. export AZURE_SPEECH_KEY=...\n'
            '     export AZURE_SPEECH_REGION=...   (e.g. eastus, centralindia)\n'
            'Read from the environment only, never written to disk.')
    return key, region


def rows_for(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def token(key, region):
    req = urllib.request.Request(
        f'https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken',
        data=b'', headers={'Ocp-Apim-Subscription-Key': key})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code} getting an auth token — check the key and region match the '
                 f'same Azure resource.\n{e.read().decode("utf-8","replace")[:300]}')


def synthesize(text, voice, tok, region):
    ssml = (
        '<speak version="1.0" xml:lang="te-IN">'
        f'<voice name="{voice}">'
        f'<prosody rate="{RATE}">{sx.escape(text)}</prosody>'
        '</voice></speak>'
    )
    req = urllib.request.Request(
        f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
        data=ssml.encode('utf-8'),
        headers={
            'Authorization': f'Bearer {tok}',
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-24khz-96kbitrate-mono-mp3',
            'User-Agent': 'roadtotelugu/ministories (personal study)',
        })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code} synthesizing audio.\n'
                 f'{e.read().decode("utf-8","replace")[:300]}')


def segments(num=None):
    cat = {r['id']: r for r in rows_for(CATALOG)}
    out = []
    for path in sorted(glob.glob(os.path.join(WORK, '*.tsv'))):
        sid = os.path.basename(path)[:-4]
        if num and int(cat[sid]['num']) != int(num):
            continue
        for r in rows_for(path):
            if r['te'].strip():
                out.append(r)
    return out


def word_segments():
    """One row per distinct word, from the manifest build_ms_reader.py writes.

    The reader plays audio/words/<guid>.mp3 when a headword's speaker icon is clicked —
    LingQ's per-word pronunciation, matched as behaviour but implemented as precomputed clips
    (DECISIONS.md #8's own audio path) rather than a live third-party call from the browser.
    Same guid scheme as everything else; the guids here are word guids (ids.guid('W', script)),
    not segment guids, so the files land in their own subdirectory.
    """
    manifest = os.path.join(MS, 'word_audio.tsv')
    if not os.path.exists(manifest):
        sys.exit('No word manifest yet — run: python3 tools/build_ms_reader.py')
    return rows_for(manifest)


def estimate(num):
    segs = segments(num)
    pending = [r for r in segs if not os.path.exists(os.path.join(AUDIO, r['guid'] + '.mp3'))]
    new_chars = sum(len(r['te']) for r in pending)
    print(f'{len(segs)} translated segment(s), {len(segs) - len(pending)} already have audio, '
          f'{len(pending)} to generate')
    print(f'{new_chars} Telugu characters still to synthesize')
    print('Check current Azure Speech pricing/free-tier limits in the portal before a large run — '
         'this script does not know your tier.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--num', help='only this story number')
    ap.add_argument('--probe', action='store_true', help='one segment, verbose, write nothing')
    ap.add_argument('--estimate', action='store_true', help='character count only, no audio')
    ap.add_argument('--voice', choices=VOICES, default='shruti')
    ap.add_argument('--force', action='store_true', help='regenerate files that already exist')
    ap.add_argument('--words', action='store_true',
                    help='per-word pronunciation clips from ministories/word_audio.tsv '
                         'instead of sentence segments')
    args = ap.parse_args()

    out_dir = os.path.join(AUDIO, 'words') if args.words else AUDIO

    if args.estimate:
        if args.words:
            rows = word_segments()
            pending = [r for r in rows
                       if not os.path.exists(os.path.join(out_dir, r['guid'] + '.mp3'))]
            print(f'{len(rows)} distinct words, {len(rows) - len(pending)} already have clips, '
                  f'{len(pending)} to generate '
                  f'({sum(len(r["te"]) for r in pending)} characters)')
            return
        return estimate(args.num)

    segs = word_segments() if args.words else segments(args.num)
    if not segs:
        print('No translated segments found for that scope.')
        return
    os.makedirs(out_dir, exist_ok=True)
    key, region = creds()
    voice = VOICES[args.voice]

    if args.probe:
        r = segs[0]
        print(f'voice: {voice}   rate: {RATE}')
        print(f'segment: {r["guid"]}  {r["te"]}')
        tok = token(key, region)
        audio = synthesize(r['te'], voice, tok, region)
        print(f'received {len(audio)} bytes of audio. Nothing written — remove --probe to save.')
        return

    tok, minted = token(key, region), time.time()
    made = skipped = 0
    for i, r in enumerate(segs, 1):
        path = os.path.join(out_dir, r['guid'] + '.mp3')
        if os.path.exists(path) and not args.force:
            skipped += 1
            continue
        if time.time() - minted > 540:            # tokens expire at 10 min; refresh at 9
            tok, minted = token(key, region), time.time()
        audio = synthesize(r['te'], voice, tok, region)
        with open(path, 'wb') as f:
            f.write(audio)
        made += 1
        print(f'{i:>4}/{len(segs)} {r["guid"]}  {r["te"][:40]}')
        time.sleep(PAUSE)
    print(f'\ngenerated {made}, skipped {skipped} already on disk')


if __name__ == '__main__':
    main()
