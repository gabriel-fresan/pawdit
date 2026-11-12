import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from pawdit.config import DEFAULTS


class FakeOllama:
    """Minimal /api/chat + /api/tags server. `responder(body) -> str | (status, str)`."""

    def __init__(self):
        self.requests = []
        self.responder = lambda body: "ok"
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj, status=200):
                b = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                self._send({"models": [{"name": "fake:1b"}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                res = outer.responder(body)
                if isinstance(res, tuple):
                    self._send({"error": res[1]}, res[0])
                else:
                    self._send({"message": {"role": "assistant", "content": res}})

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def ollama():
    srv = FakeOllama()
    yield srv
    srv.close()


@pytest.fixture
def cfg(tmp_path, ollama):
    return dict(
        DEFAULTS,
        state_dir=str(tmp_path / "state"),
        state_group=None,
        ollama_url=ollama.url,
        model="fake:1b",
        ai_timeout=10,
    )
