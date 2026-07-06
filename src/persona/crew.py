"""Crew orchestration — solo, roundtable, project modes, and kanban board."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from persona.agent import Agent
from persona.config import Settings
from persona.custom import reload_persona_registry
from persona.llm import get_provider
from persona.models import Message
from persona.personas import (
    CAPTAIN,
    PERSONAS,
    get_persona,
    persona_to_dict,
    route_personas,
)
from persona.projects import BOARD_COLUMNS, board_view, extract_tasks_from_plan, move_task, new_task


@dataclass
class CrewMessage:
    persona_id: str
    content: str
    phase: str = "response"  # plan | delegate | response | summary


@dataclass
class CrewResult:
    mode: str
    messages: list[CrewMessage] = field(default_factory=list)
    project_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "project_id": self.project_id,
            "messages": [
                {"persona_id": m.persona_id, "content": m.content, "phase": m.phase}
                for m in self.messages
            ],
        }


@dataclass
class ProjectState:
    id: str
    title: str
    goal: str
    status: str
    created_at: str
    updated_at: str
    history: list[dict] = field(default_factory=list)
    tasks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": self.history,
            "tasks": self.tasks,
            "board": board_view(self.tasks),
        }


class Crew:
    def __init__(self, settings: Settings):
        self.settings = settings
        reload_persona_registry(settings)
        self.provider = get_provider(settings)

    def solo(self, persona_id: str, message: str) -> CrewResult:
        persona = get_persona(persona_id)
        agent = Agent(self.settings, persona=persona)
        reply = agent.chat(message)
        return CrewResult(
            mode="solo",
            messages=[CrewMessage(persona_id=persona.id, content=reply)],
        )

    def iter_solo(self, persona_id: str, message: str) -> Iterator[dict[str, Any]]:
        persona = get_persona(persona_id)
        agent = Agent(self.settings, persona=persona)
        yield {"type": "persona_start", "persona_id": persona.id, "phase": "response"}
        for event in agent.iter_chat(message):
            yield event

    def roundtable(self, message: str, persona_ids: list[str] | None = None) -> CrewResult:
        ids = persona_ids or route_personas(message)
        results: list[CrewMessage] = []
        context = (
            f"The user asked: {message}\n\nOther crew members may also respond. "
            "Give your unique perspective in character. Keep it focused (2-4 paragraphs max)."
        )

        for pid in ids:
            content = self._persona_reply(pid, context)
            results.append(CrewMessage(persona_id=pid, content=content, phase="response"))

        return CrewResult(mode="roundtable", messages=results)

    def iter_roundtable(self, message: str, persona_ids: list[str] | None = None) -> Iterator[dict[str, Any]]:
        ids = persona_ids or route_personas(message)
        context = (
            f"The user asked: {message}\n\nOther crew members may also respond. "
            "Give your unique perspective in character. Keep it focused (2-4 paragraphs max)."
        )
        for pid in ids:
            yield {"type": "persona_start", "persona_id": pid, "phase": "response"}
            persona = get_persona(pid)
            prompt = (
                f"{context}\n\nYou are {persona.name} ({persona.role}). "
                f"Respond in character as {persona.name}."
            )
            if persona.tools:
                agent = Agent(self.settings, persona=persona)
                for event in agent.iter_chat(prompt):
                    yield event
            else:
                response = self.provider.chat(
                    [
                        Message(role="system", content=persona.system_prompt),
                        Message(role="user", content=prompt),
                    ]
                )
                text = response.message.content or ""
                for chunk in _chunk_text(text):
                    yield {"type": "token", "text": chunk}
                yield {"type": "done", "persona_id": pid}
        yield {"type": "complete", "mode": "roundtable"}

    def project(self, message: str, project_id: str | None = None) -> CrewResult:
        project = self._load_or_create_project(message, project_id)
        results: list[CrewMessage] = []

        plan_prompt = (
            f"Project request from user:\n{message}\n\n"
            "Create a concise project plan with 2-4 tasks. "
            "For each task, name which crew member should own it and what they should deliver."
        )
        captain_agent = Agent(self.settings, persona=CAPTAIN)
        plan = captain_agent.chat(plan_prompt)
        results.append(CrewMessage(persona_id="captain", content=plan, phase="plan"))

        delegate_prompt = (
            f"Given this plan:\n{plan}\n\n"
            f"Original user request: {message}\n\n"
            "List each crew member you are activating and their assignment in one short paragraph."
        )
        delegation = captain_agent.chat(delegate_prompt)
        results.append(CrewMessage(persona_id="captain", content=delegation, phase="delegate"))

        worker_ids = self._workers_from_plan(plan)
        worker_context = f"User project goal: {message}\n\nCaptain's plan:\n{plan}\n\nYour assignment:"

        for pid in worker_ids:
            if pid == "captain":
                continue
            task_prompt = (
                f"{worker_context}\n"
                f"Execute your part as {get_persona(pid).name}. Be concrete and actionable."
            )
            content = self._persona_reply(pid, task_prompt)
            results.append(CrewMessage(persona_id=pid, content=content, phase="response"))

        summary_prompt = (
            f"User goal: {message}\n\nPlan:\n{plan}\n\n"
            "Crew contributions:\n"
            + "\n---\n".join(
                f"{m.persona_id}: {m.content}" for m in results if m.phase == "response"
            )
            + "\n\nSynthesize a final project brief: what was done, next steps, and who owns what."
        )
        summary = captain_agent.chat(summary_prompt)
        results.append(CrewMessage(persona_id="captain", content=summary, phase="summary"))

        project.history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_message": message,
                "crew_result": [m.__dict__ for m in results],
            }
        )
        project.tasks = extract_tasks_from_plan(plan, worker_ids)
        project.status = "active"
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_project(project)

        return CrewResult(mode="project", messages=results, project_id=project.id)

    def iter_project(self, message: str, project_id: str | None = None) -> Iterator[dict[str, Any]]:
        result = self.project(message, project_id)
        for msg in result.messages:
            yield {"type": "persona_start", "persona_id": msg.persona_id, "phase": msg.phase}
            for chunk in _chunk_text(msg.content):
                yield {"type": "token", "text": chunk}
            yield {"type": "done", "persona_id": msg.persona_id}
        yield {"type": "project", "project_id": result.project_id}
        yield {"type": "complete", "mode": "project"}

    def _persona_reply(self, persona_id: str, prompt: str) -> str:
        persona = get_persona(persona_id)
        if persona.tools:
            return Agent(self.settings, persona=persona).chat(prompt)
        response = self.provider.chat(
            [
                Message(role="system", content=persona.system_prompt),
                Message(role="user", content=prompt),
            ]
        )
        return response.message.content or ""

    def _workers_from_plan(self, plan: str) -> list[str]:
        text = plan.lower()
        workers = []
        for pid in PERSONAS:
            if pid == "captain":
                continue
            persona = PERSONAS[pid]
            if pid in text or persona.name.lower() in text:
                workers.append(pid)
        if not workers:
            workers = route_personas(plan)
        return list(dict.fromkeys(workers))

    def _load_or_create_project(self, message: str, project_id: str | None) -> ProjectState:
        if project_id:
            path = self.settings.projects_dir / f"{project_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if "tasks" not in data:
                    data["tasks"] = []
                return ProjectState(**data)

        now = datetime.now(timezone.utc).isoformat()
        title = message[:60] + ("..." if len(message) > 60 else "")
        return ProjectState(
            id=project_id or str(uuid.uuid4())[:8],
            title=title,
            goal=message,
            status="new",
            created_at=now,
            updated_at=now,
        )

    def _save_project(self, project: ProjectState) -> None:
        path = self.settings.projects_dir / f"{project.id}.json"
        path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")

    def get_project(self, project_id: str) -> dict | None:
        path = self.settings.projects_dir / f"{project_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data["board"] = board_view(data.get("tasks", []))
        return data

    def update_task(self, project_id: str, task_id: str, column: str, order: int | None = None) -> dict | None:
        project = self._load_or_create_project("", project_id)
        if not (self.settings.projects_dir / f"{project_id}.json").exists():
            return None
        project.tasks = move_task(project.tasks, task_id, column, order)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_project(project)
        return project.to_dict()

    def add_task(
        self,
        project_id: str,
        title: str,
        assignee: str = "captain",
        column: str = "backlog",
    ) -> dict | None:
        if not (self.settings.projects_dir / f"{project_id}.json").exists():
            return None
        project = self._load_or_create_project("", project_id)
        project.tasks.append(new_task(title=title, assignee=assignee, column=column, order=len(project.tasks)))
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_project(project)
        return project.to_dict()

    def list_projects(self) -> list[dict]:
        projects = []
        for path in sorted(self.settings.projects_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["board"] = board_view(data.get("tasks", []))
                projects.append(data)
            except Exception:
                continue
        return projects

    def persona_catalog(self) -> list[dict]:
        return [persona_to_dict(p) for p in PERSONAS.values()]

    def add_custom_persona(self, data: dict) -> dict:
        from persona.custom import persona_from_dict, save_custom_persona

        persona = persona_from_dict(data)
        save_custom_persona(persona, self.settings.custom_personas_dir)
        reload_persona_registry(self.settings)
        return persona_to_dict(persona)

    def remove_custom_persona(self, persona_id: str) -> bool:
        from persona.custom import BUILTIN_IDS, delete_custom_persona

        if persona_id in BUILTIN_IDS:
            return False
        deleted = delete_custom_persona(persona_id, self.settings.custom_personas_dir)
        deleted = delete_custom_persona(persona_id, self.settings.workspace_personas_dir) or deleted
        reload_persona_registry(self.settings)
        return deleted


def _chunk_text(text: str, size: int = 24) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]
