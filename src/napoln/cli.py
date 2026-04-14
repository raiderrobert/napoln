"""napoln CLI entry point.

Built with Typer for type-hint based argument parsing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from napoln import __version__

app = typer.Typer(
    name="napoln",
    help="A package manager for agent skills.",
    no_args_is_help=True,
    rich_markup_mode=None,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"napoln {__version__}")
        raise typer.Exit()


# ─── Global options ───────────────────────────────────────────────────────────


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version_callback, is_eager=True,
                           help="Show napoln version.")
    ] = False,
) -> None:
    """napoln — A package manager for agent skills."""


# ─── add ──────────────────────────────────────────────────────────────────────


@app.command()
def add(
    source: Annotated[str, typer.Argument(help="Git source, local path, or registry name.")],
    agents: Annotated[Optional[str], typer.Option("--agents", help="Target agents (comma-separated).")] = None,
    version: Annotated[Optional[str], typer.Option("--version", help="Version constraint.")] = None,
    project: Annotated[bool, typer.Option("--project", help="Install to current project.")] = False,
    skill: Annotated[Optional[str], typer.Option("--skill", help="Select specific skill from multi-skill repo.")] = None,
    name: Annotated[Optional[str], typer.Option("--name", help="Override skill name.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change without applying.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress non-error output.")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")] = False,
) -> None:
    """Install a skill from a git source or local path."""
    from napoln.commands.add import run_add

    agent_ids = [a.strip() for a in agents.split(",")] if agents else None
    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_add(
        source=source,
        agent_ids=agent_ids,
        version_constraint=version,
        scope=scope,
        project_root=project_root,
        skill_name_override=name,
        dry_run=dry_run,
    )
    raise typer.Exit(code=exit_code)


# ─── remove ───────────────────────────────────────────────────────────────────


@app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Skill name to remove.")],
    agents: Annotated[Optional[str], typer.Option("--agents", help="Remove from specific agents only.")] = None,
    project: Annotated[bool, typer.Option("--project", help="Remove from project scope.")] = False,
    keep_store: Annotated[bool, typer.Option("--keep-store", help="Don't mark store entry for GC.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change.")] = False,
) -> None:
    """Remove an installed skill."""
    from napoln.commands.remove import run_remove

    agent_ids = [a.strip() for a in agents.split(",")] if agents else None
    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_remove(
        name=name,
        agent_ids=agent_ids,
        scope=scope,
        project_root=project_root,
        keep_store=keep_store,
        dry_run=dry_run,
    )
    raise typer.Exit(code=exit_code)


# ─── upgrade ──────────────────────────────────────────────────────────────────


@app.command()
def upgrade(
    name: Annotated[Optional[str], typer.Argument(help="Skill name to upgrade (all if omitted).")] = None,
    version: Annotated[Optional[str], typer.Option("--version", help="Upgrade to specific version.")] = None,
    agents: Annotated[Optional[str], typer.Option("--agents", help="Upgrade for specific agents only.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change.")] = False,
    force: Annotated[bool, typer.Option("--force", help="Replace working copies without merging.")] = False,
    project: Annotated[bool, typer.Option("--project", help="Upgrade project-scoped skills.")] = False,
) -> None:
    """Upgrade one or all skills."""
    from napoln.commands.upgrade import run_upgrade

    agent_ids = [a.strip() for a in agents.split(",")] if agents else None
    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_upgrade(
        name=name,
        version_constraint=version,
        agent_ids=agent_ids,
        dry_run=dry_run,
        force=force,
        scope=scope,
        project_root=project_root,
    )
    raise typer.Exit(code=exit_code)


# ─── status ───────────────────────────────────────────────────────────────────


@app.command()
def status(
    project: Annotated[bool, typer.Option("--project", help="Show project skills only.")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")] = False,
) -> None:
    """Show installed skills and their state."""
    from napoln.commands.status import run_status

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_status(scope=scope, project_root=project_root, json_output=json_out)
    raise typer.Exit(code=exit_code)


# ─── diff ─────────────────────────────────────────────────────────────────────


@app.command()
def diff(
    name: Annotated[str, typer.Argument(help="Skill name to diff.")],
    agent: Annotated[Optional[str], typer.Option("--agent", help="Diff for specific agent only.")] = None,
    project: Annotated[bool, typer.Option("--project", help="Diff project-scoped skill.")] = False,
) -> None:
    """Show local modifications vs. upstream."""
    from napoln.commands.diff import run_diff

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_diff(name=name, agent_id=agent, scope=scope, project_root=project_root)
    raise typer.Exit(code=exit_code)


# ─── resolve ──────────────────────────────────────────────────────────────────


@app.command()
def resolve(
    name: Annotated[str, typer.Argument(help="Skill name to mark as resolved.")],
    agent: Annotated[Optional[str], typer.Option("--agent", help="Resolve for specific agent only.")] = None,
    project: Annotated[bool, typer.Option("--project", help="Resolve project-scoped skill.")] = False,
) -> None:
    """Mark a skill's merge conflicts as resolved."""
    from napoln.commands.resolve import run_resolve

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_resolve(name=name, agent_id=agent, scope=scope, project_root=project_root)
    raise typer.Exit(code=exit_code)


# ─── sync ─────────────────────────────────────────────────────────────────────


@app.command()
def sync(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be synced.")] = False,
    project: Annotated[bool, typer.Option("--project", help="Sync project-scoped skills.")] = False,
) -> None:
    """Re-create missing placements from manifest + store."""
    from napoln.commands.sync import run_sync

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_sync(dry_run=dry_run, scope=scope, project_root=project_root)
    raise typer.Exit(code=exit_code)


# ─── install ──────────────────────────────────────────────────────────────────


@app.command()
def install(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be synced.")] = False,
    project: Annotated[bool, typer.Option("--project", help="Install project-scoped skills.")] = False,
) -> None:
    """Alias for sync. Reads manifest and ensures all placements exist."""
    from napoln.commands.sync import run_sync

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_sync(dry_run=dry_run, scope=scope, project_root=project_root)
    raise typer.Exit(code=exit_code)


# ─── doctor ───────────────────────────────────────────────────────────────────


@app.command()
def doctor(
    project: Annotated[bool, typer.Option("--project", help="Check project-scoped skills.")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")] = False,
) -> None:
    """Health check."""
    from napoln.commands.doctor import run_doctor

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_doctor(scope=scope, project_root=project_root, json_output=json_out)
    raise typer.Exit(code=exit_code)


# ─── gc ───────────────────────────────────────────────────────────────────────


@app.command()
def gc(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
    all_cache: Annotated[bool, typer.Option("--all", help="Also remove cache entries.")] = False,
    project: Annotated[bool, typer.Option("--project", help="Consider project manifest.")] = False,
) -> None:
    """Remove unreferenced store entries."""
    from napoln.commands.gc import run_gc

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_gc(
        dry_run=dry_run, clean_cache=all_cache,
        scope=scope, project_root=project_root,
    )
    raise typer.Exit(code=exit_code)


# ─── list ─────────────────────────────────────────────────────────────────────


@app.command(name="list")
def list_cmd(
    source: Annotated[str, typer.Argument(help="Git source or local path to list skills from.")],
) -> None:
    """List available skills from a source without installing."""
    from napoln.commands.list_cmd import run_list

    exit_code = run_list(source=source)
    raise typer.Exit(code=exit_code)


# ─── config ───────────────────────────────────────────────────────────────────


config_app = typer.Typer(help="View or edit configuration.", no_args_is_help=False)
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_default(
    ctx: typer.Context,
) -> None:
    """View or edit configuration."""
    if ctx.invoked_subcommand is None:
        from napoln.commands.config import run_config_show
        exit_code = run_config_show()
        raise typer.Exit(code=exit_code)


@config_app.command(name="set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key (dot notation).")],
    value: Annotated[str, typer.Argument(help="Configuration value.")],
) -> None:
    """Set a configuration value."""
    from napoln.commands.config import run_config_set
    exit_code = run_config_set(key, value)
    raise typer.Exit(code=exit_code)


# ─── telemetry ────────────────────────────────────────────────────────────────


telemetry_app = typer.Typer(help="Manage telemetry settings.", no_args_is_help=True)
app.add_typer(telemetry_app, name="telemetry")


@telemetry_app.command(name="status")
def telemetry_status() -> None:
    """Show telemetry state."""
    from napoln.commands.telemetry_cmd import run_telemetry_status
    exit_code = run_telemetry_status()
    raise typer.Exit(code=exit_code)


@telemetry_app.command(name="enable")
def telemetry_enable() -> None:
    """Enable telemetry."""
    from napoln.commands.telemetry_cmd import run_telemetry_enable
    exit_code = run_telemetry_enable()
    raise typer.Exit(code=exit_code)


@telemetry_app.command(name="disable")
def telemetry_disable() -> None:
    """Disable telemetry."""
    from napoln.commands.telemetry_cmd import run_telemetry_disable
    exit_code = run_telemetry_disable()
    raise typer.Exit(code=exit_code)


@telemetry_app.command(name="show-data")
def telemetry_show_data() -> None:
    """Show what data would be sent."""
    from napoln.commands.telemetry_cmd import run_telemetry_show_data
    exit_code = run_telemetry_show_data()
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
