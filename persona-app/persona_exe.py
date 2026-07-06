"""Entry point for PyInstaller Windows .exe — double-click standalone app."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _bootstrap_stdio() -> None:
    if not getattr(sys, "frozen", False):
        return
    devnull = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = devnull
    if sys.stderr is None:
        sys.stderr = devnull


def _show_fatal_error(exc: BaseException) -> None:
    log_dir = Path.home() / ".persona"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "error.log"
    log_path.write_text(traceback.format_exc(), encoding="utf-8")

    message = (
        f"Persona could not start.\n\n{exc}\n\n"
        f"Details saved to:\n{log_path}\n\n"
        "Make sure you unzipped the full folder and run Persona.exe inside it."
    )
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, "Persona", 0x10)
        except Exception:
            pass


if __name__ == "__main__":
    _bootstrap_stdio()
    try:
        from persona.launcher import run_standalone

        # Native app window on Windows (falls back to browser if webview unavailable).
        run_standalone(window=True)
    except Exception as e:
        _show_fatal_error(e)
        sys.exit(1)
