"""Provider detection shared by launcher and LLM layer."""

from __future__ import annotations

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
    target = settings.ollama_model.split(":")[0]
    for name in ollama_installed_models(settings):
        base = name.split(":")[0]
        if base == target or name == settings.ollama_model:
            return True
    return False


def ollama_ready(settings: Settings) -> bool:
    """Ollama is running and the configured model is available for chat."""
    return ollama_available(settings) and ollama_model_installed(settings)


def resolve_provider_mode(settings: Settings) -> str:
    """Pick the best provider from saved settings and live availability."""
    mode = (settings.provider or "auto").lower()
    if mode == "demo":
        return "demo"
    if mode == "openai":
        return "openai" if settings.openai_api_key else "demo"
    if mode == "ollama":
        if ollama_ready(settings):
            return "ollama"
        return "openai" if settings.openai_api_key else "demo"
    if ollama_ready(settings):
        return "ollama"
    if settings.openai_api_key:
        return "openai"
    return "demo"
