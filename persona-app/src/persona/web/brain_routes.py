"""Big Brain routes — API proxy, static SPA, capture helpers."""

from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from persona.big_brain.client import (
    capture_chat,
    flush_session_capture,
    get_brain_config,
    get_last_brain_error,
    inject_rag_context,
    is_brain_available,
)
from persona.big_brain.paths import brain_api_url, brain_client_dist
from persona.personas import get_persona

_log = logging.getLogger(__name__)


class BrainCaptureRequest(BaseModel):
    persona_id: str
    user_message: str
    assistant_message: str
    workspace_id: str = "default"
    mode: str = "solo"
    starred: bool = False
    force: bool = True


class BrainInjectRequest(BaseModel):
    message: str


def register_brain_routes(app: FastAPI) -> None:
    """Mount Big Brain proxy, static UI, and helper APIs on the Persona app."""

    @app.get("/api/brain/status")
    def brain_status():
        available = is_brain_available()
        config = get_brain_config() if available else {}
        return {
            "available": available,
            "url": brain_api_url(),
            "config": config,
            "client_dist": str(brain_client_dist() or ""),
        }

    @app.post("/api/brain/start")
    def brain_start():
        from persona.big_brain.process import ensure_brain_server

        ok = ensure_brain_server()
        return {"ok": ok, "available": is_brain_available()}

    @app.get("/api/brain/last-error")
    def brain_last_error():
        return get_last_brain_error()

    @app.post("/api/brain/inject")
    def brain_inject(req: BrainInjectRequest):
        return {"message": inject_rag_context(req.message)}

    @app.post("/api/brain/session-end")
    def brain_session_end():
        return flush_session_capture()

    @app.post("/api/brain/capture")
    def brain_capture_manual(req: BrainCaptureRequest):
        try:
            persona = get_persona(req.persona_id)
            name = getattr(persona, "name", req.persona_id)
        except KeyError:
            name = req.persona_id
        capture_chat(
            persona_id=req.persona_id,
            persona_name=name,
            user_message=req.user_message,
            assistant_message=req.assistant_message,
            workspace_id=req.workspace_id,
            mode=req.mode,
            starred=req.starred,
            force=req.force,
            sync=True,
        )
        from persona.big_brain.client import get_last_brain_error

        err = get_last_brain_error().get("capture")
        if err:
            raise HTTPException(status_code=502, detail=err)
        return {"ok": True}

    @app.api_route("/brain/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def brain_api_proxy(path: str, request: Request):
        url = f"{brain_api_url()}/api/{path}"
        body = await request.body()
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                upstream = await client.request(
                    request.method,
                    url,
                    content=body,
                    headers=headers,
                    params=dict(request.query_params),
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Big Brain unavailable: {exc}") from exc

        skip = {"content-encoding", "transfer-encoding", "connection", "content-length"}
        out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in skip}
        return Response(content=upstream.content, status_code=upstream.status_code, headers=out_headers)

    dist = brain_client_dist()
    if not dist:
        _log.warning("Big Brain client dist not found — /brain UI disabled")
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/brain/assets", StaticFiles(directory=assets), name="brain_assets")

    @app.get("/brain")
    @app.get("/brain/{rest:path}")
    async def brain_spa(rest: str = ""):
        if rest and rest != "index.html":
            candidate = dist / rest
            if candidate.is_file():
                return FileResponse(candidate)
        index = dist / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404, detail="Big Brain UI not built")
        return FileResponse(
            index,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )


def augment_message_with_rag(message: str) -> str:
    if not is_brain_available():
        return message
    cfg = get_brain_config()
    if not cfg.get("ragEnabled", True):
        return message
    return inject_rag_context(message)


def capture_turn(
    *,
    persona_id: str,
    user_message: str,
    assistant_message: str,
    workspace_id: str | None,
    mode: str,
    starred: bool = False,
    force: bool = False,
) -> None:
    if not is_brain_available():
        return
    try:
        persona = get_persona(persona_id)
        name = persona.get("name") if isinstance(persona, dict) else getattr(persona, "name", persona_id)
    except KeyError:
        name = persona_id
    capture_chat(
        persona_id=persona_id,
        persona_name=name,
        user_message=user_message,
        assistant_message=assistant_message,
        workspace_id=workspace_id or "default",
        mode=mode,
        starred=starred,
        force=force,
    )
