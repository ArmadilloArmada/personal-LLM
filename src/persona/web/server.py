"""FastAPI web server for the Persona interactive app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from persona.config import Settings, get_settings
from persona.crew import Crew
from persona.personas import get_persona
from persona.projects import BOARD_COLUMNS

STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    persona_id: str = "byte"
    stream: bool = False


class GroupChatRequest(BaseModel):
    message: str
    mode: str = Field(default="roundtable", pattern="^(roundtable|project)$")
    persona_ids: list[str] | None = None
    project_id: str | None = None
    stream: bool = False


class CustomPersonaRequest(BaseModel):
    id: str | None = None
    name: str
    role: str
    tagline: str = ""
    color: str = "#6366F1"
    accent: str = "#312E81"
    emoji: str = "🤖"
    shape: str = "hexagon"
    personality: str = ""
    specialties: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=lambda: ["remember", "forget"])
    company: str = ""
    instructions: str = ""


class TaskMoveRequest(BaseModel):
    column: str
    order: int | None = None


class TaskCreateRequest(BaseModel):
    title: str
    assignee: str = "captain"
    column: str = "backlog"


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    crew = Crew(settings)

    app = FastAPI(title="Persona", description="Cartoon AI crew", version="0.3.0")

    @app.get("/api/personas")
    def list_personas():
        return {"personas": crew.persona_catalog()}

    @app.post("/api/personas")
    def create_persona(req: CustomPersonaRequest):
        persona = crew.add_custom_persona(req.model_dump())
        return {"persona": persona}

    @app.delete("/api/personas/{persona_id}")
    def delete_persona(persona_id: str):
        if not crew.remove_custom_persona(persona_id):
            raise HTTPException(status_code=404, detail="Custom persona not found or is built-in")
        return {"deleted": persona_id}

    @app.get("/api/status")
    def status():
        return {
            "provider": settings.provider,
            "model": settings.openai_model
            if settings.provider == "openai"
            else settings.ollama_model,
            "workspace": str(settings.workspace),
            "board_columns": BOARD_COLUMNS,
        }

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        try:
            get_persona(req.persona_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        if req.stream:
            def generate():
                try:
                    for event in crew.iter_solo(req.persona_id, req.message):
                        yield _sse_event(event.get("type", "message"), event)
                except Exception as exc:
                    yield _sse_event("error", {"message": str(exc)})

            return StreamingResponse(generate(), media_type="text/event-stream")

        return crew.solo(req.persona_id, req.message).to_dict()

    @app.post("/api/group")
    def group_chat(req: GroupChatRequest):
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        if req.stream:
            def generate():
                try:
                    iterator = (
                        crew.iter_project(req.message, req.project_id)
                        if req.mode == "project"
                        else crew.iter_roundtable(req.message, req.persona_ids)
                    )
                    for event in iterator:
                        yield _sse_event(event.get("type", "message"), event)
                except Exception as exc:
                    yield _sse_event("error", {"message": str(exc)})

            return StreamingResponse(generate(), media_type="text/event-stream")

        if req.mode == "project":
            result = crew.project(req.message, req.project_id)
        else:
            result = crew.roundtable(req.message, req.persona_ids)
        return result.to_dict()

    @app.get("/api/projects")
    def projects():
        return {"projects": crew.list_projects()}

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        project = crew.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @app.patch("/api/projects/{project_id}/tasks/{task_id}")
    def move_task(project_id: str, task_id: str, req: TaskMoveRequest):
        project = crew.update_task(project_id, task_id, req.column, req.order)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @app.post("/api/projects/{project_id}/tasks")
    def create_task(project_id: str, req: TaskCreateRequest):
        project = crew.add_task(project_id, req.title, req.assignee, req.column)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
