"""Local dev server: `python tools/serve.py` then open http://localhost:8000

Plain `python -m http.server` can serve .js as text/plain on Windows (it reads the registry),
and browsers refuse to run ES modules with that type. This forces the right one.
"""
import http.server
import mimetypes
import os

mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/javascript', '.mjs')


class NoCache(http.server.SimpleHTTPRequestHandler):
    """Never cache during development, so a refresh always picks up edited files and re-exported PNGs."""
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
http.server.test(HandlerClass=NoCache, port=8000, bind='127.0.0.1')
