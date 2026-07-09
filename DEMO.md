# Persona — 90-second demo

## Interactive demo (browser)

**Watch:** [demo/Persona-demo.mp4](demo/Persona-demo.mp4) (~36s)  
**Play:** open [`demo/index.html`](demo/index.html) or visit `/demo` while Persona is running (`?play=1` auto-starts).

After GitHub Pages deploy: `https://armadilloarmada.github.io/personal-LLM/`

## Video recording script

Use this script to record a product demo (Loom, OBS, or screen capture) of the **real app**.

## Setup (before recording)

1. Fresh install or clear `%USERPROFILE%\.persona\` / `~/.persona/`
2. Launch Persona (Windows `.exe` or macOS `Persona.command`)
3. Close other windows; use dark theme
4. Optional: pre-upload one doc to Knowledge base (e.g. a short `product-brief.md`)

## Script (~90 seconds)

| Time | Action | Say (optional voiceover) |
|------|--------|--------------------------|
| 0:00 | App opens, splash fades | "This is Persona — your private AI team on your desktop." |
| 0:08 | Welcome screen with templates | "No account, no setup. Pick what you want to work on." |
| 0:12 | Click **Launch a side project** | "I'll ask the crew to plan a side project." |
| 0:15 | Project mode activates; Captain plans | "Captain breaks the goal into tasks and delegates to the team." |
| 0:35 | Scroll crew responses | "Byte, Nova, and Sunny each contribute in character." |
| 0:45 | Switch to **Board** tab | "Tasks land on a kanban board automatically." |
| 0:55 | Drag a task to **In Progress** | "Track progress like any project tool." |
| 1:05 | Open **Agents** sidebar → show packs | "Import agent packs — startup crew, writers, tutors — or export your own." |
| 1:15 | Settings → Built-in AI | "On Windows, built-in offline AI ships in the ~1.3 GB zip. macOS uses Ollama or cloud." |
| 1:25 | End on logo / template screen | "Download free at GitHub — link in description." |

## B-roll shots (optional)

- Solo chat with **Byte** asking to read a file
- **Group** roundtable brainstorming
- Knowledge base search with **Nova**
- Export YAML pack → send to friend → import on second machine

## Release checklist

```bash
git tag v1.0.3
git push origin v1.0.3
```

CI builds and publishes:

- `Persona-Windows-portable.zip` (~1.3 GB — built-in llama.cpp + Fast + Balanced models)
- `Persona-macOS-portable.zip` (~85 KB — launcher only; Ollama / demo / cloud)
