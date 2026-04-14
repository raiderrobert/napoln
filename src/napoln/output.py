"""Terminal output formatting for napoln."""

from __future__ import annotations

import json
import sys
from typing import Any

import typer


# Colors
SUCCESS = typer.colors.GREEN
WARNING = typer.colors.YELLOW
ERROR = typer.colors.RED
INFO = typer.colors.BLUE
DIM = typer.colors.BRIGHT_BLACK
BOLD = typer.colors.WHITE


def success(message: str) -> None:
    """Print a success message."""
    typer.echo(typer.style("✓ ", fg=SUCCESS) + message)


def warning(message: str) -> None:
    """Print a warning message."""
    typer.echo(typer.style("⚠ ", fg=WARNING) + message, err=True)


def error(message: str, cause: str = "", fix: str = "") -> None:
    """Print an error message with optional cause and fix."""
    typer.echo(typer.style("✗ ", fg=ERROR) + message, err=True)
    if cause:
        typer.echo(typer.style("  Cause: ", fg=DIM) + cause, err=True)
    if fix:
        typer.echo(typer.style("  Fix:   ", fg=DIM) + fix, err=True)


def info(message: str) -> None:
    """Print an info message."""
    typer.echo(typer.style("ℹ ", fg=INFO) + message)


def dim(message: str) -> None:
    """Print a dim/muted message."""
    typer.echo(typer.style(message, fg=DIM))


def header(message: str) -> None:
    """Print a bold header."""
    typer.echo(typer.style(message, bold=True))


def dry_run_header() -> None:
    """Print the dry-run banner."""
    typer.echo(typer.style("Dry run — no changes will be made", fg=WARNING, bold=True))
    typer.echo()


def dry_run_footer() -> None:
    """Print the dry-run footer."""
    typer.echo()
    typer.echo(typer.style("Run without --dry-run to apply.", fg=DIM))


def would(message: str) -> None:
    """Print a 'Would ...' message for dry-run."""
    typer.echo(typer.style("  Would ", fg=WARNING) + message)


def print_json(data: Any) -> None:
    """Print JSON output."""
    typer.echo(json.dumps(data, indent=2, default=str))


def skill_status_line(
    name: str, version: str, source: str,
    agents: list[tuple[str, str, str]] | None = None,
    scope: str = "global",
) -> None:
    """Print a skill status line.

    Args:
        name: Skill name.
        version: Version string.
        source: Source identifier.
        agents: List of (agent_id, path, status) tuples.
        scope: "global" or "project".
    """
    scope_tag = f"  [{scope}]" if scope == "project" else ""
    typer.echo(
        typer.style(name, bold=True)
        + f" v{version} ({source}){scope_tag}"
    )
    if agents:
        for agent_id, path, status in agents:
            status_color = SUCCESS if status == "clean" else WARNING
            typer.echo(
                f"  {agent_id:<14} {path:<40} "
                + typer.style(status, fg=status_color)
            )
