"""napoln list — Show installed skills and where they are placed."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import manifest


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _abbreviate_path(path: str, home: str) -> str:
    """Shorten an absolute path for display (e.g. ~/.claude/)."""
    if path.startswith(home):
        return "~" + path[len(home) :]
    return path


def _get_placement_dirs(entry: manifest.SkillEntry) -> list[str]:
    """Extract unique shortened parent dirs from agent placements."""
    home = str(Path.home())
    seen: set[str] = set()
    dirs: list[str] = []
    for placement in entry.agents.values():
        # Go up one level from the skill-name dir to get the agent skills dir
        parent = str(Path(placement.path).parent)
        short = _abbreviate_path(parent, home)
        if short not in seen:
            seen.add(short)
            dirs.append(short)
    return dirs


def _print_skills(
    mf: manifest.Manifest,
    napoln_home: Path,
    label: str,
) -> None:
    """Print skills from a manifest under a section label."""
    if not mf.skills:
        return

    output.header(f"{label}:")
    for name, entry in sorted(mf.skills.items()):
        source = entry.source
        # Abbreviate source for display
        if "/" in source:
            # Show just the last two path components
            parts = source.rstrip("/").split("/")
            if len(parts) >= 2:
                source = "/".join(parts[-2:])

        dirs = _get_placement_dirs(entry)
        dirs_str = "  ".join(dirs) if dirs else ""
        output.skill_list_line(name, entry.version, source, dirs_str)


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
    if not project_only:
        global_path = manifest.get_manifest_path(napoln_home)
        global_mf = manifest.read_manifest(global_path)

    # Read project manifest if it exists
    if not global_only:
        project_path = Path.cwd() / ".napoln" / "manifest.toml"
        # Only read project manifest if it's NOT the same as the global manifest
        if project_path.exists() and project_path.resolve() != global_path.resolve():
            project_mf = manifest.read_manifest(project_path)

    if json_output:
        output.print_json(_build_json(global_mf, project_mf))
        return 0

    has_any = False

    if global_mf and global_mf.skills:
        _print_skills(global_mf, napoln_home, "Global")
        has_any = True

    if project_mf and project_mf.skills:
        if has_any:
            import typer

            typer.echo()  # blank line between sections
        project_label = f"Project ({Path.cwd()})"
        _print_skills(project_mf, napoln_home, project_label)
        has_any = True

    if not has_any:
        output.info("No skills installed.")

    return 0
