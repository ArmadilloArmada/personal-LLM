"""Provider detection shared by launcher and LLM layer."""

from __future__ import annotations

import os
import sys
import time

import httpx

from persona.config import Settings

_OLLAMA_CACHE: dict[str, tuple[float, bool, list[str]]] = {}
_CACHE_TTL = 5.0


def _cache_key(settings: Settings) -> str:
    return settings.ollama_base_url


def _get_cached(settings: Settings) -> tuple[bool, list[str]] | None:
    key = _cache_key(settings)
    entry = _OLLAMA_CACHE.get(key)
    if not entry:
        return None
    ts, available, models = entry
    if time.time() - ts > _CACHE_TTL:
        return None
    return available, models


def _set_cache(settings: Settings, available: bool, models: list[str]) -> None:
    _OLLAMA_CACHE[_cache_key(settings)] = (time.time(), available, models)


def bundled_ready(settings: Settings | None = None) -> bool:
    from persona.bundled import bundled_ready as _bundled_ready

    return _bundled_ready(settings)


def ollama_available(settings: Settings) -> bool:
    cached = _get_cached(settings)
    if cached is not None:
        return cached[0]
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=1.5)
        available = r.status_code == 200
        models = (
            [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
            if available
            else []
        )
        _set_cache(settings, available, models)
        return available
    except Exception:
        _set_cache(settings, False, [])
        return False


def ollama_installed_models(settings: Settings) -> list[str]:
    cached = _get_cached(settings)
    if cached is not None:
        return cached[1]
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        if r.status_code != 200:
            _set_cache(settings, False, [])
            return []
        models = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
        _set_cache(settings, True, models)
        return models
    except Exception:
        _set_cache(settings, False, [])
        return []


def ollama_model_installed(settings: Settings) -> bool:
    """True when the configured Ollama model is actually pulled locally."""
    return _match_installed_model(settings.ollama_model, ollama_installed_models(settings)) is not None


def _match_installed_model(target: str, installed: list[str]) -> str | None:
    if target in installed:
        return target
    base = target.split(":")[0]
    for name in installed:
        if name.split(":")[0] == base or name == target:
            return name
    return None


def resolve_ollama_model_name(settings: Settings) -> str:
    """Pick the exact Ollama tag to use for chat requests."""
    installed = ollama_installed_models(settings)
    if not installed:
        return settings.ollama_model
    matched = _match_installed_model(settings.ollama_model, installed)
    if matched:
        return matched
    return installed[0]


_OLLAMA_TOOL_MODEL_PREFIXES = (
    "llama3.1",
    "llama3.2",
    "llama3.3",
    "llama4",
    "qwen2.5",
    "qwen3",
    "mistral-nemo",
    "command-r",
    "firefunction",
    "nemotron",
    "hermes3",
    "deepseek-r1",
    "granite3",
)


def ollama_model_supports_tools(model_name: str) -> bool:
    base = model_name.split(":")[0].lower()
    return any(base == prefix or base.startswith(f"{prefix}-") for prefix in _OLLAMA_TOOL_MODEL_PREFIXES)


def ollama_ready(settings: Settings) -> bool:
    """Ollama is running and at least one model is available for chat."""
    return ollama_available(settings) and bool(ollama_installed_models(settings))


def resolve_provider_mode(settings: Settings) -> str:
    """Pick the best provider from saved settings and live availability."""
    mode = (settings.provider or "auto").lower()
    if mode == "auto" and getattr(sys, "frozen", False) and not os.environ.get("PERSONA_PROVIDER"):
        if bundled_ready(settings):
            return "bundled"
    if mode == "demo":
        return "demo"
    if mode == "bundled":
        return "bundled" if bundled_ready(settings) else "demo"
    if mode == "openai":
        return "openai" if settings.openai_api_key else "demo"
    if mode == "ollama":
        if ollama_ready(settings):
            return "ollama"
        return "openai" if settings.openai_api_key else "demo"
    if bundled_ready(settings):
        return "bundled"
    if ollama_ready(settings):
        return "ollama"
    if settings.openai_api_key:
        return "openai"
    return "demo"
