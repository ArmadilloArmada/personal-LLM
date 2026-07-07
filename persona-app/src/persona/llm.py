"""LLM provider abstraction with streaming support."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

import httpx

from persona.config import Settings
from persona.models import LLMResponse, Message, ToolCall


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        ...

    def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        response = self.chat(messages, tools=tools)
        content = response.message.content or ""
        yield content


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

        try:
            response = self.client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise RuntimeError(
                    f"Ollama model '{self.settings.ollama_model}' is not installed. "
                    f"Run: ollama pull {self.settings.ollama_model.split(':')[0]}"
                ) from exc
            raise
        data = response.json()
        return self._parse_response(data)

    def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        if tools:
            yield from super().chat_stream(messages, tools=tools)
            return

        payload: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("message", {}).get("content")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
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

    def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        if tools:
            yield from super().chat_stream(messages, tools=tools)
            return

        payload: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload_text = line[6:]
                if payload_text.strip() == "[DONE]":
                    break
                data = json.loads(payload_text)
                delta = data["choices"][0].get("delta", {})
                chunk = delta.get("content")
                if chunk:
                    yield chunk


from persona.demo import DemoProvider
from persona.providers import ollama_available, ollama_model_installed, ollama_ready, resolve_provider_mode


def get_provider(settings: Settings) -> LLMProvider:
    mode = resolve_provider_mode(settings)
    if mode == "openai":
        return OpenAIProvider(settings)
    if mode == "demo":
        return DemoProvider(settings)
    return OllamaProvider(settings)


def provider_status(settings: Settings) -> dict:
    mode = resolve_provider_mode(settings)
    ollama_up = ollama_available(settings)
    model_ready = ollama_model_installed(settings) if ollama_up else False
    return {
        "active": mode,
        "ollama_available": ollama_up,
        "ollama_model_ready": model_ready,
        "ollama_model": settings.ollama_model,
        "openai_configured": bool(settings.openai_api_key),
        "demo_mode": mode == "demo",
    }
