"""CLI entry-point for group-chat-summarizer."""

from __future__ import annotations

import platform
import sys
import time
from pathlib import Path

import typer
from rich.console import Console

from chat_summarizer.config import load_config
from chat_summarizer.digest import print_digest, write_digest
from chat_summarizer.ollama_client import OllamaError, check_health
from chat_summarizer.parsers import parse_file
from chat_summarizer.state import (
    get_last_timestamp,
    load_state,
    save_state,
    update_timestamp,
)
from chat_summarizer.summarizer import summarize_messages

app = typer.Typer(
    name="summarize",
    help="Group Chat Summarizer - lazy overnight digests, fully local.",
    add_completion=False,
)
console = Console()


def _resolve_config(config_path: str | None) -> "chat_summarizer.config.AppConfig":
    """Load config, printing a helpful message if the file is missing."""
    from chat_summarizer.config import AppConfig  # noqa: F811 – for type hint

    cfg = load_config(config_path)
    return cfg


def _run_once(config_path: str | None) -> dict[str, str]:
    """Core logic: parse → filter → summarize → save state → return summaries."""
    cfg = _resolve_config(config_path)
    chats_dir = Path(cfg.chats_dir)

    if not chats_dir.exists():
        console.print(f"[yellow]Chats directory '{chats_dir}' not found. Creating it.[/yellow]")
        chats_dir.mkdir(parents=True, exist_ok=True)
        return {}

    chat_files = sorted(
        p for p in chats_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".txt", ".json") and p.name != ".gitkeep"
    )

    if not chat_files:
        console.print("[dim]No chat files found in the chats/ folder.[/dim]")
        return {}

    state = load_state(chats_dir)
    summaries: dict[str, str] = {}

    for chat_file in chat_files:
        try:
            messages = parse_file(chat_file)
        except (ValueError, Exception) as exc:
            console.print(f"[red]Error parsing {chat_file.name}: {exc}[/red]")
            continue

        if not messages:
            continue

        # Incremental: filter to messages newer than last run.
        last_ts = get_last_timestamp(state, chat_file.name)
        if last_ts:
            messages = [m for m in messages if m.timestamp > last_ts]

        if not messages:
            continue

        console.print(f"[dim]Summarizing {chat_file.name} ({len(messages)} new messages)...[/dim]")
        try:
            summary = summarize_messages(messages, cfg)
        except OllamaError as exc:
            console.print(f"[red]Ollama error for {chat_file.name}: {exc}[/red]")
            continue

        summaries[chat_file.name] = summary
        update_timestamp(state, chat_file.name, messages[-1].timestamp)

    save_state(chats_dir, state)
    return summaries


# ── Commands ────────────────────────────────────────────────────────────────


@app.command()
def run(
    config: str = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Process all chats and print the digest."""
    summaries = _run_once(config)
    if summaries:
        cfg = _resolve_config(config)
        digest_path = write_digest(summaries, cfg.digests_dir)
        print_digest(summaries, console)
        console.print(f"[green][OK] Digest saved to {digest_path}[/green]")
    else:
        console.print("[dim]Nothing new. The sloth sleeps...[/dim]")


@app.command()
def watch(
    config: str = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Continuously watch for new chats (Ctrl+C to stop)."""
    cfg = _resolve_config(config)
    interval = cfg.watch.interval_seconds
    console.print(f"[bold]Watching for new chats every {interval}s. Ctrl+C to stop.[/bold]")

    try:
        while True:
            summaries = _run_once(config)
            if summaries:
                digest_path = write_digest(summaries, cfg.digests_dir)
                print_digest(summaries, console)
                console.print(f"[green]Digest saved to {digest_path}[/green]")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Sloth going back to sleep. Bye![/dim]")


@app.command("install-schedule")
def install_schedule(
    config: str = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
    hour: int = typer.Option(7, "--hour", help="Hour to run (24h format)"),
    minute: int = typer.Option(0, "--minute", help="Minute to run"),
) -> None:
    """Print or install a nightly schedule (cron / Task Scheduler)."""
    # Build the command that should be scheduled.
    python = sys.executable
    cmd = f"{python} -m chat_summarizer run"
    if config:
        cmd += f" --config {config}"

    system = platform.system()

    if system == "Windows":
        task_name = "GroupChatSummarizer"
        schtasks_cmd = (
            f'schtasks /create /tn "{task_name}" /tr "{cmd}" '
            f"/sc daily /st {hour:02d}:{minute:02d} /f"
        )
        console.print("[bold]Windows Task Scheduler command:[/bold]")
        console.print(f"\n  {schtasks_cmd}\n")
        console.print("[dim]Run the above in an elevated (Admin) terminal to install.[/dim]")
    else:
        cron_line = f"{minute} {hour} * * * {cmd}"
        console.print("[bold]Add this line to your crontab (crontab -e):[/bold]")
        console.print(f"\n  {cron_line}\n")
        console.print("[dim]This will run the summarizer daily at {hour:02d}:{minute:02d}.[/dim]")


@app.command()
def check(
    config: str = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Verify that Ollama is running and the model is pulled."""
    cfg = _resolve_config(config)
    ok, message = check_health(cfg.ollama)
    if ok:
        console.print(f"[bold green][OK] {message}[/bold green]")
    else:
        console.print(f"[bold red][FAIL] {message}[/bold red]")
        raise typer.Exit(code=1)


def main() -> None:
    """Package entry-point."""
    app()


if __name__ == "__main__":
    main()
