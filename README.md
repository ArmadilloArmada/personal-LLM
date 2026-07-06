# Persona + Big Brain

Unified standalone app: **Persona** chat + **Big Brain** knowledge graph in one window.

## End users (Windows)

Download: **https://github.com/ArmadilloArmada/CursorProjects/releases/latest/download/Persona-Windows-portable.zip**

Unzip → run **Persona.exe** → use **Chat | Big Brain** tabs.

See [persona-app/DOWNLOAD.md](persona-app/DOWNLOAD.md) and [persona-app/windows/README.txt](persona-app/windows/README.txt).

## Developers

```powershell
cd Persona
npm install
pip install -e persona-app[desktop,dev]
npm run dev
```

| URL | App |
|-----|-----|
| http://127.0.0.1:8765 | Persona (Chat + Big Brain tab) |
| http://127.0.0.1:8765/brain/embed | Big Brain graph (embedded) |
| http://127.0.0.1:3002 | Big Brain API (child process) |

Data: `%USERPROFILE%\.persona\` (vault, DB, config, logs).

`npm start` is for local dev only. Shipped builds come from GitHub Actions as **Persona-Windows-portable.zip**.

## Structure

```
Persona/
├── persona-app/     # Persona Python + web UI
├── big-brain/       # Node vault + workflows + React UI
├── packages/shared/ # Shared types (reference)
├── scripts/         # Dev launchers
└── docs/            # DUAL_RAG.md, etc.
```

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Brain API + Persona server |
| `npm run build` | Production build of Big Brain |
| `npm test` | Run Persona Python tests (via pytest) |

## Chat commands

`/brain save`, `/brain on`, `/brain off`, `/brain graph`, `/brain search <q>`, `/brain mode <mode>`

## Releases

Tag `v*` triggers Windows portable build + GitHub Release. See `.github/workflows/build-unified-windows.yml`.
