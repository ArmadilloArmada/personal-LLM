"""Agent loop with tool execution."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from personal_llm.config import Settings
from personal_llm.llm import get_provider
from personal_llm.memory import MemoryStore
from personal_llm.models import Message
from personal_llm.tools import Tool, build_tools, run_tool, tool_schemas

SYSTEM_PROMPT = """You are a capable personal AI agent running on the user's machine.

You help with coding, research, file management, shell commands, and general tasks.
You have tools to read/write files, list directories, run shell commands, fetch web pages,
and remember facts across sessions.

Guidelines:
- Be direct and helpful. Prefer action over lengthy explanations.
- Use tools when they help accomplish the task — don't guess file contents or command output.
- Stay within the workspace unless the user explicitly asks otherwise.
- When you learn something important about the user (name, preferences, project context), use remember.
- For destructive shell commands, explain what you're about to do first.
- If a task is ambiguous, ask a short clarifying question before acting.
"""


class Agent:
    def __init__(
        self,
        settings: Settings,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
    ):
        self.settings = settings
        self.workspace = settings.workspace.resolve()
        self.memory = MemoryStore(settings.memory_file)
        self.tools: list[Tool] = build_tools(self.workspace, self.memory)
        self.provider = get_provider(settings)
        self.messages: list[Message] = []
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self._init_system()

    def _init_system(self) -> None:
        memory_context = self.memory.as_context()
        content = SYSTEM_PROMPT
        if memory_context:
            content += f"\n\n{memory_context}"
        content += f"\n\nWorkspace: {self.workspace}"
        content += f"\nCurrent time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        self.messages = [Message(role="system", content=content)]

    def reset(self) -> None:
        self._init_system()

    def load_session(self, path: Path) -> None:
        from personal_llm.models import ToolCall

        data = json.loads(path.read_text(encoding="utf-8"))
        self.messages = []
        for m in data.get("messages", []):
            tool_calls = [
                ToolCall(id=tc["id"], name=tc["name"], arguments=tc.get("arguments", {}))
                for tc in m.get("tool_calls", [])
            ]
            self.messages.append(
                Message(
                    role=m["role"],
                    content=m.get("content"),
                    tool_calls=tool_calls,
                    tool_call_id=m.get("tool_call_id"),
                    name=m.get("name"),
                )
            )
        if not self.messages or self.messages[0].role != "system":
            self._init_system()

    def save_session(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for m in self.messages:
            d = m.to_dict()
            if m.tool_calls:
                d["tool_calls"] = [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in m.tool_calls
                ]
            serializable.append(d)
        path.write_text(json.dumps({"messages": serializable}, indent=2), encoding="utf-8")

    def chat(self, user_input: str) -> str:
        self.messages.append(Message(role="user", content=user_input))

        for _ in range(self.settings.max_tool_rounds):
            response = self.provider.chat(
                self.messages,
                tools=tool_schemas(self.tools),
            )
            assistant = response.message
            self.messages.append(assistant)

            if not assistant.tool_calls:
                return assistant.content or ""

            for tc in assistant.tool_calls:
                if self.on_tool_call:
                    self.on_tool_call(tc.name, tc.arguments)
                result = run_tool(self.tools, tc.name, tc.arguments)
                if self.on_tool_result:
                    self.on_tool_result(tc.name, result)
                self.messages.append(
                    Message(
                        role="tool",
                        content=result,
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )

        return "I reached the maximum number of tool rounds. Please try a simpler request or continue the conversation."
