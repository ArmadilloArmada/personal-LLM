"""Tests for bundled model tool-calling support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from persona.bundled import MODEL_TIERS, bundled_tier_supports_tools
from persona.config import Settings
from persona.llm import BundledProvider, provider_status
from persona.models import LLMResponse, Message


def test_quality_tier_supports_tools():
    assert MODEL_TIERS["quality"]["supports_tools"] is True
    assert bundled_tier_supports_tools("quality") is True


def test_fast_balanced_tiers_no_tools():
    assert bundled_tier_supports_tools("fast") is False
    assert bundled_tier_supports_tools("balanced") is False
    assert bundled_tier_supports_tools("unknown") is False


def test_quality_model_is_qwen():
    url = MODEL_TIERS["quality"]["download_url"]
    assert "Qwen2.5-3B-Instruct" in url


def test_provider_status_bundled_tools_flag(monkeypatch):
    monkeypatch.setattr(
        "persona.bundled.bundled_status",
        lambda s: {"active_tier": "quality", "available": True},
    )
    monkeypatch.setattr("persona.providers.bundled_ready", lambda s: True)
    monkeypatch.setattr("persona.llm.resolve_provider_mode", lambda s: "bundled")
    monkeypatch.setattr("persona.llm.ollama_available", lambda s: False)
    monkeypatch.setattr("persona.llm.ollama_model_installed", lambda s: False)

    status = provider_status(Settings())
    assert status["bundled_tools_supported"] is True


def test_bundled_provider_skips_tools_for_fast_tier(monkeypatch):
    monkeypatch.setattr("persona.bundled.resolve_active_tier", lambda s: "fast")
    monkeypatch.setattr(
        "persona.bundled.bundled_server_url",
        lambda s: "http://127.0.0.1:11435",
    )
    inner = MagicMock()
    inner.chat.return_value = LLMResponse(message=Message(role="assistant", content="hi"))
    monkeypatch.setattr("persona.llm.OpenAIProvider", lambda s: inner)

    provider = BundledProvider(Settings())
    provider.chat([Message(role="user", content="hello")], tools=[{"type": "function"}])
    inner.chat.assert_called_once()
    assert inner.chat.call_args.kwargs.get("tools") is None


def test_bundled_provider_sends_tools_for_quality_tier(monkeypatch):
    monkeypatch.setattr("persona.bundled.resolve_active_tier", lambda s: "quality")
    monkeypatch.setattr(
        "persona.bundled.bundled_server_url",
        lambda s: "http://127.0.0.1:11435",
    )
    inner = MagicMock()
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    inner.chat.return_value = LLMResponse(message=Message(role="assistant", content="ok"))
    monkeypatch.setattr("persona.llm.OpenAIProvider", lambda s: inner)

    provider = BundledProvider(Settings())
    provider.chat([Message(role="user", content="read foo")], tools=tools)
    inner.chat.assert_called_once_with(
        [Message(role="user", content="read foo")],
        tools=tools,
    )


def test_bundled_provider_falls_back_on_400(monkeypatch):
    monkeypatch.setattr("persona.bundled.resolve_active_tier", lambda s: "quality")
    monkeypatch.setattr(
        "persona.bundled.bundled_server_url",
        lambda s: "http://127.0.0.1:11435",
    )
    inner = MagicMock()
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    ok = LLMResponse(message=Message(role="assistant", content="ok"))
    request = httpx.Request("POST", "http://127.0.0.1:11435/v1/chat/completions")
    response = httpx.Response(400, request=request, text="tools not supported")
    inner.chat.side_effect = [
        httpx.HTTPStatusError("bad", request=request, response=response),
        ok,
    ]
    monkeypatch.setattr("persona.llm.OpenAIProvider", lambda s: inner)

    provider = BundledProvider(Settings())
    result = provider.chat([Message(role="user", content="read foo")], tools=tools)
    assert result.message.content == "ok"
    assert inner.chat.call_count == 2
    assert inner.chat.call_args_list[1].kwargs.get("tools") is None
    assert provider._tools_supported is False
