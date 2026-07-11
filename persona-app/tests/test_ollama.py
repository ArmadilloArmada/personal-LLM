"""Tests for Ollama provider compatibility."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from persona.config import Settings
from persona.llm import OllamaProvider, _to_ollama_messages
from persona.models import Message
from persona.providers import (
    ollama_model_supports_tools,
    resolve_ollama_model_name,
)


def test_ollama_model_supports_tools_heuristic():
    assert ollama_model_supports_tools("llama3.2:latest") is True
    assert ollama_model_supports_tools("llama3.1:8b") is True
    assert ollama_model_supports_tools("llama3:latest") is False
    assert ollama_model_supports_tools("mistral:latest") is False


def test_resolve_ollama_model_name_prefers_exact_tag(monkeypatch):
    settings = Settings(ollama_model="llama3.2")
    monkeypatch.setattr(
        "persona.providers.ollama_installed_models",
        lambda s: ["llama3:latest", "llama3.2:latest"],
    )
    assert resolve_ollama_model_name(settings) == "llama3.2:latest"


def test_resolve_ollama_model_name_falls_back_to_first_installed(monkeypatch):
    settings = Settings(ollama_model="llama3.2")
    monkeypatch.setattr(
        "persona.providers.ollama_installed_models",
        lambda s: ["mistral:latest", "phi3:latest"],
    )
    assert resolve_ollama_model_name(settings) == "mistral:latest"


def test_to_ollama_messages_ensures_string_content():
    messages = [
        Message(role="system", content="hi"),
        Message(role="assistant", content=None, tool_calls=[]),
        Message(role="tool", content="done", name="remember", tool_call_id="1"),
    ]
    payload = _to_ollama_messages(messages)
    assert payload[1]["content"] == ""
    assert payload[2]["tool_name"] == "remember"


def test_ollama_chat_retries_without_tools_on_400(monkeypatch):
    settings = Settings(ollama_model="llama3.2:latest", provider="ollama")
    provider = OllamaProvider(settings)
    provider._model_name = "llama3:latest"
    provider._tools_supported = True

    calls: list[dict] = []

    def fake_post(path, json=None):
        calls.append(json or {})
        response = MagicMock()
        if json and json.get("tools"):
            response.status_code = 400
            response.json.return_value = {"error": "llama3:latest does not support tools"}
            raise httpx.HTTPStatusError(
                "bad",
                request=MagicMock(),
                response=response,
            )
        response.status_code = 200
        response.json.return_value = {
            "message": {"role": "assistant", "content": "Hello from Ollama"}
        }
        response.raise_for_status = MagicMock()
        return response

    provider.client.post = fake_post
    tools = [{"type": "function", "function": {"name": "remember", "parameters": {}}}]
    result = provider.chat([Message(role="user", content="hi")], tools=tools)

    assert result.message.content == "Hello from Ollama"
    assert len(calls) == 2
    assert "tools" in calls[0]
    assert "tools" not in calls[1]
    assert provider._tools_supported is False


def test_ollama_skips_tools_for_non_tool_models(monkeypatch):
    settings = Settings(ollama_model="llama3:latest", provider="ollama")
    provider = OllamaProvider(settings)
    provider._model_name = "llama3:latest"

    posted: list[dict] = []

    def fake_post(path, json=None):
        posted.append(json or {})
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "message": {"role": "assistant", "content": "ok"}
        }
        response.raise_for_status = MagicMock()
        return response

    provider.client.post = fake_post
    tools = [{"type": "function", "function": {"name": "remember", "parameters": {}}}]
    provider.chat([Message(role="user", content="hi")], tools=tools)

    assert "tools" not in posted[0]
