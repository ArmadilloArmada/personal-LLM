"""Persistent user preferences in ~/.persona/config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_VERSION = 1

_ENV_MAP = {
    "provider": "PERSONA_PROVIDER",
    "ollama_base_url": "PERSONA_OLLAMA_BASE_URL",
    "ollama_model": "PERSONA_OLLAMA_MODEL",
    "openai_base_url": "PERSONA_OPENAI_BASE_URL",
    "openai_api_key": "PERSONA_OPENAI_API_KEY",
    "openai_model": "PERSONA_OPENAI_MODEL",
    "allow_shell_commands": "PERSONA_ALLOW_SHELL",
}


class UserConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._data = {k: v for k, v in raw.items() if k != "version"}
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            if value is None:
                self._data.pop(key, None)
            else:
                self._data[key] = value
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": CONFIG_VERSION, **self._data}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_store: UserConfigStore | None = None


def get_user_config() -> UserConfigStore:
    global _store
    if _store is None:
        _store = UserConfigStore(Path.home() / ".persona" / "config.json")
    return _store


def apply_user_config(settings: Any) -> None:
    """Overlay saved config when env vars are not set."""
    cfg = get_user_config().all()
    for field, env_key in _ENV_MAP.items():
        if env_key in os.environ:
            continue
        if field in cfg and cfg[field] is not None and cfg[field] != "":
            setattr(settings, field, cfg[field])
    if "allow_shell_commands" in cfg and "PERSONA_ALLOW_SHELL" not in os.environ:
        settings.allow_shell_commands = bool(cfg["allow_shell_commands"])
    if "onboarding_completed" in cfg:
        settings.onboarding_completed = bool(cfg["onboarding_completed"])


def save_user_config(settings: Any, **extra: Any) -> None:
    """Persist settings and sync into the current process environment."""
    data: dict[str, Any] = {
        "provider": settings.provider,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "openai_base_url": settings.openai_base_url,
        "openai_model": settings.openai_model,
        "allow_shell_commands": getattr(settings, "allow_shell_commands", False),
        "onboarding_completed": getattr(settings, "onboarding_completed", False),
    }
    if settings.openai_api_key:
        data["openai_api_key"] = settings.openai_api_key
    data.update(extra)
    get_user_config().update(data)

    os.environ["PERSONA_PROVIDER"] = settings.provider
    os.environ["PERSONA_OLLAMA_MODEL"] = settings.ollama_model
    os.environ["PERSONA_OLLAMA_BASE_URL"] = settings.ollama_base_url
    os.environ["PERSONA_OPENAI_MODEL"] = settings.openai_model
    os.environ["PERSONA_OPENAI_BASE_URL"] = settings.openai_base_url
    if settings.openai_api_key:
        os.environ["PERSONA_OPENAI_API_KEY"] = settings.openai_api_key
    os.environ["PERSONA_ALLOW_SHELL"] = "1" if getattr(settings, "allow_shell_commands", False) else "0"
