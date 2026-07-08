"""Agent tools."""

from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from persona.memory import MemoryStore
from persona.rag import DocumentStore


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def schema(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        ...


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file in the workspace."

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file within the workspace",
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    def _resolve(self, path: str) -> Path:
        resolved = (self.workspace / path).resolve()
        if not str(resolved).startswith(str(self.workspace)):
            raise ValueError("Path escapes workspace boundary")
        return resolved

    def run(self, **kwargs: Any) -> str:
        try:
            target = self._resolve(kwargs["path"])
            if not target.exists():
                return f"Error: file not found: {kwargs['path']}"
            if not target.is_file():
                return f"Error: not a file: {kwargs['path']}"
            content = target.read_text(encoding="utf-8", errors="replace")
            if len(content) > 50_000:
                return content[:50_000] + "\n\n... (truncated)"
            return content
        except Exception as exc:
            return f"Error reading file: {exc}"


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write or overwrite a file in the workspace."

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path for the file",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full file content to write",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    def _resolve(self, path: str) -> Path:
        resolved = (self.workspace / path).resolve()
        if not str(resolved).startswith(str(self.workspace)):
            raise ValueError("Path escapes workspace boundary")
        return resolved

    def run(self, **kwargs: Any) -> str:
        try:
            target = self._resolve(kwargs["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(kwargs["content"], encoding="utf-8")
            return f"Wrote {len(kwargs['content'])} bytes to {kwargs['path']}"
        except Exception as exc:
            return f"Error writing file: {exc}"


class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "List files and directories in a workspace path."

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path (default: workspace root)",
                        },
                    },
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        try:
            rel = kwargs.get("path", ".")
            target = (self.workspace / rel).resolve()
            if not str(target).startswith(str(self.workspace)):
                return "Error: path escapes workspace boundary"
            if not target.exists():
                return f"Error: directory not found: {rel}"
            if not target.is_dir():
                return f"Error: not a directory: {rel}"
            entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            lines = []
            for entry in entries[:200]:
                prefix = "d" if entry.is_dir() else "f"
                lines.append(f"[{prefix}] {entry.relative_to(self.workspace)}")
            if len(entries) > 200:
                lines.append(f"... and {len(entries) - 200} more")
            return "\n".join(lines) if lines else "(empty directory)"
        except Exception as exc:
            return f"Error listing directory: {exc}"


class RunShellTool(Tool):
    name = "run_shell"
    description = (
        "Run a shell command in the workspace. Use for builds, tests, git, and system tasks."
    )

    def __init__(self, workspace: Path, timeout: int = 120):
        self.workspace = workspace.resolve()
        self.timeout = timeout

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        command = kwargs.get("command", "")
        if not command.strip():
            return "Error: empty command"
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            parts = [f"exit_code: {result.returncode}"]
            if result.stdout:
                stdout = result.stdout
                if len(stdout) > 20_000:
                    stdout = stdout[:20_000] + "\n... (truncated)"
                parts.append(f"stdout:\n{stdout}")
            if result.stderr:
                stderr = result.stderr
                if len(stderr) > 10_000:
                    stderr = stderr[:10_000] + "\n... (truncated)"
                parts.append(f"stderr:\n{stderr}")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {self.timeout}s"
        except Exception as exc:
            return f"Error running command: {exc}"


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch a URL and return its text content (HTML stripped to plain text)."

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "HTTP or HTTPS URL to fetch",
                        },
                    },
                    "required": ["url"],
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        url = kwargs.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return "Error: only http/https URLs are allowed"
        try:
            response = httpx.get(url, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            text = response.text
            # crude HTML tag stripping
            import re

            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 15_000:
                text = text[:15_000] + "... (truncated)"
            return text or "(empty response)"
        except Exception as exc:
            return f"Error fetching URL: {exc}"


class RememberTool(Tool):
    name = "remember"
    description = "Store a fact or preference to remember across future conversations."

    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Short label for the memory (e.g. 'name', 'editor')",
                        },
                        "value": {
                            "type": "string",
                            "description": "The fact or preference to remember",
                        },
                    },
                    "required": ["key", "value"],
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        return self.memory.add(kwargs["key"], kwargs["value"])


class ForgetTool(Tool):
    name = "forget"
    description = "Remove a stored memory by key."

    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Memory key to remove",
                        },
                    },
                    "required": ["key"],
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        return self.memory.remove(kwargs["key"])


class SearchDocsTool(Tool):
    name = "search_docs"
    description = "Search ingested company documents in the team workspace knowledge base."

    def __init__(self, doc_store: DocumentStore | None):
        self.doc_store = doc_store

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in company docs",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        if not self.doc_store:
            return "Error: no document knowledge base configured for this workspace."
        query = kwargs.get("query", "")
        hits = self.doc_store.search(query, top_k=5)
        if not hits:
            return "No matching documents found."
        lines = []
        for hit in hits:
            lines.append(f"[{hit['filename']}] (score {hit['score']})\n{hit['snippet']}")
        return "\n\n---\n\n".join(lines)


def build_tools(
    workspace: Path,
    memory: MemoryStore,
    doc_store: DocumentStore | None = None,
) -> list[Tool]:
    return [
        ReadFileTool(workspace),
        WriteFileTool(workspace),
        ListDirectoryTool(workspace),
        RunShellTool(workspace),
        WebFetchTool(),
        SearchDocsTool(doc_store),
        RememberTool(memory),
        ForgetTool(memory),
    ]


def tool_schemas(tools: list[Tool]) -> list[dict[str, Any]]:
    return [t.schema() for t in tools]


def run_tool(
    tools: list[Tool],
    name: str,
    arguments: dict[str, Any],
    *,
    allow_shell: bool = False,
) -> str:
    if name == "run_shell" and not allow_shell:
        command = arguments.get("command", "")
        return (
            "Error: shell commands are disabled. "
            f"The agent wanted to run: {command!r}. "
            "Enable shell commands in Settings → Safety if you trust this action."
        )
    for tool in tools:
        if tool.name == name:
            return tool.run(**arguments)
    return f"Error: unknown tool '{name}'"
