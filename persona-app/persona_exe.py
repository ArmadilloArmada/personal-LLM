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


if __name__ == "__main__":
    _bootstrap_stdio()
    try:
        from persona.dialogs import show_fatal_error
        from persona.launcher import run_standalone

        run_standalone(window=True)
    except Exception as e:
        log_dir = Path.home() / ".persona"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        show_fatal_error(e, log_path)
        sys.exit(1)
