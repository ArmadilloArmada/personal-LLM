# Persona + Big Brain

Unified standalone app: **Persona** AI agents + **Big Brain** knowledge vault in one window.

[![Windows build](https://github.com/ArmadilloArmada/Persona/actions/workflows/build-windows.yml/badge.svg)](https://github.com/ArmadilloArmada/Persona/actions/workflows/build-windows.yml)

## Download (Windows)

| Install | Link |
|---------|------|
| **Installer (recommended)** | [Persona-Setup.exe](https://github.com/ArmadilloArmada/Persona/releases/latest/download/Persona-Setup.exe) |
| Portable zip | [Persona-Windows-portable.zip](https://github.com/ArmadilloArmada/Persona/releases/latest/download/Persona-Windows-portable.zip) |

[All releases](https://github.com/ArmadilloArmada/Persona/releases/latest)

Run the installer or unzip → **Persona.exe** → use **Chat | Big Brain** tabs. Quit from the system tray icon.

**Built-in AI** ships in the Windows zip (~1.3 GB) — offline chat with llama.cpp, no Ollama install required. Big Brain vault and Node runtime are also bundled.

See [persona-app/DOWNLOAD.md](persona-app/DOWNLOAD.md) and [persona-app/windows/README.txt](persona-app/windows/README.txt).

**[▶ Watch the demo video](persona-app/demo/Persona-demo.mp4)** (~36s) · **[Try interactive demo](persona-app/demo/index.html)** (`?play=1` auto-starts) · Online: `https://armadilloarmada.github.io/Persona/`

## Features

- **Built-in AI (Windows)** — llama.cpp + Fast & Balanced models in the zip; Quality model downloadable in Settings
- **Voices** — spoken agent replies and microphone input (Edge/Chrome)
- **Big Brain** — Obsidian-like vault, graph, workflows, automatic chat capture
- **5 built-in agents** — Byte, Sunny, Nova, Sketch, Captain
- **Agent packs** — curated YAML teams + export/import your own
- **Project templates** — one-click onboarding flows
- **Solo / Group / Project / Board** modes
- **Ollama / Cloud API** — optional upgrades in Settings

### Model tiers (Windows built-in AI)

| Tier | Model | Size | Tools |
|------|-------|------|-------|
| Fast | Qwen2.5-0.5B | ~350 MB | Chat only |
| Balanced | Llama 3.2 1B | ~700 MB | Chat only (default) |
| Quality | Qwen2.5 3B | ~2 GB download | Chat + file/memory tools |

## Developers

```powershell
git clone https://github.com/ArmadilloArmada/Persona.git
cd Persona
npm install
pip install -e persona-app[desktop,dev]
npm run dev
```

| URL | App |
|-----|-----|
| http://127.0.0.1:8765 | Persona (Chat + Big Brain tab) |
| http://127.0.0.1:8765/brain/embed | Big Brain (embedded) |
| http://127.0.0.1:3002 | Big Brain API (child process) |

Data: `%USERPROFILE%\.persona\` (vault, DB, config, logs).

## Structure

```
Persona/
├── persona-app/     # Persona Python + web UI + Windows portable build
├── big-brain/       # Node vault + workflows + React UI
├── packages/shared/ # Shared types
├── scripts/         # Dev launchers
└── docs/            # Architecture notes
```

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Brain API + Persona server |
| `npm run build` | Production build of Big Brain |
| `npm test` | Persona Python tests |

## Chat commands

`/brain save`, `/brain on`, `/brain off`, `/brain graph`, `/brain search <q>`, `/brain mode <mode>`

## Releases

Tag `v*` (e.g. `v1.1.2`) triggers the Windows CI build, installer, and GitHub Release with:

- `Persona-Setup.exe` — recommended installer
- `Persona-Windows-portable.zip` — portable folder

Manual runs of the [Windows build workflow](https://github.com/ArmadilloArmada/Persona/actions/workflows/build-windows.yml) upload CI artifacts only; only tagged pushes publish to [Releases](https://github.com/ArmadilloArmada/Persona/releases/latest).

See [.github/workflows/build-windows.yml](.github/workflows/build-windows.yml).

## License

MIT
