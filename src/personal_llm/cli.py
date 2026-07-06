"""Command-line interface."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from personal_llm.agent import Agent
from personal_llm.config import Settings, get_settings
from personal_llm.llm import get_provider
from personal_llm.memory import MemoryStore

app = typer.Typer(
    name="personal-llm",
    help="Personal LLM agent — local-first with tools and memory",
    no_args_is_help=True,
)
console = Console()


def _settings_with_overrides(
    provider: str | None = None,
    model: str | None = None,
    workspace: Path | None = None,
) -> Settings:
    settings = get_settings()
    if provider:
        settings.provider = provider
    if model:
        if settings.provider == "openai":
            settings.openai_model = model
        else:
            settings.ollama_model = model
    if workspace:
        settings.workspace = workspace.resolve()
    return settings


@app.command()
def chat(
    message: str | None = typer.Argument(None, help="Single message (omit for interactive mode)"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="ollama or openai"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Working directory"),
    session: str | None = typer.Option(None, "--session", "-s", help="Session name to resume"),
) -> None:
    """Chat with your personal agent (with tools)."""
    settings = _settings_with_overrides(provider, model, workspace)
    agent = _make_agent(settings)

    if session:
        session_path = settings.sessions_dir / f"{session}.json"
        if session_path.exists():
            agent.load_session(session_path)
            console.print(f"[dim]Resumed session: {session}[/dim]")

    if message:
        _print_response(agent.chat(message))
        if session:
            agent.save_session(settings.sessions_dir / f"{session}.json")
        return

    console.print(Panel.fit(
        f"[bold]Personal LLM Agent[/bold]\n"
        f"Provider: {settings.provider} | Model: "
        f"{settings.openai_model if settings.provider == 'openai' else settings.ollama_model}\n"
        f"Workspace: {settings.workspace}\n"
        f"[dim]Type 'exit' or Ctrl+C to quit. 'reset' clears conversation.[/dim]",
        border_style="blue",
    ))

    session_path = None
    if session:
        session_path = settings.sessions_dir / f"{session}.json"
    else:
        default_name = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        session_path = settings.sessions_dir / f"{default_name}.json"

    try:
        while True:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            if user_input.strip().lower() in ("exit", "quit", "q"):
                break
            if user_input.strip().lower() == "reset":
                agent.reset()
                console.print("[dim]Conversation reset.[/dim]")
                continue
            if not user_input.strip():
                continue

            with console.status("[bold green]Thinking...[/bold green]"):
                response = agent.chat(user_input)
            _print_response(response)
            agent.save_session(session_path)
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/dim]")
        if session_path:
            agent.save_session(session_path)


@app.command()
def ask(
    message: str = typer.Argument(..., help="Your question"),
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    """Simple one-shot chat without tools (faster for quick questions)."""
    settings = _settings_with_overrides(provider, model)
    provider_instance = get_provider(settings)
    from personal_llm.models import Message

    response = provider_instance.chat([Message(role="user", content=message)])
    _print_response(response.message.content or "")


@app.command("memory")
def memory_cmd(
    action: str = typer.Argument("list", help="list | add | remove"),
    key: str | None = typer.Argument(None, help="Memory key"),
    value: str | None = typer.Argument(None, help="Memory value (for add)"),
) -> None:
    """View or manage persistent memories."""
    settings = get_settings()
    store = MemoryStore(settings.memory_file)

    if action == "list":
        console.print(store.list_all())
    elif action == "add":
        if not key or not value:
            console.print("[red]Usage: personal-llm memory add <key> <value>[/red]")
            raise typer.Exit(1)
        console.print(store.add(key, value))
    elif action == "remove":
        if not key:
            console.print("[red]Usage: personal-llm memory remove <key>[/red]")
            raise typer.Exit(1)
        console.print(store.remove(key))
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show configuration and check provider connectivity."""
    settings = get_settings()
    console.print(Panel.fit(
        f"[bold]Configuration[/bold]\n"
        f"Provider: {settings.provider}\n"
        f"Ollama: {settings.ollama_base_url} / {settings.ollama_model}\n"
        f"OpenAI: {settings.openai_base_url} / {settings.openai_model}\n"
        f"Workspace: {settings.workspace}\n"
        f"Data dir: {settings.data_dir}\n"
        f"Max tool rounds: {settings.max_tool_rounds}",
        title="personal-llm status",
        border_style="green",
    ))

    import httpx

    if settings.provider == "ollama":
        try:
            r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            console.print(f"[green]Ollama connected.[/green] Models: {', '.join(models) or '(none)'}")
        except Exception as exc:
            console.print(f"[red]Ollama not reachable:[/red] {exc}")
            console.print("[dim]Install from https://ollama.com and run: ollama pull llama3.2[/dim]")
    else:
        if not settings.openai_api_key:
            console.print("[yellow]Warning: PERSONAL_LLM_OPENAI_API_KEY is not set.[/yellow]")
        else:
            console.print("[green]OpenAI API key configured.[/green]")

    store = MemoryStore(settings.memory_file)
    mem = store.list_all()
    console.print(f"\n[bold]Memories[/bold]\n{mem}")


@app.command()
def sessions() -> None:
    """List saved conversation sessions."""
    settings = get_settings()
    paths = sorted(settings.sessions_dir.glob("*.json"), reverse=True)
    if not paths:
        console.print("No saved sessions.")
        return
    for p in paths[:20]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            count = len(data.get("messages", []))
            console.print(f"  {p.stem}  ({count} messages)")
        except Exception:
            console.print(f"  {p.stem}  (corrupt)")


def _make_agent(settings: Settings) -> Agent:
    def on_tool_call(name: str, args: dict) -> None:
        console.print(f"[dim]→ {name}({json.dumps(args, ensure_ascii=False)[:120]})[/dim]")

    def on_tool_result(name: str, result: str) -> None:
        preview = result[:200] + ("..." if len(result) > 200 else "")
        console.print(f"[dim]← {name}: {preview}[/dim]")

    return Agent(settings, on_tool_call=on_tool_call, on_tool_result=on_tool_result)


def _print_response(text: str) -> None:
    console.print()
    console.print(Panel(Markdown(text), title="[bold green]Agent[/bold green]", border_style="green"))


if __name__ == "__main__":
    app()
