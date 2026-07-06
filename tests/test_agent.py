"""Tests for persona."""

from pathlib import Path

import pytest

from persona.agent import Agent
from persona.config import Settings
from persona.crew import Crew
from persona.memory import MemoryStore
from persona.models import Message
from persona.personas import get_persona, list_personas, route_personas
from persona.tools import ListDirectoryTool, ReadFileTool, RememberTool, WriteFileTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


@pytest.fixture
def settings(workspace: Path) -> Settings:
    return Settings(provider="ollama", workspace=workspace)


def test_personas_defined():
    personas = list_personas()
    assert len(personas) >= 5
    byte = get_persona("byte")
    assert byte.name == "Byte"
    assert "read_file" in byte.tools


def test_route_personas_code():
    ids = route_personas("help me debug this python function")
    assert "byte" in ids


def test_route_personas_project():
    ids = route_personas("help me plan a new mobile app project")
    assert "captain" in ids


def test_memory_store_add_and_list(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    assert "Remembered" in store.add("name", "Alice")
    assert "Alice" in store.list_all()
    assert "Updated" in store.add("name", "Bob")
    assert "Bob" in store.list_all()
    assert "Forgot" in store.remove("name")


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
    agent = Agent(settings, persona=get_persona("byte"))
    agent.messages.append(Message(role="user", content="hi"))
    session_path = tmp_path / "session.json"
    agent.save_session(session_path)

    agent2 = Agent(settings, persona=get_persona("byte"))
    agent2.load_session(session_path)
    assert any(m.role == "user" and m.content == "hi" for m in agent2.messages)


def test_crew_catalog():
    crew = Crew(Settings(workspace=Path(".")))
    catalog = crew.persona_catalog()
    assert any(p["id"] == "captain" for p in catalog)


def test_web_app_import():
    from persona.web.server import create_app

    app = create_app()
    assert app.title == "Persona"
