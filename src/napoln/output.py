"""Terminal output formatting for napoln."""

from __future__ import annotations

import json
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


def install_summary(
    skills: list[str],
    agent_names: list[str],
    scope: str = "global",
) -> None:
    """Print a summary of what will be installed."""
    typer.echo()
    header(f"Installing {len(skills)} skill(s):")
    for name in skills:
        typer.echo(f"  {typer.style('•', fg=SUCCESS)} {name}")
    agents_str = ", ".join(agent_names)
    dim(f"  Agents: {agents_str}")
    dim(f"  Scope:  {scope}")
    typer.echo()


def skill_list_line(
    name: str,
    version: str,
    source: str,
    placements: str = "",
) -> None:
    """Print a single skill line in list output.

    Args:
        name: Skill name.
        version: Version string.
        source: Abbreviated source.
        placements: Abbreviated placement paths.
    """
    name_col = typer.style(f"  {name:<22}", bold=True)
    version_col = f"v{version:<10}"
    source_col = typer.style(f"{source:<24}", fg=DIM)
    typer.echo(f"{name_col}{version_col}{source_col}{placements}")
