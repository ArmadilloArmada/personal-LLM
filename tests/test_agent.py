"""Tests for persona v0.3."""

from pathlib import Path

import pytest
import yaml

from persona.agent import Agent
from persona.config import Settings
from persona.crew import Crew
from persona.custom import load_custom_personas, persona_from_dict, reload_persona_registry
from persona.memory import MemoryStore
from persona.models import Message
from persona.personas import get_persona, list_personas, route_personas
from persona.projects import BOARD_COLUMNS, board_view, extract_tasks_from_plan, move_task, new_task
from persona.tools import ListDirectoryTool, ReadFileTool, RememberTool, WriteFileTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir()
    (personas_dir / "helper.yaml").write_text(
        yaml.dump(
            {
                "id": "helper",
                "name": "Helper",
                "role": "Assistant",
                "company": "TestCo",
                "emoji": "🦾",
                "specialties": ["support"],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def settings(workspace: Path) -> Settings:
    return Settings(provider="ollama", workspace=workspace)


def test_personas_defined():
    assert len(list_personas()) >= 5
    assert get_persona("byte").name == "Byte"


def test_custom_persona_load(workspace: Path, settings: Settings):
    custom = load_custom_personas(settings.workspace_personas_dir)
    assert "helper" in custom
    assert custom["helper"].company == "TestCo"
    reload_persona_registry(settings)
    assert get_persona("helper").is_custom


def test_persona_from_dict():
    p = persona_from_dict({"name": "Bot", "role": "Helper", "emoji": "🤖"})
    assert p.id == "bot"
    assert p.is_custom


def test_route_personas_code():
    assert "byte" in route_personas("help me debug this python function")


def test_extract_tasks_from_plan():
    plan = "1. Byte: Set up API\n2. Nova: Research competitors\n3. Sketch: Write landing copy"
    tasks = extract_tasks_from_plan(plan, ["byte", "nova", "sketch"])
    assert len(tasks) >= 2
    assert any(t["assignee"] == "byte" for t in tasks)


def test_board_move_task():
    tasks = [new_task("A", assignee="byte"), new_task("B", assignee="nova")]
    moved = move_task(tasks, tasks[0]["id"], "in_progress")
    assert moved[0]["column"] == "in_progress"
    board = board_view(moved)
    assert len(board["in_progress"]) == 1


def test_memory_store_add_and_list(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.json")
    assert "Remembered" in store.add("name", "Alice")
    assert "Alice" in store.list_all()


def test_read_file_tool(workspace: Path) -> None:
    tool = ReadFileTool(workspace)
    assert tool.run(path="hello.txt") == "hello world"


def test_agent_iter_chat_events(settings: Settings, monkeypatch):
    from persona.models import LLMResponse, Message

    agent = Agent(settings, persona=get_persona("sunny"))

    def fake_chat(messages, tools=None):
        return LLMResponse(message=Message(role="assistant", content="Hello there friend"))

    monkeypatch.setattr(agent.provider, "chat", fake_chat)
    events = list(agent.iter_chat("Say hi"))
    assert any(e.get("type") == "token" for e in events)
    assert events[-1].get("type") == "done"


def test_crew_catalog(settings: Settings):
    crew = Crew(settings)
    catalog = crew.persona_catalog()
    assert any(p["id"] == "captain" for p in catalog)


def test_crew_add_custom_persona(settings: Settings, tmp_path: Path):
    crew = Crew(settings)
    persona = crew.add_custom_persona(
        {
            "name": "Scout",
            "role": "Sales",
            "company": "Acme",
            "emoji": "📞",
            "specialties": ["sales"],
        }
    )
    assert persona["id"] == "scout"
    assert get_persona("scout").company == "Acme"


def test_web_app_routes():
    from fastapi.testclient import TestClient
    from persona.web.server import create_app

    client = TestClient(create_app(Settings(workspace=Path("."))))
    assert client.get("/api/personas").status_code == 200
    assert client.get("/api/status").json()["board_columns"] == BOARD_COLUMNS
    assert client.get("/").status_code == 200
