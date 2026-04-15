"""napoln CLI entry point.

Built with Typer for type-hint based argument parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from napoln import __version__

app = typer.Typer(
    name="napoln",
    help="A package manager for agent skills.",
    no_args_is_help=True,
    rich_markup_mode=None,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"napoln {__version__}")
        raise typer.Exit()


# ─── Global options ───────────────────────────────────────────────────────────


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show napoln version."
        ),
    ] = False,
) -> None:
    """napoln — A package manager for agent skills."""


# ─── add ──────────────────────────────────────────────────────────────────────


@app.command()
def add(
    source: Annotated[str, typer.Argument(help="Git source, local path, or registry name.")],
    all_skills: Annotated[
        bool, typer.Option("--all", "-a", help="Install all skills from a multi-skill repo.")
    ] = False,
    skill: Annotated[
        Optional[str],
        typer.Option("--skill", "-s", help="Install a specific skill by name."),
    ] = None,
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Install to the current project.")
    ] = False,
    agents: Annotated[
        Optional[str],
        typer.Option("--agents", help="Override auto-detected agents (comma-separated)."),
    ] = None,
    version: Annotated[
        Optional[str], typer.Option("--version", help="Pin to a specific version.")
    ] = None,
    name: Annotated[Optional[str], typer.Option("--name", help="Override the skill name.")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would happen without applying.")
    ] = False,
) -> None:
    """Install skills from a git repo or local path."""
    from napoln.commands.add import run_add

    agent_ids = [a.strip() for a in agents.split(",")] if agents else None
    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    # Map --all flag to skill_filter='*'
    skill_filter = "*" if all_skills else skill

    exit_code = run_add(
        source=source,
        agent_ids=agent_ids,
        version_constraint=version,
        scope=scope,
        project_root=project_root,
        skill_name_override=name,
        skill_filter=skill_filter,
        dry_run=dry_run,
    )
    raise typer.Exit(code=exit_code)


# ─── remove ───────────────────────────────────────────────────────────────────


@app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Skill name to remove.")],
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Remove from project scope.")
    ] = False,
    agents: Annotated[
        Optional[str], typer.Option("--agents", help="Remove from specific agents only.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen.")] = False,
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
        dry_run=dry_run,
    )
    raise typer.Exit(code=exit_code)


# ─── upgrade ──────────────────────────────────────────────────────────────────


@app.command()
def upgrade(
    name: Annotated[
        Optional[str], typer.Argument(help="Skill to upgrade (all if omitted).")
    ] = None,
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Upgrade project-scoped skills.")
    ] = False,
    version: Annotated[
        Optional[str], typer.Option("--version", help="Upgrade to a specific version.")
    ] = None,
    agents: Annotated[
        Optional[str], typer.Option("--agents", help="Upgrade for specific agents only.")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Replace working copies without merging.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen.")] = False,
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


# ─── list ─────────────────────────────────────────────────────────────────────


@app.command(name="list")
def list_cmd(
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Show only project skills.")
    ] = False,
    global_only: Annotated[
        bool, typer.Option("--global", "-g", help="Show only global skills.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show placement paths instead of agent names.")
    ] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")] = False,
) -> None:
    """Show installed skills and where they are placed."""
    from napoln.commands.list_cmd import run_list

    exit_code = run_list(
        project_only=project,
        global_only=global_only,
        show_paths=verbose,
        json_output=json_out,
    )
    raise typer.Exit(code=exit_code)


# ─── install ──────────────────────────────────────────────────────────────────


@app.command()
def install(
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Sync only the project manifest.")
    ] = False,
    global_only: Annotated[
        bool, typer.Option("--global", "-g", help="Sync only the global manifest.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen.")] = False,
) -> None:
    """Restore skill placements from manifests."""
    from napoln.commands.install import run_install

    exit_code = run_install(
        project_only=project,
        global_only=global_only,
        dry_run=dry_run,
    )
    raise typer.Exit(code=exit_code)


# ─── init ─────────────────────────────────────────────────────────────────────


@app.command()
def init(
    name: Annotated[
        Optional[str], typer.Argument(help="Skill name (uses current directory name if omitted).")
    ] = None,
) -> None:
    """Scaffold a new SKILL.md."""
    from napoln.commands.init import run_init

    exit_code = run_init(name=name)
    raise typer.Exit(code=exit_code)


# ─── setup ────────────────────────────────────────────────────────────────────


@app.command()
def setup(
    force: Annotated[
        bool,
        typer.Option("--force", help="Re-run setup even if default agents are already configured."),
    ] = False,
) -> None:
    """Choose which agents `napoln add` should install to by default."""
    from napoln.commands.setup import run_setup

    exit_code = run_setup(force=force)
    raise typer.Exit(code=exit_code)


# ─── config ───────────────────────────────────────────────────────────────────


config_app = typer.Typer(
    help="View configuration and run housekeeping.",
    no_args_is_help=False,
    add_completion=False,
)
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


@config_app.command(name="doctor")
def config_doctor(
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Check project-scoped skills.")
    ] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")] = False,
) -> None:
    """Health check: verify store integrity, placements, and provenance."""
    from napoln.commands.config import run_config_doctor

    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_config_doctor(scope=scope, project_root=project_root, json_output=json_out)
    raise typer.Exit(code=exit_code)


@config_app.command(name="gc")
def config_gc(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed.")] = False,
) -> None:
    """Remove unreferenced store entries."""
    from napoln.commands.config import run_config_gc

    exit_code = run_config_gc(dry_run=dry_run)
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
