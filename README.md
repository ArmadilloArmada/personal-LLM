# Personal LLM

A **local-first personal AI agent** you run on your own machine. Chat in the terminal, use tools (files, shell, web), and build persistent memory across sessions.

Works with [Ollama](https://ollama.com) for fully local inference, or any OpenAI-compatible API.

## Features

- **Agent mode** — multi-step reasoning with tool use
- **Tools** — read/write files, list directories, run shell commands, fetch URLs, remember facts
- **Memory** — stores preferences and context in `~/.personal-llm/memory.json`
- **Sessions** — conversations auto-save and can be resumed
- **Providers** — Ollama (default) or OpenAI-compatible APIs

## Quick start

### 1. Install

```bash
# Clone and install
cd personal-LLM
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Run a local model (recommended)

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2

# Check everything is wired up
personal-llm status
```

### 3. Chat with your agent

```bash
# Interactive agent (tools enabled)
personal-llm chat

# One-shot task
personal-llm chat "List the files in this project and summarize the README"

# Resume a named session
personal-llm chat --session my-project

# Quick question without tools
personal-llm ask "Explain what a LoRA adapter is in one paragraph"
```

## Configuration

Copy `.env.example` to `.env` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONAL_LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `PERSONAL_LLM_OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `PERSONAL_LLM_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `PERSONAL_LLM_OPENAI_API_KEY` | — | API key for cloud providers |
| `PERSONAL_LLM_OPENAI_MODEL` | `gpt-4o-mini` | Model for OpenAI provider |
| `PERSONAL_LLM_OPENAI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `PERSONAL_LLM_WORKSPACE` | `.` | Directory the agent can access |
| `PERSONAL_LLM_MAX_TOOL_ROUNDS` | `15` | Max tool-call loops per message |

### Using OpenAI / Groq / Together

```bash
export PERSONAL_LLM_PROVIDER=openai
export PERSONAL_LLM_OPENAI_API_KEY=sk-...
export PERSONAL_LLM_OPENAI_MODEL=gpt-4o-mini
personal-llm chat
```

For Groq or other compatible hosts, set `PERSONAL_LLM_OPENAI_BASE_URL` accordingly.

## Commands

```bash
personal-llm chat          # Interactive agent with tools
personal-llm ask <msg>     # Simple one-shot chat
personal-llm memory list   # View stored memories
personal-llm memory add name "Your Name"
personal-llm memory remove name
personal-llm sessions     # List saved conversations
personal-llm status         # Config + connectivity check
```

## Agent tools

| Tool | What it does |
|------|----------------|
| `read_file` | Read a file in the workspace |
| `write_file` | Create or overwrite a file |
| `list_directory` | List files and folders |
| `run_shell` | Execute shell commands in the workspace |
| `web_fetch` | Fetch and read a web page |
| `remember` | Save a fact for future sessions |
| `forget` | Remove a stored memory |

## Project layout

```
personal-LLM/
├── src/personal_llm/
│   ├── agent.py      # Agent loop
│   ├── cli.py        # Terminal interface
│   ├── config.py     # Settings
│   ├── llm.py        # Ollama + OpenAI providers
│   ├── memory.py     # Persistent memory
│   ├── models.py     # Message types
│   └── tools.py      # Agent tools
├── tests/
├── pyproject.toml
└── .env.example
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Data locations

- Memories: `~/.personal-llm/memory.json`
- Sessions: `~/.personal-llm/sessions/`

## License

MIT
