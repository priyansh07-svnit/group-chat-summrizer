"""Digest writer – produces daily Markdown digests and terminal output."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


def write_digest(
    summaries: dict[str, str],
    digests_dir: str | Path,
    today: date | None = None,
) -> Path:
    """Write a daily digest Markdown file.

    Parameters
    ----------
    summaries:
        Mapping of ``chat_filename → summary_text``.
    digests_dir:
        Directory to write the digest into.
    today:
        Override the date (defaults to today).

    Returns
    -------
    Path
        Path to the written Markdown file.
    """
    if today is None:
        today = date.today()

    digests_dir = Path(digests_dir)
    digests_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{today.isoformat()}.md"
    filepath = digests_dir / filename

    lines: list[str] = [f"# Chat Digest – {today.isoformat()}\n"]

    for chat_name, summary in sorted(summaries.items()):
        pretty_name = Path(chat_name).stem.replace("_", " ").replace("-", " ").title()
        lines.append(f"## {pretty_name}\n")
        lines.append(summary)
        lines.append("")  # blank line

    content = "\n".join(lines).rstrip() + "\n"

    # Append if digest already exists (multiple runs in one day).
    if filepath.exists():
        existing = filepath.read_text(encoding="utf-8")
        content = existing.rstrip() + "\n\n---\n\n" + content

    filepath.write_text(content, encoding="utf-8")
    return filepath


def print_digest(summaries: dict[str, str], console: Console | None = None) -> None:
    """Pretty-print the digest to the terminal using Rich.

    Parameters
    ----------
    summaries:
        Mapping of ``chat_filename → summary_text``.
    console:
        Optional Rich console (useful for testing).
    """
    if console is None:
        console = Console()

    if not summaries:
        console.print("[dim]Nothing new to summarize. Going back to sleep...[/dim]")
        return

    console.print()
    console.print(
        Panel(
            "[bold green]Group Chat Digest[/bold green]",
            subtitle="slow and steady",
            expand=False,
        )
    )
    console.print()

    for chat_name, summary in sorted(summaries.items()):
        pretty_name = Path(chat_name).stem.replace("_", " ").replace("-", " ").title()
        console.print(f"[bold cyan]>> {pretty_name}[/bold cyan]")
        console.print(Markdown(summary))
        console.print()
