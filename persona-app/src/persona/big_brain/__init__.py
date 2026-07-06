"""Big Brain integration — capture, RAG, and child-process management."""

from persona.big_brain.client import (
    capture_chat,
    get_brain_config,
    inject_rag_context,
    is_brain_available,
)
from persona.big_brain.paths import brain_api_url, brain_client_dist, brain_server_entry
from persona.big_brain.process import ensure_brain_server, stop_brain_server

__all__ = [
    "brain_api_url",
    "brain_client_dist",
    "brain_server_entry",
    "capture_chat",
    "ensure_brain_server",
    "get_brain_config",
    "inject_rag_context",
    "is_brain_available",
    "stop_brain_server",
]
