"""FastAPI web server for the Persona interactive app."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from persona.config import Settings, get_settings
from persona.crew import Crew
from persona.llm import provider_status
from persona.personas import get_persona
from persona.projects import BOARD_COLUMNS
from persona.providers import resolve_provider_mode
from persona.rag import DocumentStore

def _static_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "persona" / "web" / "static"
    return Path(__file__).parent / "static"


STATIC_DIR = _static_dir()


class ChatRequest(BaseModel):
    message: str
    persona_id: str = "byte"
    stream: bool = False
    workspace_id: str | None = None


class GroupChatRequest(BaseModel):
    message: str
    mode: str = Field(default="roundtable", pattern="^(roundtable|project)$")
    persona_ids: list[str] | None = None
    project_id: str | None = None
    stream: bool = False
    workspace_id: str | None = None


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
    tools: list[str] = Field(default_factory=lambda: ["remember", "forget", "search_docs"])
    company: str = ""
    instructions: str = ""


class ProviderRequest(BaseModel):
    provider: str = Field(pattern="^(auto|demo|bundled|ollama|openai)$")


class BundledSettingsRequest(BaseModel):
    bundled_model_tier: str | None = Field(default=None, pattern="^(fast|balanced|quality)$")
    bundled_threads: int | None = Field(default=None, ge=0, le=64)
    bundled_gpu_layers: int | None = Field(default=None, ge=-1, le=999)


class ModelTierRequest(BaseModel):
    tier: str = Field(pattern="^(fast|balanced|quality)$")


class WorkspaceCreateRequest(BaseModel):
    name: str
    company: str = ""


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

    def _apply_workspace(workspace_id: str | None) -> None:
        if workspace_id:
            crew.switch_workspace(workspace_id)

    app = FastAPI(title="Persona", description="AI agent workspace", version="0.8.0")

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
        crew.avatars.delete(persona_id)
        return {"deleted": persona_id}

    @app.post("/api/personas/{persona_id}/avatar")
    async def upload_avatar(persona_id: str, file: UploadFile = File(...)):
        try:
            get_persona(persona_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        data = await file.read()
        try:
            url = crew.save_avatar(persona_id, file.filename or "avatar.png", data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"avatar_url": url}

    @app.get("/api/avatars/{filename}")
    def get_avatar(filename: str):
        path = crew.avatars.dir / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Avatar not found")
        return FileResponse(path)

    @app.get("/api/workspaces")
    def list_workspaces():
        return {
            "workspaces": crew.list_workspaces(),
            "active": crew.workspace_manager.get_active_id(),
        }

    @app.post("/api/workspaces")
    def create_workspace(req: WorkspaceCreateRequest):
        return {"workspace": crew.create_workspace(req.name, req.company)}

    @app.post("/api/workspaces/{workspace_id}/activate")
    def activate_workspace(workspace_id: str):
        try:
            return {"workspace": crew.switch_workspace(workspace_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/docs")
    def list_docs():
        return {"documents": crew.list_documents()}

    @app.post("/api/docs")
    async def upload_doc(file: UploadFile = File(...)):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in DocumentStore.SUPPORTED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
        content = (await file.read()).decode("utf-8", errors="replace")
        doc = crew.ingest_document(file.filename or "document.txt", content)
        return {"document": doc}

    @app.delete("/api/docs/{doc_id}")
    def delete_doc(doc_id: str):
        if not crew.delete_document(doc_id):
            raise HTTPException(status_code=404, detail="Document not found")
        return {"deleted": doc_id}

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/status")
    def status():
        ws = crew.team_workspace
        pinfo = provider_status(settings)
        return {
            "provider": pinfo["active"],
            "provider_info": pinfo,
            "model": settings.openai_model
            if pinfo["active"] == "openai"
            else settings.ollama_model
            if pinfo["active"] == "ollama"
            else pinfo.get("bundled", {}).get("active_tier", "built-in"),
            "workspace": str(settings.workspace),
            "board_columns": BOARD_COLUMNS,
            "team_workspace": ws.to_dict() if ws else None,
            "document_count": len(crew.list_documents()),
            "standalone": True,
        }

    @app.post("/api/settings/provider")
    def set_provider(req: ProviderRequest):
        import os

        from persona.bundled import bundled_ready, start_bundled_server, stop_bundled_server

        os.environ["PERSONA_PROVIDER"] = req.provider
        settings.provider = req.provider
        if req.provider == "bundled" and bundled_ready(settings):
            start_bundled_server(settings, force=True)
        elif req.provider != "bundled":
            stop_bundled_server()
        pinfo = provider_status(settings)
        return {"provider_info": pinfo}

    @app.get("/api/bundled/status")
    def bundled_info():
        from persona.bundled import bundled_status

        return bundled_status(settings)

    @app.post("/api/bundled/settings")
    def update_bundled_settings(req: BundledSettingsRequest):
        from persona.bundled import restart_bundled_server, save_bundled_preferences

        updates: dict[str, Any] = {}
        if req.bundled_model_tier is not None:
            updates["bundled_model_tier"] = req.bundled_model_tier
            settings.bundled_model_tier = req.bundled_model_tier
        if req.bundled_threads is not None:
            updates["bundled_threads"] = req.bundled_threads
            settings.bundled_threads = req.bundled_threads
        if req.bundled_gpu_layers is not None:
            updates["bundled_gpu_layers"] = req.bundled_gpu_layers
            settings.bundled_gpu_layers = req.bundled_gpu_layers
        if updates:
            save_bundled_preferences(updates)
        if resolve_provider_mode(settings) == "bundled":
            restart_bundled_server(settings)
        from persona.bundled import bundled_status

        return {"bundled": bundled_status(settings)}

    @app.post("/api/bundled/download")
    def start_model_download(req: ModelTierRequest):
        from persona.bundled import download_model_async, download_status

        if not download_model_async(req.tier, settings):
            raise HTTPException(status_code=409, detail="Download already in progress")
        return download_status()

    @app.get("/api/bundled/download")
    def model_download_status():
        from persona.bundled import download_status

        return download_status()

    @app.post("/api/bundled/restart")
    def restart_bundled():
        from persona.bundled import bundled_status, restart_bundled_server

        ok = restart_bundled_server(settings)
        return {"ok": ok, "bundled": bundled_status(settings)}

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        _apply_workspace(req.workspace_id)
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
        _apply_workspace(req.workspace_id)
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
