# Persona

**Persona** is a cartoon AI crew you can chat with solo, as a group, or hand a full project to. Each persona has its own personality, specialty, and tools — built for individuals and teams who want specialized agents that work together.

![Persona crew](https://img.shields.io/badge/crew-5%20personas-ff6b9d)

## Meet the crew

| Persona | Role | Specialty |
|---------|------|-----------|
| 💻 **Byte** | Programmer | Code, debug, ship software |
| ☀️ **Sunny** | Conversationalist | Chat, brainstorm, motivate |
| 🔭 **Nova** | Researcher | Research, analysis, fact-finding |
| 🎨 **Sketch** | Creative | Writing, branding, storytelling |
| 🧭 **Captain** | Project Lead | Plans projects, delegates to the crew |

## Modes

- **Solo** — Talk one-on-one with any persona
- **Group** — Ask the crew; relevant personas chime in (roundtable)
- **Project** — Captain leads: plans, delegates, crew executes, Captain summarizes

## Quick start

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Pull a local model (https://ollama.com)
ollama pull llama3.2

# Launch the interactive app 🎭
persona serve
# → Open http://127.0.0.1:8765
```

## Interactive web app

The web UI features cartoon SVG avatars, a stage where personas animate when talking, speech bubbles, and mode switching (Solo / Group / Project).

```bash
persona serve --port 8765
```

## CLI

```bash
persona crew                              # List the crew
persona chat --persona byte                 # Chat with Byte
persona chat -P sunny "I need motivation" # One-shot with Sunny
persona group "Compare React vs Vue"      # Roundtable
persona group "Build a todo app" --mode project  # Project mode
persona status                            # Config + connectivity
```

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONA_PROVIDER` | `ollama` | `ollama` or `openai` |
| `PERSONA_OLLAMA_MODEL` | `llama3.2` | Local model |
| `PERSONA_OPENAI_API_KEY` | — | API key for cloud |
| `PERSONA_WEB_PORT` | `8765` | Web app port |
| `PERSONA_WORKSPACE` | `.` | Agent workspace |

## Project layout

```
persona/
├── src/persona/
│   ├── personas.py    # Crew definitions
│   ├── crew.py        # Group & project orchestration
│   ├── agent.py       # Per-persona agent loop
│   ├── cli.py         # Terminal commands
│   └── web/
│       ├── server.py  # FastAPI backend
│       └── static/    # Cartoon interactive UI
└── tests/
```

## Data

- Memories: `~/.persona/memory.json`
- Sessions: `~/.persona/sessions/`
- Projects: `~/.persona/projects/`

## Development

```bash
pip install -e ".[dev]"
pytest
persona serve
```

## License

MIT
