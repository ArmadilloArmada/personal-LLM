"""Entry point for PyInstaller Windows .exe builds."""

import os
import sys

# Windowed PyInstaller builds have no console — uvicorn logging needs stderr.
if getattr(sys, "frozen", False):
    _devnull = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _devnull
    if sys.stderr is None:
        sys.stderr = _devnull

from persona.launcher import run_standalone

if __name__ == "__main__":
    run_standalone()
