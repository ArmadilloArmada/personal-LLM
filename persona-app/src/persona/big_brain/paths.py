"""Resolve Big Brain paths for dev monorepo and portable installs."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _monorepo_big_brain() -> Path | None:
    here = Path(__file__).resolve()
    # persona-app/src/persona/big_brain/paths.py -> Persona/big-brain
    candidate = here.parents[4] / "big-brain"
    if (candidate / "server" / "package.json").exists():
        return candidate
    return None


def brain_api_url() -> str:
    return os.environ.get("BIG_BRAIN_URL", "http://127.0.0.1:3002").rstrip("/")


def brain_client_dist() -> Path | None:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        for candidate in (
            base / "brain" / "client" / "dist",
            Path(sys._MEIPASS) / "brain" / "client" / "dist",
        ):
            if candidate.exists():
                return candidate
    env = os.environ.get("BIG_BRAIN_CLIENT_DIST")
    if env:
        path = Path(env)
        if path.exists():
            return path
    mono = _monorepo_big_brain()
    if mono:
        built = mono / "client" / "dist"
        if built.exists():
            return built
    return None


def brain_server_entry() -> Path | None:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        for candidate in (
            base / "brain" / "server" / "dist" / "index.js",
            Path(sys._MEIPASS) / "brain" / "server" / "dist" / "index.js",
        ):
            if candidate.exists():
                return candidate
    env = os.environ.get("BIG_BRAIN_SERVER_ENTRY")
    if env:
        path = Path(env)
        if path.exists():
            return path
    mono = _monorepo_big_brain()
    if mono:
        built = mono / "server" / "dist" / "index.js"
        if built.exists():
            return built
    return None


def persona_data_dir() -> Path:
    path = Path.home() / ".persona"
    path.mkdir(parents=True, exist_ok=True)
    return path
