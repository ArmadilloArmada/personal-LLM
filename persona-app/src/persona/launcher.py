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

from persona.browser import open_persona_ui
from persona.config import Settings, get_settings
from persona.dialogs import show_browser_missing, show_startup_failure
from persona.instance import handle_secondary_launch, try_acquire_primary_instance, write_instance
from persona.providers import resolve_provider_mode


def _persona_log_dir() -> Path:
    path = Path.home() / ".persona"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_startup(message: str) -> None:
    if not getattr(sys, "frozen", False):
        return
    log_path = _persona_log_dir() / "startup.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%H:%M:%S')} {message}\n")


def _log_error(exc: BaseException) -> None:
    path = _persona_log_dir() / "error.log"
    path.write_text(traceback.format_exc(), encoding="utf-8")


def find_free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 45.0) -> bool:
    url = f"http://{host}:{port}/api/health"
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
    import uvicorn

    try:
        _log_startup("uvicorn: importing app")
        from persona.web.server import app as fastapi_app

        if getattr(sys, "frozen", False):
            static = Path(sys._MEIPASS) / "persona" / "web" / "static"
            _log_startup(f"uvicorn: static exists={static.exists()}")

        _log_startup(f"uvicorn: starting on {host}:{port}")
        uvicorn.run(
            fastapi_app,
            host=host,
            port=port,
            log_level="warning",
            log_config=None,
            access_log=False,
            http="h11",
        )
        _log_startup("uvicorn: exited")
    except Exception:
        _log_error(RuntimeError("uvicorn failed"))
        _log_startup("uvicorn: failed (see error.log)")
        raise


def _shutdown() -> None:
    try:
        from persona.bundled import stop_bundled_server

        stop_bundled_server()
    except Exception:
        pass
    try:
        from persona.big_brain.process import stop_brain_server

        stop_brain_server()
    except Exception:
        pass


def run_standalone(*, window: bool = False, port: int | None = None) -> None:
    """Launch Persona — opens browser after the local server is ready."""
    _log_startup("launcher: begin")
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).parent)

    if window and getattr(sys, "frozen", False):
        if not try_acquire_primary_instance():
            _log_startup("launcher: another instance detected")
            if handle_secondary_launch():
                _log_startup("launcher: focused existing instance")
                return
            _log_startup("launcher: stale instance lock, continuing startup")

    settings = get_settings()
    host = "127.0.0.1"
    if port is None:
        env_port = os.environ.get("PERSONA_WEB_PORT")
        port = int(env_port) if env_port else find_free_port(settings.web_port)
    provider = resolve_provider_mode(settings)

    if provider == "bundled":
        from persona.bundled import start_bundled_server

        _log_startup("launcher: starting bundled llama-server")
        if not start_bundled_server(settings):
            _log_startup("launcher: bundled server failed — falling back to demo")
            provider = "demo"
            os.environ["PERSONA_PROVIDER"] = "demo"

    os.environ["PERSONA_PROVIDER"] = provider
    os.environ["PERSONA_WEB_PORT"] = str(port)
    _log_startup(f"launcher: provider={provider} port={port}")

    url = f"http://{host}:{port}"

    if window:
        server = threading.Thread(target=_run_uvicorn, args=(host, port), daemon=True)
        server.start()
        _log_startup("launcher: waiting for server (window mode)")
        if not wait_for_server(host, port):
            health_url = f"http://{host}:{port}/api/health"
            _log_startup("launcher: server did not respond in time")
            _persona_log_dir().joinpath("error.log").write_text(
                f"Server did not respond within 45s at {health_url}\n"
                "If /api/health works in a browser but the app still fails, check startup.log.",
                encoding="utf-8",
            )
            if getattr(sys, "frozen", False):
                show_startup_failure(health_url)
                sys.exit(1)
            print("Persona failed to start.", file=sys.stderr)
            sys.exit(1)
        write_instance(url, port)
        _log_startup("launcher: opening app window")
        _open_window(url)
        return

    threading.Thread(
        target=lambda: wait_for_server(host, port) and webbrowser.open(url),
        daemon=True,
    ).start()

    if not getattr(sys, "frozen", False):
        _print_banner(url, provider)

    try:
        _run_uvicorn(host, port)
    finally:
        _shutdown()


def _open_window(url: str) -> None:
    """Open Persona in a native window — pywebview in dev, Edge app mode in frozen builds."""
    if getattr(sys, "frozen", False):
        _log_startup("launcher: frozen build — using Edge/Chrome app window")
        if open_persona_ui(url):
            _log_startup("launcher: opened Edge/Chrome app window")
            _run_tray_loop(url)
            return
        _log_startup("launcher: browser app mode failed")
        show_browser_missing(url)
        _run_tray_loop(url)
        return

    try:
        import webview

        _log_startup("launcher: starting pywebview")
        webview.create_window("Persona", url, width=1280, height=860, min_size=(900, 600))
        if sys.platform == "win32":
            webview.start(gui="edgechromium")
        else:
            webview.start()
        return
    except Exception as exc:
        _log_startup(f"launcher: pywebview failed: {exc}")

    if open_persona_ui(url):
        _log_startup("launcher: opened Edge/Chrome app window")
        _run_tray_loop(url)
        return

    _log_startup("launcher: falling back to default browser")
    webbrowser.open(url)
    _run_tray_loop(url)


def _run_tray_loop(url: str) -> None:
    from persona.tray import run_tray

    run_tray(url, on_quit=_shutdown)


def _print_banner(url: str, provider: str) -> None:
    mode = {
        "demo": "Demo",
        "bundled": "Built-in AI",
        "ollama": "Ollama",
        "openai": "Cloud API",
    }.get(provider, provider)
    print(f"\n  Persona running at {url} ({mode})\n  Press Ctrl+C to quit\n")


def main() -> None:
    run_standalone()
