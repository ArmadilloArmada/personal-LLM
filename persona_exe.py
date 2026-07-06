"""Entry point for PyInstaller Windows .exe — double-click standalone app."""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path


def _early_log(message: str) -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        log_dir = Path.home() / ".persona"
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%H:%M:%S")
        with (log_dir / "startup.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")
    except Exception:
        pass


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


def _verify_frozen_layout() -> None:
    if not getattr(sys, "frozen", False):
        return
    exe_dir = Path(sys.executable).resolve().parent
    internal = exe_dir / "_internal"
    if internal.is_dir():
        return
    raise FileNotFoundError(
        "The _internal folder is missing next to Persona.exe.\n"
        "Unzip the entire Persona-Windows-portable.zip and run Persona.exe "
        "from inside that folder (do not move the .exe alone)."
    )


if __name__ == "__main__":
    _early_log("persona_exe: boot")
    _bootstrap_stdio()
    try:
        _verify_frozen_layout()
        _early_log("persona_exe: layout ok, importing launcher")
        from persona.launcher import run_standalone

        # Native app window on Windows (falls back to browser if webview unavailable).
        _early_log("persona_exe: calling run_standalone(window=True)")
        run_standalone(window=True)
        _early_log("persona_exe: run_standalone returned")
    except Exception as e:
        _early_log(f"persona_exe: fatal error: {e}")
        _show_fatal_error(e)
        sys.exit(1)
