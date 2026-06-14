"""Local web server for the CADCopilot browser panel. Serves the chat UI and a
streaming /api/chat endpoint (newline-delimited JSON events) that runs the Claude
agent loop against the CAD tools."""

from __future__ import annotations

import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("CAD_PANEL_PORT", "8750"))


class Handler(BaseHTTPRequestHandler):
    def _head(self, code: int, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._head(200, "text/html; charset=utf-8")
            self.wfile.write((HERE / "index.html").read_bytes())
        else:
            self._head(404, "text/plain")
            self.wfile.write(b"not found")

    def do_POST(self):  # noqa: N802
        from ..agent import get_agent
        agent = get_agent()
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")

        if self.path == "/api/reset":
            agent.reset()
            self._head(200, "application/json")
            self.wfile.write(b'{"ok":true}')
            return

        if self.path == "/api/chat":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def emit(ev: dict) -> None:
                try:
                    self.wfile.write((json.dumps(ev) + "\n").encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionError):
                    pass

            try:
                agent.run_turn(body.get("message", ""), emit)
            except Exception as e:  # noqa: BLE001 - report to the browser
                emit({"type": "error", "text": str(e)})
                emit({"type": "done"})
            return

        self._head(404, "text/plain")
        self.wfile.write(b"not found")

    def log_message(self, *args):  # silence stdout
        pass


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    backend = os.environ.get("CAD_BACKEND", "inventor")
    agent = os.environ.get("CAD_AGENT", "ollama")
    model = os.environ.get("CAD_OLLAMA_MODEL", "qwen2.5:14b-instruct") if agent == "ollama" \
        else os.environ.get("CAD_CLAUDE_MODEL", "claude-opus-4-8")
    print(f"CADCopilot panel running at {url}  (CAD={backend}, agent={agent}, model={model})")
    if agent == "ollama":
        print("Local & free. Make sure Inventor is open and the Ollama app is running.")
    else:
        print("Make sure Inventor is open and ANTHROPIC_API_KEY is set.")
    if not os.environ.get("CAD_PANEL_NO_BROWSER"):   # the in-Inventor add-in sets this to skip the extra tab
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
