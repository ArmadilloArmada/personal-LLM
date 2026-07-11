Persona + Big Brain for Windows
================================

Persona is your local AI agent workspace. Big Brain is your knowledge vault and graph — built in.

## Install (end users)

1. Download **Persona-Setup.exe** (recommended) or **Persona-Windows-portable.zip** from:
   https://github.com/ArmadilloArmada/Persona/releases/latest
2. Run the installer — or unzip the portable folder (keep all files together).
3. Double-click **Persona.exe** (or use **Run Persona.bat**).
4. Built-in AI loads automatically — first start may take ~30 seconds.
5. Use the tray icon (purple P) to open or quit Persona.
6. Use the **Chat** and **Big Brain** tabs in the header.

Optional: run **Create Desktop Shortcut.bat** to pin Persona to your desktop.

## What's included (~1.3 GB total)

- **Built-in offline AI** — llama-server + Fast (~350 MB) + Balanced (~700 MB) models
- **Quality model** (Qwen2.5 3B, ~2 GB) — download from Settings for file & memory tools
- **Big Brain** — vault, graph, workflows, chat capture
- **5 built-in agents** — Byte, Sunny, Nova, Sketch, Captain
- **Agent packs** — curated teams you can import from the sidebar

## Settings (inside the app)

- **Built-in AI** — default on Windows, works offline
- **Model manager** — Fast / Balanced / Quality tiers
- **CPU threads & GPU layers** — tune performance
- **Ollama / Cloud API** — optional upgrades
- **Big Brain** — vault capture and RAG injection

## Your data (private, local)

Everything stays on your PC:

```
%USERPROFILE%\.persona\
├── config.json       # LLM settings
├── preferences.json  # Built-in AI model tier, threads
├── models\           # Downloaded Quality model
├── vault\            # Big Brain markdown notes
├── big-brain.db      # Brain settings, graph, workflows
├── chat_history.json
├── error.log         # Persona errors
└── brain.log         # Big Brain process log
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App won't start | Check `%USERPROFILE%\.persona\startup.log`. Try **Run Persona.bat**. |
| No window appears | Persona may still be running. Open http://127.0.0.1:8765 or use **Run Persona.bat**. |
| Built-in AI slow | First load takes ~30s. Try Fast tier in Settings if RAM is limited. |
| Big Brain offline | Check `%USERPROFILE%\.persona\brain.log` |
| Old UI after update | Close Persona fully and reopen |
| Port in use | Close other Persona instances; default port is 8765 |

IMPORTANT:
- Do NOT move Persona.exe out of the portable folder.
- The "_internal" folder must stay next to Persona.exe.
- Recommended: 8 GB+ RAM (16 GB ideal for Quality model).

## Developers

From the Persona monorepo root:

```powershell
npm install
pip install -e persona-app[desktop,dev]
npm run dev
```

`npm start` is a dev launcher only. Shipped builds come from CI as **Persona-Setup.exe** (installer) and **Persona-Windows-portable.zip** (portable).

## Privacy

Persona runs locally. No account required. Cloud API keys (if you add them) are stored in `%USERPROFILE%\.persona\config.json` on your machine only.
