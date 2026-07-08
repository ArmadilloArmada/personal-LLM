# Persona

**Persona** is a standalone Windows AI agent app — download, unzip, double-click. **Built-in AI included** — no Ollama, no Python, no API keys required.

## Download

### Windows (recommended — built-in offline AI)

**https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-Windows-portable.zip**

1. Download and **unzip the whole folder**
2. Double-click **`Persona.exe`**
3. Pick a project template — Captain and the crew plan it with you

### macOS

**https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-macOS-portable.zip**

1. Unzip and double-click **`Persona.command`**
2. First launch installs dependencies (needs internet once)
3. Connect Ollama or a cloud API in Settings, or use demo mode

See [DOWNLOAD.md](DOWNLOAD.md) if it won't open.

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

- **Built-in AI** — llama.cpp + local models shipped in the app (~1 GB download)
- **Project templates** — side projects, debugging, study plans, blog posts, and more
- **Model manager** — Fast / Balanced / Quality tiers in Settings
- **Modern dark UI** with light mode toggle, chat history, and onboarding
- **5 built-in agents** — Byte, Sunny, Nova, Sketch, Captain
- **Shareable agent packs** — export/import YAML teams; 3 built-in packs (Startup, Writer's room, Study squad)
- **Solo, Group, Project, Board** modes
- **Team workspaces**, **knowledge base**, **custom agents**

## AI options (Settings)

| Mode | Description |
|------|-------------|
| **Built-in AI** (default) | Offline, included in the zip — no install |
| **Quality model** | Download Llama 3.2 3B from Settings (~2 GB, best answers) |
| **Ollama** | Optional advanced local setup |
| **Cloud API** | OpenAI-compatible API key |
| **Demo** | Instant scripted replies for exploring the UI |

## Upgrade options (optional)

- **Settings → Built-in model → Quality** — download the larger 3B model
- Install [Ollama](https://ollama.com) for power-user local models with tool support
- Add a cloud API key in Settings

## Data

Everything stays local in `%USERPROFILE%\.persona\`

## License

MIT
