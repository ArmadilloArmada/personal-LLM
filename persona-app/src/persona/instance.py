"""Single-instance lock and persisted server URL for Persona."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

MUTEX_NAME = "Global\\Persona.SingleInstance.v1"
INSTANCE_FILE = "instance.json"


def persona_data_dir() -> Path:
    path = Path.home() / ".persona"
    path.mkdir(parents=True, exist_ok=True)
    return path


def instance_file() -> Path:
    return persona_data_dir() / INSTANCE_FILE


def write_instance(url: str, port: int, pid: int | None = None) -> None:
    payload = {
        "url": url,
        "port": port,
        "pid": pid or _current_pid(),
        "updated_at": time.time(),
    }
    instance_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_instance() -> dict | None:
    path = instance_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_saved_url() -> str | None:
    data = read_instance()
    if not data:
        return None
    url = data.get("url")
    port = data.get("port")
    if url:
        return str(url)
    if port:
        return f"http://127.0.0.1:{int(port)}"
    return None


def is_server_up(url: str, timeout: float = 1.5) -> bool:
    try:
        return httpx.get(f"{url.rstrip('/')}/api/health", timeout=timeout).status_code == 200
    except Exception:
        return False


def _current_pid() -> int:
    import os

    return os.getpid()


def try_acquire_primary_instance() -> bool:
    """Return True when this process should start Persona; False when another instance is active."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            if handle:
                kernel32.CloseHandle(handle)
            return False
        return True
    except Exception:
        return True


def handle_secondary_launch() -> bool:
    """If another Persona is running, open it and return True (caller should exit)."""
    from persona.browser import open_persona_ui

    saved = read_saved_url()
    if saved and is_server_up(saved):
        open_persona_ui(saved)
        return True
    return False
