"""LLM provider abstraction."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from personal_llm.config import Settings
from personal_llm.models import LLMResponse, Message, ToolCall


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        ...


class OllamaProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(base_url=settings.ollama_base_url, timeout=300.0)

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        response = self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        msg = data.get("message", {})
        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args) if args else {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", f"call_{fn.get('name', 'unknown')}"),
                    name=fn.get("name", ""),
                    arguments=args,
                )
            )

        return LLMResponse(
            message=Message(
                role=msg.get("role", "assistant"),
                content=msg.get("content"),
                tool_calls=tool_calls,
            ),
            finish_reason="tool_calls" if tool_calls else "stop",
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        headers = {"Content-Type": "application/json"}
        if settings.openai_api_key:
            headers["Authorization"] = f"Bearer {settings.openai_api_key}"
        self.client = httpx.Client(
            base_url=settings.openai_base_url.rstrip("/"),
            headers=headers,
            timeout=300.0,
        )

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": [m.to_dict() for m in messages],
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        msg = choice["message"]
        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc["function"]
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args) if args else {}
            tool_calls.append(
                ToolCall(
                    id=tc["id"],
                    name=fn["name"],
                    arguments=args,
                )
            )

        return LLMResponse(
            message=Message(
                role=msg.get("role", "assistant"),
                content=msg.get("content"),
                tool_calls=tool_calls,
            ),
            finish_reason=choice.get("finish_reason"),
        )


def get_provider(settings: Settings) -> LLMProvider:
    if settings.provider == "openai":
        return OpenAIProvider(settings)
    return OllamaProvider(settings)
