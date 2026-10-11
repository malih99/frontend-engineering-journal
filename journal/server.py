"""Tiny local server: static dashboard files plus a live-generated /data.json."""

from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from journal import export
from journal.config import Config


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, cfg: Config, **kwargs):
        self._cfg = cfg
        super().__init__(*args, directory=str(cfg.root / "dashboard"), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path.split("?")[0] == "/data.json":
            self._send_data()
        else:
            super().do_GET()

    def _send_data(self) -> None:
        from journal.cli import build_snapshot  # local import avoids a circular import

        snap, errors = build_snapshot(self._cfg)
        if errors:
            body = json.dumps({"error": errors}).encode()
            status = HTTPStatus.UNPROCESSABLE_ENTITY
        else:
            body, status = export.to_json(snap).encode(), HTTPStatus.OK
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # keep the terminal quiet


def serve(cfg: Config, port: int) -> int:
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(_Handler, cfg=cfg))
    print(f"Dashboard: http://127.0.0.1:{port}  (Ctrl+C to stop; refresh to re-read your files)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0
