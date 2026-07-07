"""Windows startup error dialogs with actionable choices."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def persona_data_dir() -> Path:
    return Path.home() / ".persona"


def open_logs_folder() -> None:
    log_dir = persona_data_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(log_dir))  # type: ignore[attr-defined]
    else:
        webbrowser.open(log_dir.as_uri())


def show_startup_failure(url: str | None = None) -> None:
    if sys.platform != "win32" or os.environ.get("PERSONA_NO_MSGBOX"):
        return

    log_dir = persona_data_dir()
    message = (
        "Persona could not start its local server within 45 seconds.\n\n"
        f"Logs: {log_dir}\n\n"
    )
    if url:
        message += f"Try opening manually:\n{url}\n\n"
    message += "Yes = Open in browser\nNo = Open logs folder\nCancel = Close"

    try:
        import ctypes

        MB_YESNOCANCEL = 0x00000003
        MB_ICONERROR = 0x00000010
        IDYES = 6
        IDNO = 7
        choice = ctypes.windll.user32.MessageBoxW(0, message, "Persona", MB_YESNOCANCEL | MB_ICONERROR)
        if choice == IDYES and url:
            webbrowser.open(url)
        elif choice == IDNO:
            open_logs_folder()
    except Exception:
        pass


def show_browser_missing(url: str) -> None:
    if sys.platform != "win32" or os.environ.get("PERSONA_NO_MSGBOX"):
        return
    message = (
        "Persona started but could not open Edge or Chrome.\n\n"
        f"Open this URL in your browser:\n{url}\n\n"
        "Yes = Open in default browser\nNo = Open logs folder"
    )
    try:
        import ctypes

        MB_YESNO = 0x00000004
        MB_ICONWARNING = 0x00000030
        IDYES = 6
        choice = ctypes.windll.user32.MessageBoxW(0, message, "Persona", MB_YESNO | MB_ICONWARNING)
        if choice == IDYES:
            webbrowser.open(url)
        else:
            open_logs_folder()
    except Exception:
        webbrowser.open(url)


def show_fatal_error(exc: BaseException, log_path: Path) -> None:
    if sys.platform != "win32" or os.environ.get("PERSONA_NO_MSGBOX"):
        return
    message = (
        f"Persona could not start.\n\n{exc}\n\n"
        f"Details: {log_path}\n\n"
        "Yes = Open logs folder\nNo = Close"
    )
    try:
        import ctypes

        MB_YESNO = 0x00000004
        MB_ICONERROR = 0x00000010
        if ctypes.windll.user32.MessageBoxW(0, message, "Persona", MB_YESNO | MB_ICONERROR) == 6:
            open_logs_folder()
    except Exception:
        pass
