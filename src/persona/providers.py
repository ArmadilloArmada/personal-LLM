"""Provider detection shared by launcher and LLM layer."""

from __future__ import annotations

import httpx

from persona.config import Settings


def ollama_available(settings: Settings) -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def ollama_installed_models(settings: Settings) -> list[str]:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
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
