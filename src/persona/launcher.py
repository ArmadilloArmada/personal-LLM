"""Standalone app launcher — one command, no setup."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

import httpx
import uvicorn

from persona.config import Settings, get_settings


def _log_error(exc: BaseException) -> None:
    log_dir = Path.home() / ".persona"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "error.log"
    path.write_text(traceback.format_exc(), encoding="utf-8")


def ollama_available(settings: Settings) -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def resolve_provider_mode(settings: Settings) -> str:
    mode = (settings.provider or "auto").lower()
    if mode == "demo":
        return "demo"
    if mode == "openai":
        return "openai" if settings.openai_api_key else "demo"
    if mode == "ollama":
        if ollama_available(settings):
            return "ollama"
        return "openai" if settings.openai_api_key else "demo"
    if ollama_available(settings):
        return "ollama"
    if settings.openai_api_key:
        return "openai"
    return "demo"


def find_free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 50):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 30.0) -> bool:
    url = f"http://{host}:{port}/api/status"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=1.0).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _create_uvicorn_app():
    from persona.web.server import create_app

    return create_app()


def _open_browser_when_ready(host: str, port: int, url: str) -> None:
    if wait_for_server(host, port):
        webbrowser.open(url)


def run_standalone(*, window: bool = False, port: int | None = None) -> None:
    """Launch Persona — browser opens, server runs on main thread (Windows-safe)."""
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).parent)

    settings = get_settings()
    host = "127.0.0.1"
    if port is None:
        port = int(os.environ["PERSONA_WEB_PORT"]) if os.environ.get("PERSONA_WEB_PORT") else find_free_port(settings.web_port)
    provider = resolve_provider_mode(settings)

    os.environ["PERSONA_PROVIDER"] = provider
    os.environ["PERSONA_WEB_PORT"] = str(port)

    url = f"http://{host}:{port}"

    if window:
        try:
            import webview

            threading.Thread(
                target=lambda: (wait_for_server(host, port) and webview.create_window(
                    "Persona", url, width=1200, height=800
                )),
                daemon=True,
            ).start()
        except ImportError:
            threading.Thread(
                target=_open_browser_when_ready, args=(host, port, url), daemon=True
            ).start()
    else:
        threading.Thread(
            target=_open_browser_when_ready, args=(host, port, url), daemon=True
        ).start()

    if not getattr(sys, "frozen", False):
        _print_banner(url, provider)

    try:
        app = _create_uvicorn_app()
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except Exception as exc:
        _log_error(exc)
        raise


def _print_banner(url: str, provider: str) -> None:
    mode = {
        "demo": "Demo",
        "ollama": "Ollama",
        "openai": "Cloud API",
    }.get(provider, provider)
    print(f"\n  Persona running at {url} ({mode})\n  Press Ctrl+C to quit\n")


def main() -> None:
    run_standalone()
