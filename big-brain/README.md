# Big Brain

Obsidian-like knowledge graph for **Persona** — captures every chat into a linked vault, graph, and workflow engine.

Part of the [Persona](../README.md) project. Works standalone or integrated with Persona.

## Features

- Markdown vault with `[[wiki-links]]`, tags, backlinks, search
- **Graph view** of all notes including Persona chats and agent profiles
- **Persona chat capture** — conversations auto-saved to `Persona/Chats/` and `Personas/`
- Visual workflow editor with Persona LLM nodes
- Standalone: runs without Persona (workflows need Persona API for LLM steps)

## Quick start

```bash
cd Persona/big-brain
npm install
npm run dev:all
```

- **UI:** http://localhost:5174  
- **API:** http://localhost:3002  

## Persona integration

Chat capture runs server-side in Persona when Big Brain is running. See [docs/DUAL_RAG.md](../docs/DUAL_RAG.md) for architecture details.

## Workflow node types

| Node | Purpose |
|------|---------|
| Note Trigger | Start from a vault note |
| Persona LLM | Call Persona `/api/chat` |
| Transform | Sandboxed JavaScript |
| Vault Write | Append or create notes |
| Output | Return result to UI |

## License

MIT
