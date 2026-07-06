# Persona v0.3

**Persona** is a cartoon AI crew for individuals and companies — specialized agents that work solo, as a group, or take over projects together.

## What's new in v0.3

- **Custom personas** — YAML/JSON definitions for company-specific agents
- **Streaming responses** — real-time token streaming in the web UI (SSE)
- **Project board** — drag-and-drop kanban (Backlog → In Progress → Review → Done)
- **Voice** — mic input (Web Speech API) + optional spoken replies

## Meet the crew

| Persona | Role | Specialty |
|---------|------|-----------|
| 💻 **Byte** | Programmer | Code, debug, ship |
| ☀️ **Sunny** | Conversationalist | Chat, motivate |
| 🔭 **Nova** | Researcher | Research, analysis |
| 🎨 **Sketch** | Creative | Writing, branding |
| 🧭 **Captain** | Project Lead | Plans, delegates |

Add your own — e.g. **Ledger** the Accountant for Acme Corp (see `personas/example-ledger.yaml`).

## Quick start

```bash
pip install -e .
ollama pull llama3.2
persona serve
# → http://127.0.0.1:8765
```

## Modes

| Mode | What it does |
|------|----------------|
| **Solo** | One-on-one with any persona |
| **Group** | Roundtable — relevant personas respond |
| **Project** | Captain plans, crew executes, tasks hit the board |
| **Board** | Drag tasks between kanban columns |

## Custom personas

Drop YAML files in `~/.persona/personas/` or `./personas/`:

```yaml
id: ledger
name: Ledger
role: Accountant
company: Acme Corp
emoji: "📊"
color: "#10B981"
shape: diamond
specialties: [finance, budget]
instructions: You are Ledger, our friendly finance expert...
```

```bash
persona personas list
persona personas add personas/example-ledger.yaml
persona personas remove ledger
```

Or use the **➕ Persona** button in the web app.

## Voice

- **🎤 Mic** — speak your message (Chrome/Edge/Safari)
- **🔊 Toggle** — personas read replies aloud

## CLI

```bash
persona serve                    # Interactive web app
persona chat -P byte             # Terminal chat
persona group "Plan a SaaS app" --mode project
persona personas list
persona crew
persona status
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONA_PROVIDER` | `ollama` | `ollama` or `openai` |
| `PERSONA_WEB_PORT` | `8765` | Web app port |
| `PERSONA_WORKSPACE` | `.` | Agent workspace |

## Project layout

```
persona/
├── src/persona/
│   ├── personas.py      # Built-in crew
│   ├── custom.py        # Custom persona loader
│   ├── crew.py          # Orchestration + board
│   ├── projects.py      # Kanban task logic
│   └── web/static/      # Cartoon UI
├── personas/            # Workspace custom personas
└── tests/
```

## Development

```bash
pip install -e ".[dev]"
pytest
persona serve
```

## License

MIT
