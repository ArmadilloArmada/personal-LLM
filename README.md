# Persona

**Persona** is a standalone AI agent app for teams and individuals — cartoon personas, project templates, kanban boards, and local-first data.

## Download

### Windows (recommended — built-in offline AI, ~1.3 GB)

**https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-Windows-portable.zip**

1. Download and **unzip the whole folder** (expect **~1.3 GB** — includes llama.cpp + local models)
2. Double-click **`Persona.exe`**
3. Pick a project template — Captain and the crew plan it with you

No Python, no Ollama, no API keys required for offline chat.

### macOS (launcher only — ~85 KB, no bundled LLM)

**https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-macOS-portable.zip**

1. Unzip and double-click **`Persona.command`**
2. First launch installs Python dependencies (needs internet once)
3. Use **demo mode**, **Ollama**, or a **cloud API** in Settings

The macOS zip does **not** include offline models. For local AI on Mac, install [Ollama](https://ollama.com). See [DOWNLOAD.md](DOWNLOAD.md) for full platform comparison.

**[▶ Watch the demo video](demo/Persona-demo.mp4)** (~36s) · **[Try interactive demo](demo/index.html)** (`?play=1` auto-starts)

## Agent pack gallery

Import curated teams from the app sidebar, or browse [`personas/gallery/`](personas/gallery/):

| Pack | Agents |
|------|--------|
| 🎲 Dungeon Master's Table | DM, Lorekeeper |
| 💪 Fitness Crew | Coach, Fuel |
| 🛠️ Indie Hacker | Ship, Launch |
| 🏫 Homeschool Helpers | Atlas, Echo |
| 🎬 Content Studio | Reel, Frame |

Plus built-in packs: Startup crew, Writer's room, Study squad.

## What you get

- **Built-in AI (Windows)** — llama.cpp + Fast & Balanced models in the Windows zip (~1.3 GB)
- **Project templates** — side projects, debugging, study plans, blog posts, and more
- **Model manager** — Fast / Balanced / Quality tiers in Settings
- **Modern dark UI** with light mode toggle, chat history, and onboarding
- **5 built-in agents** — Byte, Sunny, Nova, Sketch, Captain
- **Shareable agent packs** — export/import YAML teams
- **Solo, Group, Project, Board** modes
- **Team workspaces**, **knowledge base**, **custom agents**

## AI options (Settings)

| Mode | Windows | macOS |
|------|---------|-------|
| **Built-in AI** (default on Windows) | Offline, included in zip | Not available — use Ollama or cloud |
| **Fast / Balanced** | Bundled in Windows zip | — |
| **Quality model** | Download from Settings (~2 GB, file & memory tools) | — |
| **Ollama** | Optional | Recommended for local AI |
| **Cloud API** | OpenAI-compatible key | Same |
| **Demo** | Scripted UI exploration | Same |

### Model tiers (Windows built-in AI)

| Tier | Size | Tools |
|------|------|-------|
| Fast | ~350 MB (bundled) | Chat only |
| Balanced | ~700 MB (bundled, default) | Chat only |
| Quality | ~2 GB (download in app) | Chat + read/write files, memory |

Quality uses **Qwen2.5-3B-Instruct** (v1.0.3+).

## Upgrade options (optional)

- **Settings → Built-in model → Quality** — download for best answers and file tools (Windows)
- Install [Ollama](https://ollama.com) for power-user local models (especially on macOS)
- Add a cloud API key in Settings

## Data

Everything stays local:

- Windows: `%USERPROFILE%\.persona\`
- macOS/Linux: `~/.persona/`

## License

MIT
