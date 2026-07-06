# Persona v0.4

**Persona** is a cartoon AI crew for individuals and companies — specialized agents that work solo, as a group, or take over projects together.

## What's new in v0.4

- **Team workspaces** — separate boards, docs, and projects per team/company
- **Company docs (RAG)** — upload policies and specs; personas search them via `search_docs`
- **Custom avatars** — upload images for any persona (PNG, JPG, GIF, WebP, SVG)

## Quick start

```bash
pip install -e .
persona serve
# → http://127.0.0.1:8765
```

## Team workspaces

Each workspace has its own:
- Project kanban board
- Document knowledge base
- Shared crew context

```bash
# Web UI: workspace dropdown + 🏢 button
# Or API:
curl -X POST http://localhost:8765/api/workspaces \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Team","company":"Acme Corp"}'
```

## Company docs (RAG)

Upload `.txt`, `.md`, `.csv`, `.json`, `.yaml` files in the web UI **Company Docs** panel, or:

```bash
curl -X POST http://localhost:8765/api/docs \
  -F file=@handbook.md
```

Personas with `search_docs` (Byte, Nova, Captain) automatically retrieve relevant snippets.

## Custom avatars

Upload a cartoon portrait when creating a persona, or:

```bash
curl -X POST http://localhost:8765/api/personas/byte/avatar \
  -F file=@byte-cartoon.png
```

## Modes

| Mode | Description |
|------|-------------|
| Solo | One-on-one with any persona |
| Group | Roundtable with relevant crew |
| Project | Captain leads; tasks on board |
| Board | Drag-and-drop kanban |

## Custom personas

```yaml
# personas/example-ledger.yaml
id: ledger
name: Ledger
role: Accountant
company: Acme Corp
emoji: "📊"
instructions: You are Ledger, our finance expert...
```

```bash
persona personas add personas/example-ledger.yaml
```

## CLI

```bash
persona serve
persona chat -P nova "What does our handbook say about pricing?"
persona group "Launch Q3 campaign" --mode project
persona personas list
persona crew
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONA_PROVIDER` | `ollama` | `ollama` or `openai` |
| `PERSONA_ACTIVE_WORKSPACE` | `default` | Active team workspace |
| `PERSONA_WEB_PORT` | `8765` | Web app port |

## Data layout

```
~/.persona/
├── workspaces/          # Team workspaces
│   └── {id}/docs/       # RAG document index
├── avatars/             # Uploaded persona images
├── personas/            # Custom persona YAML
├── projects/            # Kanban projects (per workspace)
└── memory.json
```

## Development

```bash
pip install -e ".[dev]"
pytest
persona serve
```

## License

MIT
