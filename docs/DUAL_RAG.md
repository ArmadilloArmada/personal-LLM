# Dual RAG in Persona + Big Brain

Persona ships two complementary retrieval layers:

| Layer | Implementation | Indexed content |
|-------|----------------|-----------------|
| **Workspace docs** | `persona-app/src/persona/rag.py` (`DocumentStore`) | Files uploaded per workspace under `~/.persona/workspaces/*/docs` |
| **Brain vault** | `big-brain/server/src/services/rag.ts` | Markdown vault at `~/.persona/vault` (chats, notes, personas) |

## v1 unified behavior

1. **Persona chat** (`server.py`): before LLM, calls `augment_message_with_rag()` → Brain `POST /api/brain/rag/inject`.
2. **Persona agents** still use workspace `search_docs` tool for uploaded files.
3. **Big Brain workflows** can use `personaRag` node + Persona LLM node.

## v2 (future)

Merge into one `KnowledgeService` ranking vault + workspace docs + persona memory with shared embeddings (Ollama).
