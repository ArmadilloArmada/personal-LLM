Persona + Big Brain for Windows
================================

Persona is your local AI agent workspace. Big Brain is your knowledge vault and graph — built in.

## Install (end users)

1. Download **Persona-Setup.exe** (recommended) or **Persona-Windows-portable.zip** from:
   https://github.com/ArmadilloArmada/CursorProjects/releases/latest
2. Run the installer — or unzip the portable folder (keep all files together).
3. Double-click **Persona.exe** (or use **Run Persona.bat**).
4. Use the tray icon (purple P) to open or quit Persona.
5. Use the **Chat** and **Big Brain** tabs in the header.

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
| App won't start | Check `%USERPROFILE%\.persona\startup.log`. Try **Run Persona.bat** — if the server is up, open http://127.0.0.1:8765 in your browser. |
| No window appears | Persona may still be running in the background. Open http://127.0.0.1:8765 or use **Run Persona.bat**. |
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
