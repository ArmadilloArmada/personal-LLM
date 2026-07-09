"""Tests for Ollama provider message formatting."""

from __future__ import annotations

import json

from persona.config import Settings
from persona.llm import OllamaProvider
from persona.models import Message, ToolCall


def test_ollama_prepare_messages_parses_tool_arguments():
    provider = OllamaProvider(Settings())
    messages = [
        Message(role="user", content="hello"),
        Message(
            role="assistant",
            tool_calls=[
                ToolCall(id="call_1", name="search_docs", arguments={"query": "test"}),
            ],
        ),
        Message(role="tool", content="results", tool_call_id="call_1", name="search_docs"),
    ]
    prepared = provider._prepare_messages(messages)
    args = prepared[1]["tool_calls"][0]["function"]["arguments"]
    assert isinstance(args, dict)
    assert args["query"] == "test"
    assert prepared[1]["content"] == ""
