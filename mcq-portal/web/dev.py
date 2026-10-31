#!/usr/bin/env python3
"""Local stand-in for the Vercel setup: serves this folder and forwards /api/* to the Django API, so the browser sees ONE
origin (as in production, where vercel.json rewrites /api/* to the API host).

  python3 web/dev.py [--port 5174] [--api http://127.0.0.1:8010]
"""
import argparse
import mimetypes
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "proxy-authorization", "proxy-authenticate", "content-length", "content-encoding"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class H(BaseHTTPRequestHandler):
    api = "http://127.0.0.1:8010"

    def log_message(self, *a):
        pass

    def proxy(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        req = urllib.request.Request(self.api + self.path, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in HOP | {"host", "accept-encoding"}:
                req.add_header(k, v)
        req.add_header("Host", self.headers.get("Host", ""))  # Django's CSRF check compares Origin with Host
        try:
            r = urllib.request.build_opener(NoRedirect).open(req, timeout=120)
        except urllib.error.HTTPError as e:
            r = e
        except OSError as e:
            msg = f'{{"error":{{"code":"bad_gateway","message":"API not reachable: {e}"}}}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            return self.wfile.write(msg)
        data = r.read()
        self.send_response(r.status if hasattr(r, "status") else r.code)
        for k, v in r.headers.items():
            if k.lower() not in HOP:
                self.send_header(k, v)  # includes every Set-Cookie
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def static(self):
        rel = self.path.split("?")[0].lstrip("/") or "index.html"
        p = (WEB / rel).resolve()
        if WEB not in p.parents or not p.is_file() or p.name == "dev.py":
            return self.send_error(404)
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        body = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or "javascript" in ctype else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def handle_any(self):
        if self.path.startswith("/api/"):
            return self.proxy()
        if self.command in ("GET", "HEAD"):
            return self.static()
        self.send_error(405)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = handle_any


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5174)
    ap.add_argument("--api", default="http://127.0.0.1:8010")
    a = ap.parse_args()
    H.api = a.api.rstrip("/")
    print(f"Ghatnachakra on http://127.0.0.1:{a.port}  (API -> {H.api})")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
