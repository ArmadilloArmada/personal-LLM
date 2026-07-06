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


def _show_windows_error(message: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "Persona", 0x10)
    except Exception:
        pass


def ollama_available(settings: Settings) -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def resolve_provider_mode(settings: Settings) -> str:
    """Pick provider — frozen Windows builds default to demo for instant startup."""
    if getattr(sys, "frozen", False) and not os.environ.get("PERSONA_PROVIDER"):
        return "demo"

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
        time.sleep(0.2)
    return False


def _run_uvicorn(host: str, port: int) -> None:
    try:
        uvicorn.run(
            "persona.web.server:app",
            host=host,
            port=port,
            log_level="warning",
        )
    except Exception as exc:
        _log_error(exc)
        raise


def run_standalone(*, window: bool = False, port: int | None = None) -> None:
    """Launch Persona — opens browser after the local server is ready."""
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).parent)

    settings = get_settings()
    host = "127.0.0.1"
    if port is None:
        env_port = os.environ.get("PERSONA_WEB_PORT")
        port = int(env_port) if env_port else find_free_port(settings.web_port)
    provider = resolve_provider_mode(settings)

    os.environ["PERSONA_PROVIDER"] = provider
    os.environ["PERSONA_WEB_PORT"] = str(port)

    url = f"http://{host}:{port}"

    server = threading.Thread(target=_run_uvicorn, args=(host, port), daemon=True)
    server.start()

    if not wait_for_server(host, port):
        message = (
            "Persona could not start its local server.\n\n"
            f"Check %USERPROFILE%\\.persona\\error.log\n\n"
            "Make sure you unzipped the full folder and run Persona.exe inside it."
        )
        _log_error(RuntimeError(f"Server did not respond on {host}:{port}"))
        if getattr(sys, "frozen", False):
            _show_windows_error(message)
            sys.exit(1)
        print("Persona failed to start. Try: persona serve", file=sys.stderr)
        sys.exit(1)

    if window:
        _open_window(url, host, port)
    else:
        webbrowser.open(url)
        if not getattr(sys, "frozen", False):
            _print_banner(url, provider)

    try:
        while server.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        if not getattr(sys, "frozen", False):
            print("\nPersona closed.")


def _open_window(url: str, host: str, port: int) -> None:
    try:
        import webview

        webview.create_window("Persona", url, width=1200, height=800, min_size=(800, 600))
        webview.start()
    except ImportError:
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nPersona closed.")


def _print_banner(url: str, provider: str) -> None:
    mode = {
        "demo": "Demo",
        "ollama": "Ollama",
        "openai": "Cloud API",
    }.get(provider, provider)
    print(f"\n  Persona running at {url} ({mode})\n  Press Ctrl+C to quit\n")


def main() -> None:
    run_standalone()
