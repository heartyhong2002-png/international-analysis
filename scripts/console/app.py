"""
Local unified pipeline console (prototype).
==========================================

Wraps scripts/run_pipeline.py (and a light collector lane) behind a tiny
stdlib HTTP server + HTML home. No Flask/React. Not for public deploy.

Usage:
    .\\.venv\\Scripts\\python.exe scripts/console/app.py
    # open http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8765

CONSOLE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CONSOLE_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parent
STATIC_DIR = CONSOLE_DIR / "static"
LOG_DIR = REPO_ROOT / "logs"
DASHBOARD_INDEX = REPO_ROOT / "output" / "dashboard" / "index.html"

PYTHON = sys.executable

LIGHT_SCRIPTS = [
    ("government RSS", SCRIPTS_DIR / "collection" / "gov_announcements_collector.py", []),
    ("White House RSS", SCRIPTS_DIR / "collection" / "fetch_whitehouse_official.py", []),
    ("signal-gap RSS", SCRIPTS_DIR / "collection" / "fetch_signal_gap_rss.py", []),
    ("financial proxy", SCRIPTS_DIR / "collection" / "fetch_financial_proxy.py", []),
]

PRESETS = {
    "default": {
        "label": "수집 + DB + 대시보드",
        "desc": "run_pipeline.py --skip-trends (LLM/Ollama 제외)",
    },
    "collect-only": {
        "label": "수집만",
        "desc": "run_pipeline.py --collect-only --skip-trends",
    },
    "light": {
        "label": "Light RSS",
        "desc": "gov / White House / signal-gap / financial (Actions light lane)",
    },
}

_state_lock = threading.Lock()
_state: dict[str, Any] = {
    "running": False,
    "preset": None,
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "log_path": None,
    "error": None,
}
_worker: subprocess.Popen[str] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _py(script: Path, *args: str) -> list[str]:
    # -X utf8 avoids Windows cp949 UnicodeEncodeError in collector prints.
    return [PYTHON, "-X", "utf8", str(script), *args]


def _build_commands(preset: str) -> list[list[str]]:
    if preset == "default":
        return [_py(SCRIPTS_DIR / "run_pipeline.py", "--skip-trends")]
    if preset == "collect-only":
        return [_py(SCRIPTS_DIR / "run_pipeline.py", "--collect-only", "--skip-trends")]
    if preset == "light":
        return [_py(path, *args) for _name, path, args in LIGHT_SCRIPTS]
    raise ValueError(f"unknown preset: {preset}")


def _append_log(log_path: Path, text: str) -> None:
    with log_path.open("a", encoding="utf-8", errors="replace") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    # Windows consoles often default to cp949; collectors print emoji/UTF-8.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run_pipeline_job(preset: str, log_path: Path) -> None:
    global _worker
    exit_code = 1
    try:
        cmds = _build_commands(preset)
        _append_log(log_path, f"[{_utc_now()}] START preset={preset}")
        _append_log(log_path, f"python={PYTHON}")
        _append_log(log_path, f"repo={REPO_ROOT}")

        for i, cmd in enumerate(cmds, start=1):
            _append_log(log_path, f"\n--- step {i}/{len(cmds)} ---")
            _append_log(log_path, " ".join(cmd))
            with log_path.open("a", encoding="utf-8", errors="replace") as log_fh:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(REPO_ROOT),
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=_child_env(),
                )
                with _state_lock:
                    _worker = proc
                code = proc.wait()
                with _state_lock:
                    _worker = None
                _append_log(log_path, f"[step {i}] exit={code}")
                if code != 0:
                    exit_code = code
                    _append_log(log_path, f"[{_utc_now()}] ABORT after step {i}")
                    break
        else:
            exit_code = 0
            _append_log(log_path, f"[{_utc_now()}] DONE ok")
    except Exception as exc:  # noqa: BLE001 — surface to UI status
        exit_code = 1
        _append_log(log_path, f"[{_utc_now()}] ERROR {type(exc).__name__}: {exc}")
        with _state_lock:
            _state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        with _state_lock:
            _state["running"] = False
            _state["finished_at"] = _utc_now()
            _state["exit_code"] = exit_code
            _worker = None


def _start_job(preset: str) -> dict[str, Any]:
    if preset not in PRESETS:
        return {"ok": False, "error": f"unknown preset: {preset}"}

    with _state_lock:
        if _state["running"]:
            return {"ok": False, "error": "pipeline already running", "status": _public_status()}
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / f"console_pipeline_{_stamp()}.log"
        _state.update(
            {
                "running": True,
                "preset": preset,
                "started_at": _utc_now(),
                "finished_at": None,
                "exit_code": None,
                "log_path": str(log_path),
                "error": None,
            }
        )

    thread = threading.Thread(
        target=_run_pipeline_job,
        args=(preset, log_path),
        name=f"console-pipeline-{preset}",
        daemon=True,
    )
    thread.start()
    return {"ok": True, "status": _public_status()}


def _tail_log(max_chars: int = 12000) -> str:
    path = _state.get("log_path")
    if not path:
        return ""
    log_path = Path(path)
    if not log_path.is_file():
        return ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _public_status() -> dict[str, Any]:
    with _state_lock:
        snapshot = dict(_state)
    snapshot["log_tail"] = _tail_log()
    snapshot["dashboard_exists"] = DASHBOARD_INDEX.is_file()
    snapshot["presets"] = PRESETS
    return snapshot


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "EarlyWarningConsole/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            index = STATIC_DIR / "index.html"
            if not index.is_file():
                self._send(404, b"index.html missing", "text/plain; charset=utf-8")
                return
            body = index.read_bytes()
            self._send(200, body, "text/html; charset=utf-8")
            return

        if path == "/api/status":
            self._send_json(200, _public_status())
            return

        if path == "/dashboard" or path.startswith("/dashboard/"):
            if not DASHBOARD_INDEX.is_file():
                msg = (
                    "<!doctype html><meta charset=utf-8>"
                    "<title>Dashboard</title>"
                    "<p>대시보드가 아직 없습니다. 콘솔에서 "
                    "<b>수집 + DB + 대시보드</b> 프리셋으로 한 번 실행하세요.</p>"
                    "<p><a href='/'>← 콘솔로</a></p>"
                ).encode("utf-8")
                self._send(404, msg, "text/html; charset=utf-8")
                return
            if path in ("/dashboard", "/dashboard/"):
                self.send_response(302)
                self.send_header("Location", "/dashboard/index.html")
                self.end_headers()
                return
            rel = path[len("/dashboard/") :]
            target = (REPO_ROOT / "output" / "dashboard" / rel).resolve()
            dash_root = (REPO_ROOT / "output" / "dashboard").resolve()
            if not str(target).startswith(str(dash_root)) or not target.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            data = target.read_bytes()
            ctype = "text/html; charset=utf-8"
            if target.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif target.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            elif target.suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
                ctype = f"image/{target.suffix.lstrip('.')}"
            self._send(200, data, ctype)
            return

        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (STATIC_DIR / rel).resolve()
            if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            data = target.read_bytes()
            ctype = "text/plain; charset=utf-8"
            if target.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif target.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            self._send(200, data, ctype)
            return

        self._send(404, b"not found", "text/plain; charset=utf-8")

    def _same_origin_ok(self) -> bool:
        """Reject cross-site POSTs that browsers still send to loopback."""
        expected = {f"http://{HOST}:{PORT}", f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
        origin = (self.headers.get("Origin") or "").rstrip("/")
        referer = self.headers.get("Referer") or ""
        if origin:
            return origin in expected
        if referer:
            return any(referer.startswith(base + "/") or referer.rstrip("/") == base for base in expected)
        # No Origin/Referer (non-browser clients): require explicit local console header
        return (self.headers.get("X-Console-Local") or "") == "1"

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/run":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype and ctype != "application/json":
            self._send_json(415, {"ok": False, "error": "Content-Type must be application/json"})
            return
        if not self._same_origin_ok():
            self._send_json(403, {"ok": False, "error": "cross-origin POST blocked"})
            return
        body = self._read_json()
        if "preset" not in body:
            self._send_json(400, {"ok": False, "error": "JSON body with preset is required"})
            return
        preset = str(body.get("preset") or "").strip()
        if not preset:
            self._send_json(400, {"ok": False, "error": "preset must be non-empty"})
            return
        result = _start_job(preset)
        code = 200 if result.get("ok") else 409
        self._send_json(code, result)


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer((HOST, PORT), ConsoleHandler)
    print("=" * 60)
    print("Early-warning local console")
    print(f"  URL : http://{HOST}:{PORT}/")
    print(f"  Repo: {REPO_ROOT}")
    print(f"  Py  : {PYTHON}")
    print("  Ctrl+C to stop")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
