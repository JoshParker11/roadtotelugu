# -*- coding: utf-8 -*-
"""Static server for the site, with HTTP Range support.

    python3 tools/serve.py          # http://localhost:8123
    python3 tools/serve.py 9000

WHY NOT `python3 -m http.server`
Because it answers a Range request with `200` and the whole file. For everything else here
that is merely wasteful; for the reader's audio it breaks the feature outright. The podcast is
105 MB, and seeking to 42:10 in a file the browser cannot request a byte range of means
downloading all of it first. With Range, the browser fetches a few hundred KB around the seek
point and plays immediately.

Opening the site as file:// also works — Chrome seeks local files fine — but then anything
using fetch() is blocked by CORS, so this is the better default.
"""
import os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RANGE = re.compile(r'bytes=(\d*)-(\d*)')


class RangeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        # A dev server that lets the browser cache is a trap: re-run build_reader.py, reload,
        # and the page quietly keeps serving the previous bake. Audio is exempt — caching a
        # 105 MB file across seeks is the entire point of Range support.
        if not self.path.lower().endswith(('.mp3', '.m4a', '.ogg', '.wav')):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_head(self):
        hdr = self.headers.get('Range')
        if not hdr:
            return super().send_head()
        m = RANGE.match(hdr.strip())
        path = self.translate_path(self.path)
        if not m or not os.path.isfile(path):
            return super().send_head()

        size = os.path.getsize(path)
        first, last = m.group(1), m.group(2)
        if first == '':                       # suffix form: bytes=-500
            start, end = max(0, size - int(last or 0)), size - 1
        else:
            start = int(first)
            end = int(last) if last else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return None

        f = open(path, 'rb')
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        # SimpleHTTPRequestHandler copies to EOF, so hand it only the requested slice.
        return _Slice(f, end - start + 1)

    def log_message(self, fmt, *args):
        if '404' in (args[1] if len(args) > 1 else ''):
            super().log_message(fmt, *args)


class _Slice:
    """A read-only view of `n` bytes from an already-positioned file."""
    def __init__(self, f, n):
        self.f, self.left = f, n

    def read(self, size=-1):
        if self.left <= 0:
            return b''
        if size is None or size < 0:
            size = self.left
        data = self.f.read(min(size, self.left))
        self.left -= len(data)
        return data

    def close(self):
        self.f.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    print(f'serving {ROOT} on http://localhost:{port}  (Range enabled)')
    ThreadingHTTPServer(('127.0.0.1', port), RangeHandler).serve_forever()
