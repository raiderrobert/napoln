"""napoln list — Show installed skills and where they are placed."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import manifest


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _abbreviate_path(path: str, home: str) -> str:
    """Shorten an absolute path for display (e.g. ~/.claude/skills)."""
    if path.startswith(home):
        return "~" + path[len(home) :]
    return path


AGENT_SHORT_NAMES: dict[str, str] = {
    "claude-code": "claude",
    "gemini-cli": "gemini",
    "pi": "pi",
    "codex": "codex",
    "cursor": "cursor",
}


def _get_agent_names(entry: manifest.SkillEntry) -> list[str]:
    """Get short agent names for a skill entry."""
    names: list[str] = []
    seen: set[str] = set()
    for agent_id in entry.agents:
        short = AGENT_SHORT_NAMES.get(agent_id, agent_id)
        if short not in seen:
            seen.add(short)
            names.append(short)
    return names


def _common_agents(mf: manifest.Manifest) -> list[str] | None:
    """If all skills share the same agents, return them. Else None."""
    common: list[str] | None = None
    for entry in mf.skills.values():
        agents = _get_agent_names(entry)
        if common is None:
            common = agents
        elif agents != common:
            return None
    return common


def _abbreviate_source(source: str) -> str:
    """Shorten a source for display."""
    if source == "bundled":
        return source
    # Local paths — show just the leaf directory
    if source.startswith("/") or source.startswith("./"):
        return Path(source).name
    # For git sources like "github.com/owner/repo/skills/name", show "owner/repo"
    parts = source.strip("/").split("/")
    if len(parts) >= 3 and "." in parts[0]:
        return f"{parts[1]}/{parts[2]}"
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return source


def _print_skills(
    mf: manifest.Manifest,
    label: str,
) -> None:
    """Print skills from a manifest under a section label."""
    import typer

    if not mf.skills:
        return

    common = _common_agents(mf)

    # Build header with common agents if they exist
    if common:
        agents_str = ", ".join(common)
        output.header(f"{label} (→ {agents_str}):")
    else:
        output.header(f"{label}:")

    # Calculate dynamic column widths
    entries = sorted(mf.skills.items())
    max_name = max(len(name) for name, _ in entries)
    max_ver = max(len(entry.version) for _, entry in entries)

    for name, entry in entries:
        source = _abbreviate_source(entry.source)

        name_col = f"  {name:<{max_name}}"
        ver_col = f"  {entry.version:<{max_ver}}"
        source_col = f"  {source}"

        # If agents differ per skill, show them on this line
        suffix = ""
        if not common:
            agents = _get_agent_names(entry)
            suffix = f"  → {', '.join(agents)}"

        typer.echo(
            typer.style(name_col, bold=True)
            + typer.style(ver_col, fg=typer.colors.BRIGHT_BLACK)
            + typer.style(source_col, fg=typer.colors.BRIGHT_BLACK)
            + suffix
        )


def _build_json(
    global_mf: manifest.Manifest | None,
    project_mf: manifest.Manifest | None,
) -> dict:
    """Build JSON output for installed skills."""
    data: dict = {}

    if global_mf is not None:
        data["global"] = {}
        for name, entry in sorted(global_mf.skills.items()):
            agents_data = {}
            for agent_id, placement in entry.agents.items():
                agents_data[agent_id] = {
                    "path": placement.path,
                    "link_mode": placement.link_mode,
                }
            data["global"][name] = {
                "version": entry.version,
                "source": entry.source,
                "agents": agents_data,
            }

    if project_mf is not None:
        data["project"] = {}
        for name, entry in sorted(project_mf.skills.items()):
            agents_data = {}
            for agent_id, placement in entry.agents.items():
                agents_data[agent_id] = {
                    "path": placement.path,
                    "link_mode": placement.link_mode,
                }
            data["project"][name] = {
                "version": entry.version,
                "source": entry.source,
                "agents": agents_data,
            }

    return data


def run_list(
    project_only: bool = False,
    global_only: bool = False,
    json_output: bool = False,
) -> int:
    """Execute the list command.

    Returns:
        Exit code (0=always).
    """
    napoln_home = _get_napoln_home()

    global_mf: manifest.Manifest | None = None
    project_mf: manifest.Manifest | None = None

    # Read global manifest
    global_path = manifest.get_manifest_path(napoln_home)
    if not project_only:
        global_mf = manifest.read_manifest(global_path)

    # Read project manifest if it exists
    if not global_only:
        project_path = Path.cwd() / ".napoln" / "manifest.toml"
        if project_path.exists() and project_path.resolve() != global_path.resolve():
            project_mf = manifest.read_manifest(project_path)

    if json_output:
        output.print_json(_build_json(global_mf, project_mf))
        return 0

    has_any = False

    if global_mf and global_mf.skills:
        _print_skills(global_mf, "Global")
        has_any = True

    if project_mf and project_mf.skills:
        if has_any:
            import typer

            typer.echo()  # blank line between sections
        cwd_short = _abbreviate_path(str(Path.cwd()), str(Path.home()))
        project_label = f"Project ({cwd_short})"
        _print_skills(project_mf, project_label)
        has_any = True

    if not has_any:
        output.info("No skills installed.")

    return 0
