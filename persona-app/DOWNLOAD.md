# Download Persona + Big Brain (Windows)

## Latest release (recommended)

**Installer:** https://github.com/ArmadilloArmada/Persona/releases/latest/download/Persona-Setup.exe

**Portable zip:** https://github.com/ArmadilloArmada/Persona/releases/latest/download/Persona-Windows-portable.zip

Release page: https://github.com/ArmadilloArmada/Persona/releases/latest

> **Note:** v1.1.2 and earlier only include demo-mode AI (no real LLM). Use **v1.2.0+** for built-in offline AI with llama.cpp.

## What's included (v1.2.0+)

| Feature | Details |
|---------|---------|
| **Built-in AI** | llama.cpp + Fast & Balanced models shipped offline (~1 GB). No Ollama required. |
| **Voices** | Speaker icon toggles spoken replies; mic button for voice input (Edge/Chrome speech APIs). |
| **Big Brain** | Vault, graph, workflows, and automatic chat capture — bundled Node runtime included. |
| **5 agents** | Byte, Sunny, Nova, Sketch, Captain + importable agent packs |
| **Optional upgrades** | Ollama or cloud API in Settings; Quality model (~2 GB) for tool use |

### Model tiers (built-in AI)

| Tier | Model | Size | Tools |
|------|-------|------|-------|
| Fast | Qwen2.5-0.5B | ~350 MB | Chat only |
| Balanced | Llama 3.2 1B | ~700 MB | Chat only (default) |
| Quality | Qwen2.5 3B | ~2 GB download | Chat + file/memory tools |

## Quick start

1. Download **Persona-Setup.exe** (or the portable zip for advanced users)
2. Run the installer — or unzip the portable folder and run **Persona.exe**
3. Wait ~30 seconds on first launch while built-in AI loads
4. Persona opens in an app window; use the system tray icon to quit
5. Click **Chat** or **Big Brain** in the header
6. Toggle the **speaker icon** for voice replies; use the **mic** for voice input

## Requirements

- Windows 10 or 11 (64-bit)
- Microsoft Edge or Google Chrome (for the app window and voice features)
- 8 GB+ RAM recommended (16 GB for Quality model)
- No Python or Node install required (bundled)
- Optional: [Ollama](https://ollama.com) for larger local models

## Troubleshooting

See [windows/README.txt](windows/README.txt) in the install folder, or logs in `%USERPROFILE%\.persona\`.

## Developers

See the [monorepo README](../README.md) for `npm run dev` setup.
