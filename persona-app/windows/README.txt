Persona + Big Brain for Windows
================================

Persona is your local AI agent workspace. Big Brain is your knowledge vault and graph — built in.

## Install (end users)

1. Download **Persona-Windows-portable.zip** from:
   https://github.com/ArmadilloArmada/CursorProjects/releases/latest/download/Persona-Windows-portable.zip
2. Unzip the **entire folder** (keep all files together).
3. Double-click **Persona.exe** (or use **Run Persona.bat**).
4. Use the **Chat** and **Big Brain** tabs in the header.

Optional: run **Create Desktop Shortcut.bat** to pin Persona to your desktop.

## What you get

- **Chat** — Solo, Group, Project, and Board modes with built-in agents
- **Big Brain** — Vault, graph, workflows, and automatic chat capture
- **Demo mode** — works instantly with no API keys
- **Ollama** — auto-detected for local models (install from https://ollama.com)

## Your data (private, local)

Everything stays on your PC:

```
%USERPROFILE%\.persona\
├── config.json       # LLM settings
├── vault\            # Big Brain markdown notes
├── big-brain.db      # Brain settings, graph, workflows
├── chat_history.json
├── error.log         # Persona errors
└── brain.log         # Big Brain process log
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App won't start | Check `%USERPROFILE%\.persona\error.log` and `startup.log` |
| Big Brain offline | Check `%USERPROFILE%\.persona\brain.log` |
| Old UI after update | Close Persona fully and reopen (no browser cache needed in app window) |
| Port in use | Close other Persona instances; default port is 8765 |

## Developers

From the Persona monorepo root:

```powershell
npm install
pip install -e persona-app[desktop,dev]
npm run dev
```

`npm start` is a dev launcher only. Shipped builds come from CI as **Persona-Windows-portable.zip**.

## Privacy

Persona runs locally. No account required. Cloud API keys (if you add them) are stored in `%USERPROFILE%\.persona\config.json` on your machine only.
