"""Command-line interface."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from persona.agent import Agent
from persona.config import Settings, get_settings
from persona.crew import Crew
from persona.llm import get_provider
from persona.memory import MemoryStore
from persona.personas import get_persona, list_personas

app = typer.Typer(
    name="persona",
    help="Persona — cartoon AI crew with specialized agents",
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
def serve(
    host: str | None = typer.Option(None, "--host", "-h"),
    port: int | None = typer.Option(None, "--port", "-p"),
) -> None:
    """Launch the interactive Persona web app."""
    settings = get_settings()
    host = host or settings.web_host
    port = port or settings.web_port
    console.print(Panel.fit(
        f"[bold]Persona Interactive App[/bold]\n"
        f"Open [link=http://{host}:{port}]http://{host}:{port}[/link] in your browser\n"
        f"[dim]Ctrl+C to stop[/dim]",
        border_style="magenta",
    ))
    uvicorn.run("persona.web.server:app", host=host, port=port, reload=False)


@app.command()
def chat(
    message: str | None = typer.Argument(None, help="Single message (omit for interactive mode)"),
    persona: str = typer.Option("byte", "--persona", "-P", help="Persona id: byte, sunny, nova, sketch, captain"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="ollama or openai"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Working directory"),
    session: str | None = typer.Option(None, "--session", "-s", help="Session name to resume"),
) -> None:
    """Chat with a single persona."""
    settings = _settings_with_overrides(provider, model, workspace)
    p = get_persona(persona)
    agent = _make_agent(settings, p)

    if session:
        session_path = settings.sessions_dir / f"{session}.json"
        if session_path.exists():
            agent.load_session(session_path)
            console.print(f"[dim]Resumed session: {session}[/dim]")

    if message:
        _print_response(agent.chat(message), p.name)
        if session:
            agent.save_session(settings.sessions_dir / f"{session}.json")
        return

    console.print(Panel.fit(
        f"[bold]{p.emoji} {p.name}[/bold] — {p.role}\n"
        f"{p.tagline}\n"
        f"Provider: {settings.provider} | Workspace: {settings.workspace}\n"
        f"[dim]Type 'exit' to quit, 'reset' to clear.[/dim]",
        border_style="blue",
    ))

    session_path = settings.sessions_dir / (
        f"{session}.json" if session else f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    )

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
            with console.status(f"[bold]{p.name} thinking...[/bold]"):
                response = agent.chat(user_input)
            _print_response(response, p.name)
            agent.save_session(session_path)
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/dim]")
        agent.save_session(session_path)


@app.command()
def group(
    message: str = typer.Argument(..., help="Message for the crew"),
    mode: str = typer.Option("roundtable", "--mode", "-M", help="roundtable or project"),
    provider: str | None = typer.Option(None, "--provider", "-p"),
) -> None:
    """Ask the whole crew (roundtable) or start a project."""
    settings = _settings_with_overrides(provider)
    crew = Crew(settings)

    if mode == "project":
        result = crew.project(message)
    else:
        result = crew.roundtable(message)

    for msg in result.messages:
        p = get_persona(msg.persona_id)
        title = f"{p.emoji} {p.name}"
        if msg.phase != "response":
            title += f" [{msg.phase}]"
        console.print(Panel(Markdown(msg.content), title=title, border_style="green"))


@app.command()
def crew() -> None:
    """List all personas in your crew."""
    for p in list_personas():
        console.print(
            f"  {p.emoji} [bold]{p.name}[/bold] ({p.id}) — {p.role}\n"
            f"     {p.tagline}\n"
            f"     [dim]Specialties: {', '.join(p.specialties)}[/dim]"
        )


@app.command()
def ask(
    message: str = typer.Argument(..., help="Your question"),
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    """Simple one-shot chat without tools."""
    settings = _settings_with_overrides(provider, model)
    provider_instance = get_provider(settings)
    from persona.models import Message

    response = provider_instance.chat([Message(role="user", content=message)])
    _print_response(response.message.content or "", "Persona")


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
            console.print("[red]Usage: persona memory add <key> <value>[/red]")
            raise typer.Exit(1)
        console.print(store.add(key, value))
    elif action == "remove":
        if not key:
            console.print("[red]Usage: persona memory remove <key>[/red]")
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
        f"[bold]Persona Configuration[/bold]\n"
        f"Provider: {settings.provider}\n"
        f"Ollama: {settings.ollama_base_url} / {settings.ollama_model}\n"
        f"OpenAI: {settings.openai_base_url} / {settings.openai_model}\n"
        f"Workspace: {settings.workspace}\n"
        f"Data dir: {settings.data_dir}\n"
        f"Web: http://{settings.web_host}:{settings.web_port}",
        title="persona status",
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
    else:
        if not settings.openai_api_key:
            console.print("[yellow]Warning: PERSONA_OPENAI_API_KEY is not set.[/yellow]")
        else:
            console.print("[green]OpenAI API key configured.[/green]")

    console.print("\n[bold]Crew[/bold]")
    crew()


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
            persona = data.get("persona_id", "?")
            count = len(data.get("messages", []))
            console.print(f"  {p.stem}  ({persona}, {count} messages)")
        except Exception:
            console.print(f"  {p.stem}  (corrupt)")


def _make_agent(settings: Settings, persona=None) -> Agent:
    def on_tool_call(name: str, args: dict) -> None:
        console.print(f"[dim]→ {name}({json.dumps(args, ensure_ascii=False)[:120]})[/dim]")

    def on_tool_result(name: str, result: str) -> None:
        preview = result[:200] + ("..." if len(result) > 200 else "")
        console.print(f"[dim]← {name}: {preview}[/dim]")

    return Agent(settings, persona=persona, on_tool_call=on_tool_call, on_tool_result=on_tool_result)


def _print_response(text: str, title: str = "Agent") -> None:
    console.print()
    console.print(Panel(Markdown(text), title=f"[bold green]{title}[/bold green]", border_style="green"))


if __name__ == "__main__":
    app()
