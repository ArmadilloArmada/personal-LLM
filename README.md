# Persona

**Persona** is a standalone Windows AI agent app — download, unzip, double-click. **Built-in AI included** — no Ollama, no Python, no API keys required.

## Download (Windows)

**https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-Windows-portable.zip**

1. Download and **unzip the whole folder**
2. Double-click **`Persona.exe`**
3. The app opens with **built-in offline AI** (first launch may take ~30s while the model loads)

Optional: run **`Create Desktop Shortcut.bat`** to add Persona to your desktop.

See [DOWNLOAD.md](DOWNLOAD.md) if it won't open.

## What you get

- **Built-in AI** — llama.cpp + local models shipped in the app (~1 GB download)
- **Model manager** — Fast / Balanced / Quality tiers in Settings
- **Modern dark UI** with light mode toggle
- **5 built-in agents** — Byte, Sunny, Nova, Sketch, Captain
- **Solo, Group, Project, Board** modes
- **Team workspaces**, **knowledge base**, **custom agents**

## AI options (Settings)

| Mode | Description |
|------|-------------|
| **Built-in AI** (default) | Offline, included in the zip — no install |
| **Quality model** | Download Llama 3.2 3B from Settings (~2 GB, best answers) |
| **Ollama** | Optional advanced local setup |
| **Cloud API** | OpenAI-compatible API key |

## Upgrade options (optional)

- **Settings → Built-in model → Quality** — download the larger 3B model
- Install [Ollama](https://ollama.com) for power-user local models with tool support
- Add a cloud API key in Settings

## Data

Everything stays local in `%USERPROFILE%\.persona\`

## License

MIT
