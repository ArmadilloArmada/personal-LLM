"""Standalone app launcher — one command, no setup."""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser

import httpx
import uvicorn

from persona.config import Settings, get_settings


def ollama_available(settings: Settings) -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def resolve_provider_mode(settings: Settings) -> str:
    """Pick the best available provider: explicit > ollama > openai > demo."""
    mode = (settings.provider or "auto").lower()
    if mode == "demo":
        return "demo"
    if mode == "openai":
        return "openai" if settings.openai_api_key else "demo"
    if mode == "ollama":
        if ollama_available(settings):
            return "ollama"
        return "openai" if settings.openai_api_key else "demo"
    # auto
    if ollama_available(settings):
        return "ollama"
    if settings.openai_api_key:
        return "openai"
    return "demo"


def find_free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    url = f"http://{host}:{port}/api/status"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=1.0).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def run_standalone(*, window: bool = False, port: int | None = None) -> None:
    """Launch Persona as a standalone app — opens UI automatically."""
    settings = get_settings()
    host = "127.0.0.1"
    port = port or find_free_port(settings.web_port)
    provider = resolve_provider_mode(settings)

    # Ensure resolved provider is used by the server process
    import os

    os.environ["PERSONA_PROVIDER"] = provider
    os.environ["PERSONA_WEB_PORT"] = str(port)

    url = f"http://{host}:{port}"

    server = threading.Thread(
        target=lambda: uvicorn.run(
            "persona.web.server:app",
            host=host,
            port=port,
            log_level="warning",
        ),
        daemon=True,
    )
    server.start()

    if not wait_for_server(host, port):
        print("Persona failed to start. Try: persona serve", file=sys.stderr)
        sys.exit(1)

    if window:
        _open_window(url)
    else:
        webbrowser.open(url)
        _print_banner(url, provider)

    try:
        while server.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nPersona closed.")


def _open_window(url: str) -> None:
    try:
        import webview

        webview.create_window("Persona", url, width=1200, height=800, min_size=(800, 600))
        webview.start()
    except ImportError:
        webbrowser.open(url)
        _print_banner(url, "demo")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nPersona closed.")


def _print_banner(url: str, provider: str) -> None:
    mode = {
        "demo": "Demo (ready instantly — no AI install needed)",
        "ollama": "Ollama (local AI)",
        "openai": "Cloud API",
    }.get(provider, provider)

    print()
    print("  🎭  Persona is running!")
    print(f"  →   {url}")
    print(f"  →   Mode: {mode}")
    print("  →   Press Ctrl+C to quit")
    print()


def main() -> None:
    run_standalone()
