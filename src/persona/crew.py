"""Crew orchestration — solo, roundtable, and project modes."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from persona.agent import Agent
from persona.config import Settings
from persona.llm import get_provider
from persona.models import Message
from persona.personas import (
    CAPTAIN,
    PERSONAS,
    get_persona,
    persona_to_dict,
    route_personas,
)


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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": self.history,
        }


class Crew:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = get_provider(settings)

    def solo(self, persona_id: str, message: str) -> CrewResult:
        persona = get_persona(persona_id)
        agent = Agent(self.settings, persona=persona)
        reply = agent.chat(message)
        return CrewResult(
            mode="solo",
            messages=[CrewMessage(persona_id=persona.id, content=reply)],
        )

    def roundtable(self, message: str, persona_ids: list[str] | None = None) -> CrewResult:
        ids = persona_ids or route_personas(message)
        results: list[CrewMessage] = []

        context = f"The user asked: {message}\n\nOther crew members may also respond. "
        context += "Give your unique perspective in character. Keep it focused (2-4 paragraphs max)."

        for pid in ids:
            persona = get_persona(pid)
            prompt = (
                f"{context}\n\nYou are {persona.name} ({persona.role}). "
                f"Respond in character as {persona.name}."
            )
            if persona.tools:
                agent = Agent(self.settings, persona=persona)
                content = agent.chat(prompt)
            else:
                response = self.provider.chat(
                    [
                        Message(role="system", content=persona.system_prompt),
                        Message(role="user", content=prompt),
                    ]
                )
                content = response.message.content or ""

            results.append(CrewMessage(persona_id=pid, content=content, phase="response"))

        return CrewResult(mode="roundtable", messages=results)

    def project(self, message: str, project_id: str | None = None) -> CrewResult:
        """Captain-led project mode: plan → delegate → execute → summarize."""
        project = self._load_or_create_project(message, project_id)
        results: list[CrewMessage] = []

        plan_prompt = (
            f"Project request from user:\n{message}\n\n"
            "Create a concise project plan with 2-4 tasks. "
            "For each task, name which crew member should own it "
            "(byte, sunny, nova, sketch) and what they should deliver."
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
            persona = get_persona(pid)
            task_prompt = (
                f"{worker_context}\n"
                f"Execute your part as {persona.name}. Be concrete and actionable."
            )
            if persona.tools:
                agent = Agent(self.settings, persona=persona)
                content = agent.chat(task_prompt)
            else:
                response = self.provider.chat(
                    [
                        Message(role="system", content=persona.system_prompt),
                        Message(role="user", content=task_prompt),
                    ]
                )
                content = response.message.content or ""

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
        project.status = "active"
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_project(project)

        return CrewResult(mode="project", messages=results, project_id=project.id)

    def _workers_from_plan(self, plan: str) -> list[str]:
        text = plan.lower()
        workers = []
        for pid in ["byte", "nova", "sketch", "sunny"]:
            if pid in text or get_persona(pid).name.lower() in text:
                workers.append(pid)
        if not workers:
            workers = route_personas(plan)
        if "captain" not in workers:
            workers = ["captain", *workers]
        return list(dict.fromkeys(workers))

    def _load_or_create_project(self, message: str, project_id: str | None) -> ProjectState:
        if project_id:
            path = self.settings.projects_dir / f"{project_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return ProjectState(**data)

        now = datetime.now(timezone.utc).isoformat()
        title = message[:60] + ("..." if len(message) > 60 else "")
        project = ProjectState(
            id=project_id or str(uuid.uuid4())[:8],
            title=title,
            goal=message,
            status="new",
            created_at=now,
            updated_at=now,
        )
        self._save_project(project)
        return project

    def _save_project(self, project: ProjectState) -> None:
        path = self.settings.projects_dir / f"{project.id}.json"
        path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")

    def list_projects(self) -> list[dict]:
        projects = []
        for path in sorted(self.settings.projects_dir.glob("*.json"), reverse=True):
            try:
                projects.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return projects

    @staticmethod
    def persona_catalog() -> list[dict]:
        return [persona_to_dict(p) for p in PERSONAS.values()]
