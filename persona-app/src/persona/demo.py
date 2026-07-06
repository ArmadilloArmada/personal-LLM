"""Demo LLM provider — works instantly with no Ollama or API key."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from persona.config import Settings
from persona.models import LLMResponse, Message


class DemoProvider:
    """Offline demo brain so Persona runs as a standalone app out of the box."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        user_text = _last_user_message(messages)
        persona_name = _persona_from_system(messages)
        reply = _craft_reply(persona_name, user_text, bool(tools))
        return LLMResponse(message=Message(role="assistant", content=reply))

    def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        text = self.chat(messages, tools).message.content or ""
        for i in range(0, len(text), 18):
            yield text[i : i + 18]


def _last_user_message(messages: list[Message]) -> str:
    for msg in reversed(messages):
        if msg.role == "user" and msg.content:
            return msg.content.strip()
    return ""


def _persona_from_system(messages: list[Message]) -> str:
    for msg in messages:
        if msg.role != "system" or not msg.content:
            continue
        text = msg.content
        for name in ("Byte", "Sunny", "Nova", "Sketch", "Captain"):
            if f"You are {name}" in text:
                return name
        match = re.search(r"You are (\w+)", text)
        if match:
            return match.group(1)
    return "Persona"


def _craft_reply(persona: str, user_text: str, has_tools: bool) -> str:
    topic = user_text[:120] if user_text else "your request"
    tool_note = (
        "\n\n*(Demo mode — tool actions are simulated. Connect Ollama or an API key in "
        "Settings for real file/shell/doc access.)*"
        if has_tools
        else ""
    )

    templates = {
        "Byte": (
            f"Hey! Byte here 💻 — I'd tackle **{topic}** like this:\n\n"
            "1. Scan the repo structure\n"
            "2. Write a minimal fix with tests\n"
            "3. Run the build and confirm green\n\n"
            "In full AI mode I can actually read your files and run commands for you."
        ),
        "Sunny": (
            f"Hi friend! ☀️ Sunny here. I hear you on **{topic}**.\n\n"
            "Let's break it down together — what's the one thing that would make this feel "
            "solved? Sometimes talking it through is half the battle.\n\n"
            "I'm in demo mode right now, but I'm still a great sounding board!"
        ),
        "Nova": (
            f"Nova reporting 🔭 — researching **{topic}**:\n\n"
            "**Key angles to explore:**\n"
            "- Primary sources and recent data\n"
            "- Trade-offs between top options\n"
            "- Recommendation with caveats\n\n"
            "Connect a real model and upload company docs — I'll search them automatically."
        ),
        "Sketch": (
            f"Ooh, fun! 🎨 Sketch here. For **{topic}** I'd pitch:\n\n"
            "- **Option A:** Bold & playful\n"
            "- **Option B:** Clean & professional\n"
            "- **Option C:** Weird in the best way\n\n"
            "Tell me your audience and I'll refine the vibe!"
        ),
        "Captain": (
            f"Captain on deck 🧭 — project plan for **{topic}**:\n\n"
            "**Phase 1 — Plan:** Define scope and success metrics\n"
            "**Phase 2 — Build:** Byte ships code, Sketch handles copy\n"
            "**Phase 3 — Ship:** Nova validates, Sunny keeps morale up\n\n"
            "Switch to Project mode and I'll delegate to the full crew!"
        ),
    }

    body = templates.get(persona, templates["Sunny"])
    header = (
        "> 🎭 **Demo mode** — Persona is running standalone. "
        "Install [Ollama](https://ollama.com) or add an API key anytime for full AI power.\n\n"
    )
    return header + body + tool_note
