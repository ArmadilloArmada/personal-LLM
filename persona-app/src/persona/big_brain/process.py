"""Start/stop Big Brain Node API as a child process."""

from __future__ import annotations

import atexit
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from persona.big_brain.paths import brain_server_entry, persona_data_dir

_log = logging.getLogger(__name__)
_process: subprocess.Popen | None = None
_brain_log: Path | None = None


def _brain_log_path() -> Path:
    global _brain_log
    if _brain_log is None:
        _brain_log = persona_data_dir() / "brain.log"
    return _brain_log


def _find_node() -> str | None:
    env = os.environ.get("BIG_BRAIN_NODE")
    if env and Path(env).exists():
        return env
    if getattr(sys, "frozen", False):
        for candidate in (
            Path(sys.executable).parent / "node" / "node.exe",
            Path(sys.executable).parent / "node.exe",
        ):
            if candidate.exists():
                return str(candidate)
    return shutil.which("node")


def ensure_brain_server(port: int = 3002) -> bool:
    """Start Brain API if not already running. Returns True if available."""
    global _process
    from persona.big_brain.client import is_brain_available

    if is_brain_available():
        return True

    entry = brain_server_entry()
    node = _find_node()
    if not entry or not node:
        _log.warning("Big Brain server entry or node not found")
        return False

    data = persona_data_dir()
    env = os.environ.copy()
    env.setdefault("PORT", str(port))
    env.setdefault("HOST", "127.0.0.1")
    env.setdefault("VAULT_PATH", str(data / "vault"))
    env.setdefault("DB_PATH", str(data / "big-brain.db"))
    env.setdefault("PERSONA_API_URL", os.environ.get("PERSONA_API_URL", "http://127.0.0.1:8765"))
    if getattr(sys, "frozen", False) and not env.get("BIG_BRAIN_CAPTURE_SECRET"):
        secret_path = data / ".brain-secret"
        if secret_path.exists():
            env["BIG_BRAIN_CAPTURE_SECRET"] = secret_path.read_text(encoding="utf-8").strip()
        else:
            import secrets

            secret = secrets.token_hex(16)
            secret_path.write_text(secret, encoding="utf-8")
            env["BIG_BRAIN_CAPTURE_SECRET"] = secret

    log_path = _brain_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    log_file.write(f"\n--- Big Brain start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_file.flush()

    _process = subprocess.Popen(
        [node, str(entry)],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(entry.parent),
    )
    atexit.register(stop_brain_server)

    deadline = time.time() + 20
    while time.time() < deadline:
        if is_brain_available():
            _log.info("Big Brain API ready on port %s", port)
            return True
        if _process.poll() is not None:
            _log.error("Big Brain process exited early (see %s)", log_path)
            return False
        time.sleep(0.3)
    return False


def stop_brain_server() -> None:
    global _process
    try:
        from persona.big_brain.client import flush_session_capture

        flush_session_capture()
    except Exception as exc:
        _log.debug("session-end flush skipped: %s", exc)
    if _process and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
    _process = None
