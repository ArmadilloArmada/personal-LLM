"""Provider detection shared by launcher and LLM layer."""

from __future__ import annotations

import os
import sys

import httpx

from persona.config import Settings


def ollama_available(settings: Settings) -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def resolve_provider_mode(settings: Settings) -> str:
    """Pick provider — frozen Windows builds default to demo for instant startup."""
    if getattr(sys, "frozen", False) and not os.environ.get("PERSONA_PROVIDER"):
        return "demo"

    mode = (settings.provider or "auto").lower()
    if mode == "demo":
        return "demo"
    if mode == "openai":
        return "openai" if settings.openai_api_key else "demo"
    if mode == "ollama":
        if ollama_available(settings):
            return "ollama"
        return "openai" if settings.openai_api_key else "demo"
    if ollama_available(settings):
        return "ollama"
    if settings.openai_api_key:
        return "openai"
    return "demo"
