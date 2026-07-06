# Persona

**Persona** is a standalone cartoon AI crew app — double-click and chat. No Ollama, no API keys, no config required to get started.

## Windows .exe (no install)

**Download:** https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-Windows-portable.zip

Unzip → double-click `Persona.exe`. See [DOWNLOAD.md](DOWNLOAD.md).

## Install (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/ArmadilloArmada/personal-LLM/main/install.sh | bash
```

Or from this folder:

```bash
chmod +x install.sh && ./install.sh
```

Then just run:

```bash
persona
```

That's it. Your browser opens automatically.

## What you get out of the box

- **Demo mode** — works instantly, no AI install needed
- **5 cartoon personas** — Byte, Sunny, Nova, Sketch, Captain
- **Solo, Group, Project, Board** — full app experience
- **Team workspaces** + **company docs** + **custom personas**

## Upgrade to full AI (optional)

When you want real LLM power:

1. Install [Ollama](https://ollama.com) → `ollama pull llama3.2`
2. Persona **auto-detects** it — or click ⚙️ Settings in the app

Or set a cloud API key:

```bash
export PERSONA_OPENAI_API_KEY=sk-...
```

## Launch options

| Command | What it does |
|---------|----------------|
| `persona` | Open app (default) |
| `persona app` | Same — opens browser |
| `persona app -w` | Native window (`pip install persona[desktop]`) |
| Desktop menu | Search "Persona" after install |

## Features

- Custom personas & avatars for your company
- Upload docs — personas search them (RAG)
- Kanban project board with drag-and-drop
- Voice input & spoken replies
- Streaming responses

## Data

Everything stays local in `~/.persona/`

## Development

```bash
pip install -e ".[dev]"
persona
pytest
```

## License

MIT
