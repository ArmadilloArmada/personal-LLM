"""Persist web chat history per workspace and mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ChatHistoryStore:
    MAX_MESSAGES = 200

    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, list[dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _key(self, workspace_id: str, mode: str, persona_id: str | None = None) -> str:
        if mode == "solo" and persona_id:
            return f"{workspace_id}:solo:{persona_id}"
        return f"{workspace_id}:{mode}"

    def get(self, workspace_id: str, mode: str, persona_id: str | None = None) -> list[dict[str, Any]]:
        return list(self._data.get(self._key(workspace_id, mode, persona_id), []))

    def save(
        self,
        workspace_id: str,
        mode: str,
        messages: list[dict[str, Any]],
        persona_id: str | None = None,
    ) -> None:
        key = self._key(workspace_id, mode, persona_id)
        self._data[key] = messages[-self.MAX_MESSAGES :]
        self._persist()

    def append(
        self,
        workspace_id: str,
        mode: str,
        message: dict[str, Any],
        persona_id: str | None = None,
    ) -> list[dict[str, Any]]:
        key = self._key(workspace_id, mode, persona_id)
        history = self._data.get(key, [])
        history.append(message)
        history = history[-self.MAX_MESSAGES :]
        self._data[key] = history
        self._persist()
        return history

    def clear(self, workspace_id: str, mode: str, persona_id: str | None = None) -> None:
        self._data.pop(self._key(workspace_id, mode, persona_id), None)
        self._persist()

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
