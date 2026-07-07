"""Open Persona UI in Edge/Chrome app mode or default browser."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser


def open_persona_ui(url: str, *, force_new: bool = False) -> bool:
    """Open Persona URL. Returns True if a browser was launched."""
    if sys.platform == "win32":
        browser = _find_chromium()
        if browser:
            args = [browser, f"--app={url}"]
            if force_new:
                args.append("--new-window")
            args.append("--disable-extensions")
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            return True
    webbrowser.open(url)
    return True


def _find_chromium() -> str | None:
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None
