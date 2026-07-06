"""HTTP client for Big Brain API (capture, RAG, config)."""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
import uuid
from typing import Any

from persona.big_brain.paths import brain_api_url

_log = logging.getLogger(__name__)
_SESSION_ID = str(uuid.uuid4())
_CAPTURE_SECRET = os.environ.get("BIG_BRAIN_CAPTURE_SECRET", "")
_last_brain_error: dict[str, Any] | None = None
_session_buffer: list[dict[str, Any]] = []
_buffer_lock = threading.Lock()


def get_last_brain_error() -> dict[str, Any]:
    return _last_brain_error or {"capture": None, "rag": None}


def _set_error(kind: str, message: str | None) -> None:
    global _last_brain_error
    if _last_brain_error is None:
        _last_brain_error = {"capture": None, "rag": None}
    _last_brain_error[kind] = message


def is_brain_available(timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(f"{brain_api_url()}/api/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_brain_config() -> dict:
    try:
        req = urllib.request.Request(f"{brain_api_url()}/api/brain/config")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {
            "captureEnabled": True,
            "captureMode": "every_turn",
            "ragEnabled": True,
            "ragMaxChunks": 5,
        }


def inject_rag_context(message: str) -> str:
    cfg = get_brain_config()
    if not cfg.get("ragEnabled", True):
        return message
    try:
        payload = json.dumps({"message": message}).encode("utf-8")
        req = urllib.request.Request(
            f"{brain_api_url()}/api/brain/rag/inject",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _set_error("rag", None)
            return str(data.get("injectedMessage") or message)
    except Exception as exc:
        _log.debug("RAG inject failed: %s", exc)
        _set_error("rag", str(exc))
        return message


def _post_json(path: str, payload: dict, *, timeout: float = 30) -> dict:
    headers = {"Content-Type": "application/json"}
    if _CAPTURE_SECRET:
        headers["X-Big-Brain-Secret"] = _CAPTURE_SECRET
    req = urllib.request.Request(
        f"{brain_api_url()}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def capture_chat(
    *,
    persona_id: str,
    persona_name: str | None,
    user_message: str,
    assistant_message: str,
    workspace_id: str = "default",
    mode: str = "solo",
    starred: bool = False,
    force: bool = False,
    sync: bool = False,
) -> None:
    if not assistant_message.strip():
        return

    cfg = get_brain_config()
    if not cfg.get("captureEnabled", True) and not force:
        return

    effective_mode = cfg.get("captureMode", "every_turn")
    if effective_mode == "session_end" and not force:
        with _buffer_lock:
            _session_buffer.append(
                {
                    "personaId": persona_id,
                    "personaName": persona_name or persona_id,
                    "userMessage": user_message,
                    "assistantMessage": assistant_message,
                    "starred": starred,
                }
            )
        return

    def _send() -> None:
        payload = {
            "personaId": persona_id,
            "personaName": persona_name or persona_id,
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "workspaceId": workspace_id,
            "mode": mode,
            "sessionId": _SESSION_ID,
            "starred": starred,
            "force": force,
        }
        try:
            _post_json("/api/persona/capture", payload)
            _set_error("capture", None)
        except Exception as exc:
            _log.warning("Big Brain capture failed: %s", exc)
            _set_error("capture", str(exc))

    if sync:
        _send()
    else:
        threading.Thread(target=_send, daemon=True).start()


def flush_session_capture(
    *,
    persona_id: str | None = None,
    persona_name: str | None = None,
) -> dict[str, Any]:
    """Flush buffered session_end turns to Big Brain."""
    with _buffer_lock:
        if not _session_buffer:
            return {"ok": True, "captured": 0}
        turns = list(_session_buffer)
        pid = persona_id or (turns[-1].get("personaId") if turns else "byte")
        pname = persona_name or (turns[-1].get("personaName") if turns else pid)
        _session_buffer.clear()

    payload = {
        "personaId": pid,
        "personaName": pname,
        "sessionId": _SESSION_ID,
        "turns": [
            {
                "userMessage": t["userMessage"],
                "assistantMessage": t["assistantMessage"],
                "starred": t.get("starred", False),
            }
            for t in turns
        ],
    }
    try:
        result = _post_json("/api/persona/capture/session-end", payload)
        _set_error("capture", None)
        return result
    except Exception as exc:
        _log.warning("Big Brain session-end flush failed: %s", exc)
        _set_error("capture", str(exc))
        with _buffer_lock:
            _session_buffer[:0] = turns
        return {"ok": False, "error": str(exc)}
