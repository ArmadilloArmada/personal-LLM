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


def _log_error(exc: BaseException) -> None:
    path = _persona_log_dir() / "error.log"
    path.write_text(traceback.format_exc(), encoding="utf-8")


def _show_windows_error(message: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "Persona", 0x10)
    except Exception:
        pass


def find_free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 45.0) -> bool:
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


def run_standalone(*, window: bool = False, port: int | None = None) -> None:
    """Launch Persona — opens browser after the local server is ready."""
    _log_startup("launcher: begin")
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
    _log_startup(f"launcher: provider={provider} port={port}")

    url = f"http://{host}:{port}"

    if window:
        # Non-daemon: keeps the process alive if the main thread exits unexpectedly.
        server = threading.Thread(target=_run_uvicorn, args=(host, port), daemon=False)
        server.start()
        _log_startup("launcher: waiting for server (window mode)")
        if not wait_for_server(host, port):
            message = (
                "Persona could not start its local server.\n\n"
                "Check %USERPROFILE%\\.persona\\error.log and startup.log"
            )
            _log_startup("launcher: server did not respond in time")
            _log_error(RuntimeError(f"Server did not respond on {host}:{port}"))
            if getattr(sys, "frozen", False):
                if not os.environ.get("PERSONA_NO_MSGBOX"):
                    _show_windows_error(message)
                sys.exit(1)
            print("Persona failed to start.", file=sys.stderr)
            sys.exit(1)
        _log_startup("launcher: opening app window")
        _open_window(url)
        return

    threading.Thread(
        target=lambda: wait_for_server(host, port) and webbrowser.open(url),
        daemon=True,
    ).start()

    if not getattr(sys, "frozen", False):
        _print_banner(url, provider)

    _run_uvicorn(host, port)


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
