"""Tests for persona v0.4."""

from pathlib import Path

import pytest

from persona.agent import Agent
from persona.avatars import AvatarStore
from persona.config import Settings
from persona.crew import Crew
from persona.custom import load_custom_personas, persona_from_dict, reload_persona_registry
from persona.memory import MemoryStore
from persona.models import Message
from persona.personas import get_persona, list_personas, route_personas
from persona.projects import board_view, extract_tasks_from_plan, move_task, new_task
from persona.rag import DocumentStore
from persona.workspace import WorkspaceManager


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir()
    return tmp_path


@pytest.fixture
def settings(workspace: Path, tmp_path: Path) -> Settings:
    return Settings(provider="ollama", workspace=workspace)


def test_workspace_create_and_switch(tmp_path: Path):
    manager = WorkspaceManager(tmp_path)
    ws = manager.create("Acme Team", company="Acme Corp")
    assert ws.name == "Acme Team"
    manager.set_active(ws.id)
    assert manager.get_active_id() == ws.id


def test_rag_ingest_and_search(tmp_path: Path):
    store = DocumentStore(tmp_path / "ws1")
    store.ingest(
        "handbook.md",
        "Acme Corp pricing is $12 per user per month for Pro plan. Enterprise has SLA support.",
    )
    hits = store.search("pricing Pro plan")
    assert hits
    assert "pricing" in hits[0]["snippet"].lower() or "12" in hits[0]["snippet"]


def test_rag_context_block(tmp_path: Path):
    store = DocumentStore(tmp_path / "ws2")
    store.ingest("policy.txt", "Remote work is allowed on Fridays for all employees.")
    ctx = store.context_block("remote work policy")
    assert "Remote work" in ctx


def test_avatar_store(tmp_path: Path):
    avatars = AvatarStore(tmp_path)
    path = avatars.save("byte", "byte.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    assert path.exists()
    assert avatars.url_for("byte") == "/api/avatars/byte.png"


def test_search_docs_tool(settings: Settings, tmp_path: Path):
    from persona.tools import SearchDocsTool

    store = DocumentStore(tmp_path)
    store.ingest("faq.md", "Our refund policy allows returns within 30 days.")
    tool = SearchDocsTool(store)
    result = tool.run(query="refund")
    assert "30 days" in result


def test_agent_with_doc_context(settings: Settings, tmp_path: Path, monkeypatch):
    from persona.models import LLMResponse, Message

    store = DocumentStore(tmp_path)
    store.ingest("guide.md", "The codename for Project Phoenix is BLUEBIRD.")
    agent = Agent(settings, persona=get_persona("nova"), doc_store=store)

    def fake_chat(messages, tools=None):
        # user question should have doc context injected as extra system message
        assert any("BLUEBIRD" in (m.content or "") for m in messages if m.role == "system")
        return LLMResponse(message=Message(role="assistant", content="The codename is BLUEBIRD."))

    monkeypatch.setattr(agent.provider, "chat", fake_chat)
    events = list(agent.iter_chat("What is the codename for Project Phoenix?"))
    assert any(e.get("type") == "token" for e in events)


def test_project_has_workspace_id(settings: Settings):
    crew = Crew(settings)
    ws_id = crew.workspace_manager.get_active_id()
    project = crew._load_or_create_project("Build landing page", None)
    assert project.workspace_id == ws_id


def test_personas_defined():
    assert len(list_personas()) >= 5


def test_extract_tasks_from_plan():
    plan = "1. Byte: Build API\n2. Nova: Research market"
    tasks = extract_tasks_from_plan(plan, ["byte", "nova"])
    assert len(tasks) >= 1


def test_board_move_task():
    tasks = [new_task("A", assignee="byte")]
    moved = move_task(tasks, tasks[0]["id"], "done")
    assert moved[0]["column"] == "done"


def test_web_app_v04_routes():
    from fastapi.testclient import TestClient
    from persona.web.server import create_app

    client = TestClient(create_app(Settings(workspace=Path("."))))
    assert client.get("/api/workspaces").status_code == 200
    assert client.get("/api/docs").status_code == 200
    status = client.get("/api/status").json()
    assert "team_workspace" in status
    assert "document_count" in status
