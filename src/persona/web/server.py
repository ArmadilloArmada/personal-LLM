"""FastAPI web server for the Persona interactive app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from persona.config import Settings, get_settings
from persona.crew import Crew
from persona.personas import get_persona

STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    persona_id: str = "byte"


class GroupChatRequest(BaseModel):
    message: str
    mode: str = Field(default="roundtable", pattern="^(roundtable|project)$")
    persona_ids: list[str] | None = None
    project_id: str | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    crew = Crew(settings)

    app = FastAPI(title="Persona", description="Cartoon AI crew", version="0.2.0")

    @app.get("/api/personas")
    def list_personas():
        return {"personas": crew.persona_catalog()}

    @app.get("/api/status")
    def status():
        return {
            "provider": settings.provider,
            "model": settings.openai_model
            if settings.provider == "openai"
            else settings.ollama_model,
            "workspace": str(settings.workspace),
        }

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        try:
            get_persona(req.persona_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        result = crew.solo(req.persona_id, req.message)
        return result.to_dict()

    @app.post("/api/group")
    def group_chat(req: GroupChatRequest):
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if req.mode == "project":
            result = crew.project(req.message, req.project_id)
        else:
            result = crew.roundtable(req.message, req.persona_ids)
        return result.to_dict()

    @app.get("/api/projects")
    def projects():
        return {"projects": crew.list_projects()}

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
