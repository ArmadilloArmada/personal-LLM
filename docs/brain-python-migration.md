# Big Brain API: Node child → Python evaluation

## Current architecture

- **Persona** (Python/FastAPI) proxies `/brain/api/*` to a **Node** child on port 3002
- Node uses `better-sqlite3` for graph, workflows, settings
- Portable zip bundles `brain/server/dist`, `node_modules`, and `node/node.exe` (~67 MB total)

## Pain points

- Dual runtime startup (Python + Node)
- Large portable folder (`_internal`, `brain`, `node`)
- CI must run `npm install` inside the portable bundle
- Child process lifecycle and logging complexity

## Migration options

### A. Python FastAPI routes + aiosqlite (recommended long-term)

- Port Brain REST routes from `big-brain/server/src` to `persona/big_brain/api.py`
- Keep vault as markdown files (already shared)
- SQLite schema unchanged; read/write via `aiosqlite` or stdlib `sqlite3`
- **Pros:** Single process, simpler portable build, faster cold start
- **Cons:** ~2–3 week port; workflow runner and MCP need reimplementation or defer

### B. Embed Node as library via python-node (not recommended)

- Still ships Node; little benefit

### C. Keep Node child, slim bundle

- Pre-build `node_modules` in CI artifact; lazy-start Brain on first Big Brain tab
- **Pros:** Low risk
- **Cons:** Does not remove dual-runtime

## Recommendation

**v1.x:** Keep Node child; lazy-start Brain on first tab click to speed Chat-only launches.

**v2.0:** Port read-heavy routes first (graph, vault list, RAG search) to Python; keep Node only for workflows until ported.

## Success metrics

- Portable zip under 45 MB
- Cold start under 5s on mid-range laptop
- No `brain.log` child-process errors in support tickets
