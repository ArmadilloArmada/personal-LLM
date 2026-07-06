"""Tests for personal-llm."""

from pathlib import Path

import pytest

from personal_llm.agent import Agent
from personal_llm.config import Settings
from personal_llm.memory import MemoryStore
from personal_llm.models import Message
from personal_llm.tools import ListDirectoryTool, ReadFileTool, RememberTool, WriteFileTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


@pytest.fixture
def settings(workspace: Path) -> Settings:
    return Settings(provider="ollama", workspace=workspace)


def test_memory_store_add_and_list(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    assert "Remembered" in store.add("name", "Alice")
    assert "Alice" in store.list_all()
    assert "Updated" in store.add("name", "Bob")
    assert "Bob" in store.list_all()
    assert "Forgot" in store.remove("name")
    assert "No memory" in store.list_all() or "No memories" in store.list_all()


def test_read_file_tool(workspace: Path) -> None:
    tool = ReadFileTool(workspace)
    assert tool.run(path="hello.txt") == "hello world"
    assert "not found" in tool.run(path="missing.txt")


def test_write_file_tool(workspace: Path) -> None:
    tool = WriteFileTool(workspace)
    result = tool.run(path="out.txt", content="data")
    assert "Wrote" in result
    assert (workspace / "out.txt").read_text(encoding="utf-8") == "data"


def test_list_directory_tool(workspace: Path) -> None:
    tool = ListDirectoryTool(workspace)
    result = tool.run(path=".")
    assert "hello.txt" in result


def test_remember_tool(tmp_path: Path) -> None:
    memory = MemoryStore(tmp_path / "memory.json")
    tool = RememberTool(memory)
    assert "Remembered" in tool.run(key="lang", value="Python")
    assert "Python" in memory.as_context()


def test_agent_session_roundtrip(settings: Settings, tmp_path: Path) -> None:
    agent = Agent(settings)
    agent.messages.append(Message(role="user", content="hi"))
    session_path = tmp_path / "session.json"
    agent.save_session(session_path)

    agent2 = Agent(settings)
    agent2.load_session(session_path)
    assert any(m.role == "user" and m.content == "hi" for m in agent2.messages)


def test_tool_schema_shape(workspace: Path) -> None:
    tool = ReadFileTool(workspace)
    schema = tool.schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "read_file"
