"""LLM provider abstraction with streaming support."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

import httpx

from persona.config import Settings
from persona.demo import DemoProvider
from persona.models import LLMResponse, Message, ToolCall
from persona.providers import (
    ollama_available,
    ollama_model_installed,
    ollama_model_supports_tools,
    ollama_ready,
    resolve_ollama_model_name,
    resolve_provider_mode,
)


def _ollama_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        err = body.get("error")
        if isinstance(err, str):
            return err
        if isinstance(err, dict):
            return str(err.get("message", err))
    except Exception:
        pass
    return response.text.strip()


def _to_ollama_messages(messages: list[Message]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for message in messages:
        data = message.to_dict()
        if data.get("content") is None:
            data["content"] = ""
        if message.role == "tool" and message.name:
            data["tool_name"] = message.name
        result.append(data)
    return result


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
        self._model_name = resolve_ollama_model_name(settings)
        self._tools_supported: bool | None = None

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        send_tools = self._should_send_tools(tools)
        try:
            return self._chat_once(messages, send_tools)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400 and send_tools:
                self._tools_supported = False
                return self._chat_once(messages, None)
            raise self._friendly_error(exc) from exc

    def _should_send_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        if self._tools_supported is False:
            return None
        if self._tools_supported is True:
            return tools
        if ollama_model_supports_tools(self._model_name):
            return tools
        self._tools_supported = False
        return None

    def _chat_once(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": _to_ollama_messages(messages),
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        response = self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        return self._parse_response(response.json())

    def _friendly_error(self, exc: httpx.HTTPStatusError) -> RuntimeError:
        detail = _ollama_error_message(exc.response)
        if exc.response.status_code == 404:
            return RuntimeError(
                f"Ollama model '{self._model_name}' is not installed. "
                f"Run: ollama pull {self._model_name.split(':')[0]}"
            )
        if exc.response.status_code == 400 and "support tools" in detail.lower():
            return RuntimeError(
                f"Model '{self._model_name}' does not support tools in Ollama. "
                "Persona will chat without tools, or try: ollama pull llama3.2"
            )
        return RuntimeError(detail or f"Ollama request failed ({exc.response.status_code})")

    def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        if self._should_send_tools(tools):
            yield from super().chat_stream(messages, tools=tools)
            return

        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": _to_ollama_messages(messages),
            "stream": True,
        }
        with self.client.stream("POST", "/api/chat", json=payload) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise self._friendly_error(exc) from exc
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


class BundledProvider(LLMProvider):
    """Local llama.cpp server shipped inside Persona — no Ollama install required."""

    def __init__(self, settings: Settings):
        from persona.bundled import MODEL_TIERS, bundled_server_url, resolve_active_tier

        self.settings = settings
        tier = resolve_active_tier(settings)
        base = bundled_server_url(settings)
        inner_settings = settings.model_copy(
            update={
                "openai_base_url": f"{base.rstrip('/')}/v1",
                "openai_api_key": "",
                "openai_model": MODEL_TIERS[tier]["label"],
            }
        )
        self._inner = OpenAIProvider(inner_settings)
        self._tier = tier

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        return self._inner.chat(messages, tools=tools)

    def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        yield from self._inner.chat_stream(messages, tools=tools)


def get_provider(settings: Settings) -> LLMProvider:
    mode = resolve_provider_mode(settings)
    if mode == "bundled":
        return BundledProvider(settings)
    if mode == "openai":
        return OpenAIProvider(settings)
    if mode == "demo":
        return DemoProvider(settings)
    return OllamaProvider(settings)


def provider_status(settings: Settings) -> dict:
    from persona.bundled import bundled_status
    from persona.providers import bundled_ready

    mode = resolve_provider_mode(settings)
    ollama_up = ollama_available(settings)
    model_ready = ollama_model_installed(settings)
    resolved_model = resolve_ollama_model_name(settings) if ollama_up else settings.ollama_model
    bundled = bundled_status(settings)
    return {
        "active": mode,
        "bundled": bundled,
        "bundled_available": bundled_ready(settings),
        "ollama_available": ollama_up,
        "ollama_model_ready": model_ready,
        "ollama_model": settings.ollama_model,
        "ollama_model_resolved": resolved_model,
        "ollama_tools_supported": ollama_model_supports_tools(resolved_model),
        "openai_configured": bool(settings.openai_api_key),
        "demo_mode": mode == "demo",
    }
