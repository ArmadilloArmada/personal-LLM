"""Persistent memory for facts the agent should remember across sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, path: Path):
        self.path = path
        self._entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._entries = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self._entries = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._entries, indent=2), encoding="utf-8")

    def add(self, key: str, value: str) -> str:
        now = datetime.now(timezone.utc).isoformat()
        for entry in self._entries:
            if entry["key"].lower() == key.lower():
                entry["value"] = value
                entry["updated_at"] = now
                self._save()
                return f"Updated memory: {key}"

        self._entries.append({"key": key, "value": value, "updated_at": now})
        self._save()
        return f"Remembered: {key}"

    def remove(self, key: str) -> str:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e["key"].lower() != key.lower()]
        self._save()
        if len(self._entries) < before:
            return f"Forgot: {key}"
        return f"No memory found for: {key}"

    def list_all(self) -> str:
        if not self._entries:
            return "No memories stored yet."
        lines = []
        for e in self._entries:
            lines.append(f"- {e['key']}: {e['value']}")
        return "\n".join(lines)

    def as_context(self) -> str:
        if not self._entries:
            return ""
        lines = ["Known facts about the user and preferences:"]
        for e in self._entries:
            lines.append(f"- {e['key']}: {e['value']}")
        return "\n".join(lines)
