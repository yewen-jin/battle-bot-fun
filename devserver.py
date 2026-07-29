#!/usr/bin/env python3
"""Static file server that never caches -- for local dev only.

python's built-in http.server sends Last-Modified but no Cache-Control,
which lets browsers apply heuristic caching and silently serve stale JS/
images across ordinary reloads. This adds `Cache-Control: no-store` to
every response so edits always show up on refresh, no query-string
versioning or hard-refresh reminders needed.

Usage: python3 devserver.py [port]   (default port 8000)
"""

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    HTTPServer(("", port), NoCacheHandler).serve_forever()
