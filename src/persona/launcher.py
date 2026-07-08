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

from persona.config import Settings, get_settings
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


def _show_windows_error(message: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "Persona", 0x10)
    except Exception:
        pass


def _log_error(exc: BaseException | None = None) -> None:
    path = _persona_log_dir() / "error.log"
    if exc is not None:
        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        text = traceback.format_exc()
    path.write_text(text, encoding="utf-8")


def _configure_asyncio_for_windows() -> None:
    if sys.platform != "win32":
        return
    import asyncio

    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _can_bind_port(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def find_free_port(preferred: int = 8765, host: str = "127.0.0.1") -> int:
    for port in range(preferred, preferred + 50):
        if _can_bind_port(host, port):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 90.0) -> bool:
    """Wait until the local server responds — prefer lightweight /api/health."""
    paths = ("/api/health", "/api/status")
    deadline = time.time() + timeout
    while time.time() < deadline:
        for path in paths:
            url = f"http://{host}:{port}{path}"
            try:
                if httpx.get(url, timeout=1.5).status_code == 200:
                    return True
            except Exception:
                pass
        time.sleep(0.25)
    return False


def _preflight_app() -> object:
    _configure_asyncio_for_windows()
    _log_startup("launcher: preflight app import")
    from persona.web.server import app as fastapi_app

    if getattr(sys, "frozen", False):
        static = Path(sys._MEIPASS) / "persona" / "web" / "static"
        _log_startup(f"launcher: static exists={static.exists()}")
    _log_startup("launcher: preflight ok")
    return fastapi_app


def _run_uvicorn(host: str, port: int, fastapi_app: object) -> None:
    import uvicorn

    try:
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
    except Exception as exc:
        _log_error(exc)
        _log_startup(f"uvicorn: failed: {exc}")
        raise


def _server_timeout_message(host: str, port: int) -> str:
    log_dir = Path.home() / ".persona"
    tail = ""
    startup_log = log_dir / "startup.log"
    if startup_log.exists():
        lines = startup_log.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            tail = "\n\nRecent log:\n" + "\n".join(lines[-8:])
    return (
        "Persona could not start its local server.\n\n"
        f"Tried: http://{host}:{port}\n\n"
        f"Check:\n{log_dir}\\error.log\n{log_dir}\\startup.log"
        f"{tail}"
    )


def _open_when_ready(host: str, port: int, url: str) -> None:
    _log_startup("launcher: waiting for server (window mode)")
    if not wait_for_server(host, port):
        _log_startup("launcher: server did not respond in time")
        _log_error(RuntimeError(f"Server did not respond on {host}:{port}"))
        if getattr(sys, "frozen", False) and not os.environ.get("PERSONA_NO_MSGBOX"):
            _show_windows_error(_server_timeout_message(host, port))
        os._exit(1)
    _log_startup("launcher: opening app window")
    _open_window(url)


def run_standalone(*, window: bool = False, port: int | None = None) -> None:
    """Launch Persona — opens browser after the local server is ready."""
    _log_startup("launcher: begin")
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).parent)

    settings = get_settings()
    host = "127.0.0.1"
    if port is None:
        env_port = os.environ.get("PERSONA_WEB_PORT")
        port = int(env_port) if env_port else find_free_port(settings.web_port, host)
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
    fastapi_app = _preflight_app()

    if window:
        # uvicorn must run on the main thread on Windows; open the UI once ready.
        threading.Thread(
            target=_open_when_ready,
            args=(host, port, url),
            daemon=True,
        ).start()
        _run_uvicorn(host, port, fastapi_app)
        return

    threading.Thread(
        target=lambda: wait_for_server(host, port) and webbrowser.open(url),
        daemon=True,
    ).start()

    if not getattr(sys, "frozen", False):
        _print_banner(url, provider)

    _run_uvicorn(host, port, fastapi_app)


def _frozen_windows() -> bool:
    return getattr(sys, "frozen", False) and sys.platform == "win32"


def _open_window(url: str) -> None:
    """Open Persona in a native window — Edge app mode on frozen Windows, else pywebview."""
    # pywebview often exits immediately in PyInstaller builds; Edge --app is reliable.
    if _frozen_windows():
        _log_startup("launcher: frozen Windows — trying Edge/Chrome app mode first")
        if _open_browser_app_mode(url):
            _log_startup("launcher: opened Edge/Chrome app window")
            _keepalive()
            return
        _log_startup("launcher: Edge/Chrome not found, trying pywebview")

    if _try_pywebview(url):
        _log_startup("launcher: pywebview window closed")
        return

    if _open_browser_app_mode(url):
        _log_startup("launcher: opened Edge/Chrome app window (fallback)")
        _keepalive()
        return

    _log_startup("launcher: falling back to default browser")
    webbrowser.open(url)
    _keepalive()


def _try_pywebview(url: str) -> bool:
    """Return True if pywebview ran until the user closed the window."""
    try:
        import webview
    except Exception as exc:
        _log_startup(f"launcher: pywebview import failed: {exc}")
        return False

    try:
        _log_startup("launcher: starting pywebview")
        webview.create_window("Persona", url, width=1280, height=860, min_size=(900, 600))
        started = time.time()
        if sys.platform == "win32":
            webview.start(gui="edgechromium")
        else:
            webview.start()
        elapsed = time.time() - started
        if _frozen_windows() and elapsed < 2.0:
            _log_startup(f"launcher: pywebview exited too fast ({elapsed:.1f}s)")
            return False
        return True
    except Exception as exc:
        _log_startup(f"launcher: pywebview failed: {exc}")
        return False


def _open_browser_app_mode(url: str) -> bool:
    """Launch Chromium in --app mode (standalone window, no browser tabs)."""
    if sys.platform != "win32":
        return False

    import subprocess

    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            subprocess.Popen(
                [path, f"--app={url}", "--new-window", "--disable-extensions"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            return True
    return False


def _keepalive() -> None:
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def _print_banner(url: str, provider: str) -> None:
    mode = {
        "demo": "Demo",
        "ollama": "Ollama",
        "openai": "Cloud API",
    }.get(provider, provider)
    print(f"\n  Persona running at {url} ({mode})\n  Press Ctrl+C to quit\n")


def main() -> None:
    run_standalone()
