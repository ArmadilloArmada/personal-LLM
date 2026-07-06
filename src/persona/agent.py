"""Agent loop with persona identity, tool execution, and streaming events."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from persona.config import Settings
from persona.llm import get_provider
from persona.memory import MemoryStore
from persona.models import Message
from persona.personas import DEFAULT_PERSONA, Persona, get_persona
from persona.rag import DocumentStore
from persona.tools import Tool, build_tools, run_tool, tool_schemas
from persona.workspace import TeamWorkspace, WorkspaceManager


class Agent:
    def __init__(
        self,
        settings: Settings,
        persona: Persona | None = None,
        team_workspace: TeamWorkspace | None = None,
        doc_store: DocumentStore | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
    ):
        self.settings = settings
        self.persona = persona or DEFAULT_PERSONA
        self.team_workspace = team_workspace
        self.doc_store = doc_store
        self.workspace = settings.workspace.resolve()
        self.memory = MemoryStore(settings.memory_file)
        all_tools = build_tools(self.workspace, self.memory, doc_store)
        allowed = set(self.persona.tools)
        self.tools: list[Tool] = [t for t in all_tools if t.name in allowed]
        self.provider = get_provider(settings)
        self.messages: list[Message] = []
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self._init_system()

    def _init_system(self) -> None:
        memory_context = self.memory.as_context()
        content = self.persona.system_prompt
        if memory_context:
            content += f"\n\n{memory_context}"
        if self.team_workspace:
            content += (
                f"\n\nTeam workspace: {self.team_workspace.name}"
                f"{f' ({self.team_workspace.company})' if self.team_workspace.company else ''}"
                f"\nMembers: {', '.join(self.team_workspace.members)}"
            )
        if self.doc_store and self.doc_store.list_documents():
            docs = ", ".join(d["filename"] for d in self.doc_store.list_documents()[:8])
            content += f"\n\nCompany knowledge base includes: {docs}"
            content += "\nUse search_docs to find relevant policy, product, or company information."
        content += f"\n\nFilesystem workspace: {self.workspace}"
        content += f"\nCurrent time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        self.messages = [Message(role="system", content=content)]

    def reset(self) -> None:
        self._init_system()

    def load_session(self, path: Path) -> None:
        from persona.models import ToolCall

        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("persona_id"):
            self.persona = get_persona(data["persona_id"])
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
        path.write_text(
            json.dumps({"persona_id": self.persona.id, "messages": serializable}, indent=2),
            encoding="utf-8",
        )

    def chat(self, user_input: str) -> str:
        parts: list[str] = []
        for event in self.iter_chat(user_input):
            if event.get("type") == "token":
                parts.append(event.get("text", ""))
        return "".join(parts)

    def iter_chat(self, user_input: str) -> Iterator[dict[str, Any]]:
        self.messages.append(Message(role="user", content=user_input))

        if self.doc_store:
            doc_context = self.doc_store.context_block(user_input)
            if doc_context:
                self.messages.append(
                    Message(role="system", content=doc_context)
                )

        schemas = tool_schemas(self.tools) if self.tools else None

        for _ in range(self.settings.max_tool_rounds):
            response = self.provider.chat(self.messages, tools=schemas)
            assistant = response.message
            self.messages.append(assistant)

            if not assistant.tool_calls:
                text = assistant.content or ""
                for chunk in _chunk_text(text):
                    yield {"type": "token", "text": chunk}
                yield {"type": "done", "persona_id": self.persona.id}
                return

            for tc in assistant.tool_calls:
                yield {"type": "tool", "name": tc.name, "args": tc.arguments}
                if self.on_tool_call:
                    self.on_tool_call(tc.name, tc.arguments)
                result = run_tool(self.tools, tc.name, tc.arguments)
                if self.on_tool_result:
                    self.on_tool_result(tc.name, result)
                yield {"type": "tool_result", "name": tc.name, "result": result[:300]}
                self.messages.append(
                    Message(
                        role="tool",
                        content=result,
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )

        yield {
            "type": "token",
            "text": "I reached the maximum number of tool rounds. Please try a simpler request.",
        }
        yield {"type": "done", "persona_id": self.persona.id}


def _chunk_text(text: str, size: int = 24) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


def build_agent_context(settings: Settings) -> tuple[TeamWorkspace | None, DocumentStore | None]:
    manager = WorkspaceManager(settings.data_dir)
    ws_id = manager.get_active_id()
    team_ws = manager.get(ws_id)
    doc_store = DocumentStore(manager.workspace_dir(ws_id))
    return team_ws, doc_store
