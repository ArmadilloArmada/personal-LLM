"""FastAPI web server for the Persona interactive app."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from persona.chat_history import ChatHistoryStore
from persona.config import Settings, get_settings
from persona.crew import Crew
from persona.llm import provider_status
from persona.memory import MemoryStore
from persona.personas import get_persona
from persona.projects import BOARD_COLUMNS
from persona.providers import ollama_available, ollama_installed_models, ollama_ready
from persona.rag import DocumentStore
from persona.web.brain_routes import augment_message_with_rag, capture_turn, register_brain_routes
from persona.user_config import get_user_config, save_user_config

APP_VERSION = "1.0.2"
GITHUB_REPO = "ArmadilloArmada/CursorProjects"
RELEASE_ASSET = "Persona-Windows-portable.zip"

def _static_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "persona" / "web" / "static"
    return Path(__file__).parent / "static"


STATIC_DIR = _static_dir()
_INDEX_HTML: str | None = None


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next) -> StarletteResponse:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/") or path.startswith("/brain/assets/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


def _index_html() -> str:
    global _INDEX_HTML
    if _INDEX_HTML is None:
        raw = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        _INDEX_HTML = raw.replace("__APP_VERSION__", APP_VERSION)
    return _INDEX_HTML


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
    provider: str = Field(pattern="^(auto|demo|ollama|openai)$")


class SettingsRequest(BaseModel):
    provider: str = Field(default="auto", pattern="^(auto|demo|ollama|openai)$")
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    allow_shell_commands: bool | None = None
    onboarding_completed: bool | None = None


class MemoryRequest(BaseModel):
    key: str
    value: str


class ChatHistoryRequest(BaseModel):
    workspace_id: str = "default"
    mode: str = "solo"
    persona_id: str | None = None
    messages: list[dict[str, Any]] | None = None


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
    memory = MemoryStore(settings.memory_file)
    history = ChatHistoryStore(settings.chat_history_file)

    def _apply_workspace(workspace_id: str | None) -> None:
        if workspace_id:
            crew.switch_workspace(workspace_id)

    def _apply_settings(req: SettingsRequest) -> dict[str, Any]:
        settings.provider = req.provider
        if req.ollama_base_url is not None:
            settings.ollama_base_url = req.ollama_base_url
        if req.ollama_model is not None:
            settings.ollama_model = req.ollama_model
        if req.openai_base_url is not None:
            settings.openai_base_url = req.openai_base_url
        if req.openai_model is not None:
            settings.openai_model = req.openai_model
        if req.openai_api_key is not None and req.openai_api_key.strip():
            settings.openai_api_key = req.openai_api_key.strip()
        if req.allow_shell_commands is not None:
            settings.allow_shell_commands = req.allow_shell_commands
        if req.onboarding_completed is not None:
            settings.onboarding_completed = req.onboarding_completed
        save_user_config(settings)
        crew.refresh_provider()
        return _settings_payload()

    def _settings_payload() -> dict[str, Any]:
        cfg = get_user_config().all()
        pinfo = provider_status(settings)
        return {
            "provider": settings.provider,
            "provider_info": pinfo,
            "ollama_base_url": settings.ollama_base_url,
            "ollama_model": settings.ollama_model,
            "openai_base_url": settings.openai_base_url,
            "openai_model": settings.openai_model,
            "openai_api_key_set": bool(settings.openai_api_key),
            "allow_shell_commands": settings.allow_shell_commands,
            "onboarding_completed": settings.onboarding_completed,
            "ollama_models": ollama_installed_models(settings) if ollama_available(settings) else [],
            "version": APP_VERSION,
        }

    app = FastAPI(title="Persona", description="AI agent workspace", version=APP_VERSION)
    app.add_middleware(NoCacheStaticMiddleware)
    register_brain_routes(app)

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
            else settings.ollama_model,
            "workspace": str(settings.workspace),
            "board_columns": BOARD_COLUMNS,
            "team_workspace": ws.to_dict() if ws else None,
            "document_count": len(crew.list_documents()),
            "standalone": True,
            "version": APP_VERSION,
            "onboarding_completed": settings.onboarding_completed,
            "allow_shell_commands": settings.allow_shell_commands,
        }

    @app.get("/api/settings")
    def get_app_settings():
        return _settings_payload()

    @app.post("/api/settings")
    def update_settings(req: SettingsRequest):
        return _apply_settings(req)

    @app.post("/api/settings/provider")
    def set_provider(req: ProviderRequest):
        return _apply_settings(SettingsRequest(provider=req.provider))

    @app.post("/api/settings/test")
    def test_provider(req: SettingsRequest = SettingsRequest()):
        probe = Settings(**settings.model_dump())
        probe.provider = req.provider
        if req.ollama_base_url:
            probe.ollama_base_url = req.ollama_base_url
        if req.ollama_model:
            probe.ollama_model = req.ollama_model
        if req.openai_base_url:
            probe.openai_base_url = req.openai_base_url
        if req.openai_model:
            probe.openai_model = req.openai_model
        if req.openai_api_key and req.openai_api_key.strip():
            probe.openai_api_key = req.openai_api_key.strip()

        mode = req.provider
        if mode == "ollama" or (mode == "auto" and ollama_ready(probe)):
            if not ollama_available(probe):
                return {"ok": False, "message": "Ollama is not running at " + probe.ollama_base_url}
            if not ollama_ready(probe):
                return {
                    "ok": False,
                    "message": f"Model {probe.ollama_model} is not installed. Run: ollama pull {probe.ollama_model.split(':')[0]}",
                }
            return {"ok": True, "message": "Ollama is ready.", "provider": "ollama"}

        api_key = probe.openai_api_key
        if mode == "openai" or (mode == "auto" and api_key):
            if not api_key:
                return {"ok": False, "message": "API key is required for cloud AI."}
            try:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                base = probe.openai_base_url.rstrip("/")
                model = probe.openai_model
                r = httpx.post(
                    f"{base}/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
                    timeout=15.0,
                )
                if r.status_code == 401:
                    return {"ok": False, "message": "Invalid API key."}
                if r.status_code >= 400:
                    return {"ok": False, "message": f"API error: {r.status_code}"}
                return {"ok": True, "message": "Cloud API connected.", "provider": "openai"}
            except Exception as exc:
                return {"ok": False, "message": str(exc)}

        return {"ok": True, "message": "Demo mode works without a provider.", "provider": "demo"}

    @app.get("/api/updates")
    def check_updates():
        try:
            r = httpx.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
                timeout=8.0,
            )
            if r.status_code != 200:
                return {"available": False, "current": APP_VERSION}
            data = r.json()
            latest = (data.get("tag_name") or "").lstrip("v")
            current = APP_VERSION
            return {
                "available": latest and latest != current,
                "current": current,
                "latest": latest,
                "url": data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"),
                "download_url": f"https://github.com/{GITHUB_REPO}/releases/latest/download/{RELEASE_ASSET}",
                "name": data.get("name", ""),
            }
        except Exception:
            return {"available": False, "current": APP_VERSION}

    @app.get("/api/memory")
    def list_memory():
        return {"entries": memory.entries()}

    @app.post("/api/memory")
    def add_memory(req: MemoryRequest):
        memory.add(req.key, req.value)
        return {"entries": memory.entries()}

    @app.delete("/api/memory/{key}")
    def delete_memory(key: str):
        memory.remove(key)
        return {"entries": memory.entries()}

    @app.get("/api/chat/history")
    def get_chat_history(workspace_id: str = "default", mode: str = "solo", persona_id: str | None = None):
        return {"messages": history.get(workspace_id, mode, persona_id)}

    @app.post("/api/chat/history")
    def save_chat_history(req: ChatHistoryRequest):
        if req.messages is not None:
            history.save(req.workspace_id, req.mode, req.messages, req.persona_id)
        return {"messages": history.get(req.workspace_id, req.mode, req.persona_id)}

    @app.delete("/api/chat/history")
    def clear_chat_history(workspace_id: str = "default", mode: str = "solo", persona_id: str | None = None):
        history.clear(workspace_id, mode, persona_id)
        return {"cleared": True}

    @app.get("/api/logs")
    def get_logs():
        log_dir = settings.data_dir
        result: dict[str, str] = {}
        for name in ("error.log", "startup.log"):
            path = log_dir / name
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                result[name] = text[-8000:] if len(text) > 8000 else text
        return {"logs": result, "log_dir": str(log_dir)}

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        _apply_workspace(req.workspace_id)
        try:
            get_persona(req.persona_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        user_message = req.message.strip()
        llm_message = augment_message_with_rag(user_message)

        if req.stream:
            def generate():
                assistant_parts: list[str] = []
                try:
                    for event in crew.iter_solo(req.persona_id, llm_message):
                        event_type = event.get("type", "message")
                        if event_type == "token":
                            assistant_parts.append(str(event.get("text", "")))
                        yield _sse_event(event_type, event)
                    assistant_text = "".join(assistant_parts)
                    if assistant_text.strip():
                        capture_turn(
                            persona_id=req.persona_id,
                            user_message=user_message,
                            assistant_message=assistant_text,
                            workspace_id=req.workspace_id,
                            mode="solo",
                        )
                except Exception as exc:
                    yield _sse_event("error", {"message": str(exc)})

            return StreamingResponse(generate(), media_type="text/event-stream")

        result = crew.solo(req.persona_id, llm_message)
        data = result.to_dict()
        for msg in data.get("messages", []):
            content = str(msg.get("content", ""))
            if content.strip():
                capture_turn(
                    persona_id=str(msg.get("persona_id", req.persona_id)),
                    user_message=user_message,
                    assistant_message=content,
                    workspace_id=req.workspace_id,
                    mode="solo",
                )
        return data

    @app.post("/api/group")
    def group_chat(req: GroupChatRequest):
        _apply_workspace(req.workspace_id)
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        user_message = req.message.strip()
        llm_message = augment_message_with_rag(user_message)

        if req.stream:
            def generate():
                assistant_parts: list[str] = []
                current_persona = "captain"
                try:
                    iterator = (
                        crew.iter_project(llm_message, req.project_id)
                        if req.mode == "project"
                        else crew.iter_roundtable(llm_message, req.persona_ids)
                    )
                    for event in iterator:
                        event_type = event.get("type", "message")
                        if event_type == "persona_start":
                            if assistant_parts:
                                capture_turn(
                                    persona_id=current_persona,
                                    user_message=user_message,
                                    assistant_message="".join(assistant_parts),
                                    workspace_id=req.workspace_id,
                                    mode=req.mode,
                                )
                            assistant_parts = []
                            current_persona = str(event.get("persona_id", "captain"))
                        if event_type == "token":
                            assistant_parts.append(str(event.get("text", "")))
                        yield _sse_event(event_type, event)
                    if assistant_parts:
                        capture_turn(
                            persona_id=current_persona,
                            user_message=user_message,
                            assistant_message="".join(assistant_parts),
                            workspace_id=req.workspace_id,
                            mode=req.mode,
                        )
                except Exception as exc:
                    yield _sse_event("error", {"message": str(exc)})

            return StreamingResponse(generate(), media_type="text/event-stream")

        if req.mode == "project":
            result = crew.project(llm_message, req.project_id)
        else:
            result = crew.roundtable(llm_message, req.persona_ids)
        data = result.to_dict()
        for msg in data.get("messages", []):
            content = str(msg.get("content", ""))
            if content.strip():
                capture_turn(
                    persona_id=str(msg.get("persona_id", "captain")),
                    user_message=user_message,
                    assistant_message=content,
                    workspace_id=req.workspace_id,
                    mode=req.mode,
                )
        return data

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
        return HTMLResponse(
            _index_html(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
