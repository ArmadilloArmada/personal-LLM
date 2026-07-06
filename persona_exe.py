"""Entry point for PyInstaller Windows .exe builds."""

from __future__ import annotations

import multiprocessing
import os
import sys
import traceback
from pathlib import Path


def _bootstrap() -> None:
    if getattr(sys, "frozen", False):
        # Run from the folder containing Persona.exe (required for one-folder builds).
        os.chdir(Path(sys.executable).parent)
        multiprocessing.freeze_support()


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
    else:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    _bootstrap()
    try:
        from persona.launcher import run_standalone

        run_standalone()
    except Exception as e:
        _show_fatal_error(e)
        sys.exit(1)
