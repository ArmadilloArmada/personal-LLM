"""Provider detection shared by launcher and LLM layer."""

from __future__ import annotations

import os
import sys

import httpx

from persona.config import Settings


def bundled_ready(settings: Settings | None = None) -> bool:
    from persona.bundled import bundled_ready as _bundled_ready

    return _bundled_ready(settings)


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


# Model families that generally support Ollama tool calling (function calling).
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
    """Pick provider — bundled AI first on frozen builds, then Ollama/cloud."""
    if getattr(sys, "frozen", False) and not os.environ.get("PERSONA_PROVIDER"):
        if bundled_ready(settings):
            return "bundled"
        return "demo"

    mode = (settings.provider or "auto").lower()
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
