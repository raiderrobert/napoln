"""napoln remove — Remove an installed skill."""

from __future__ import annotations

import shutil
from pathlib import Path

from napoln import output
from napoln.core import manifest
from napoln.core.resolver import normalize_source_for_match


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _resolve_from_source(
    from_source: str,
    mf: manifest.Manifest,
) -> list[str]:
    """Resolve --from-source to matching skill names.

    Args:
        from_source: Source identifier (shorthand or URL).
        mf: Current manifest.

    Returns:
        List of skill names that match the source.
    """
    normalized = normalize_source_for_match(from_source)
    matching_names: list[str] = []

    for name, entry in mf.skills.items():
        entry_source = normalize_source_for_match(entry.source)
        if entry_source == normalized:
            matching_names.append(name)

    return matching_names


def run_remove(
    names: list[str],
    from_source: str | None = None,
    agent_ids: list[str] | None = None,
    scope: str = "global",
    project_root: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Execute the remove command.

    Args:
        names: Skill names to remove.
        from_source: If set, remove all skills from this repository.
        agent_ids: If specified, only remove these agent placements.
        scope: "global" or "project".
        project_root: Project root for project scope.
        dry_run: Show what would happen without applying.

    Returns:
        Exit code (0=success, 1=error).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    # Resolve --from-source to names and merge with explicit names
    from_source_names = []
    if from_source:
        from_source_names = _resolve_from_source(from_source, mf)
        if not from_source_names:
            output.info(f"No skills found from '{from_source}'.")
        # Merge with explicit names, avoid duplicates
        existing = set(from_source_names)
        for name in names:
            if name not in existing:
                from_source_names.append(name)
        names = from_source_names

    if not names:
        output.info("No skills specified.")
        return 0

    if dry_run:
        output.dry_run_header()

    exit_code = 0

    for name in names:
        result = _remove_single(
            name=name,
            mf=mf,
            manifest_path=manifest_path,
            agent_ids=agent_ids,
            dry_run=dry_run,
        )
        if result != 0:
            exit_code = 1

    if not dry_run:
        # Write manifest once after all removals
        manifest.write_manifest(mf, manifest_path)

    return exit_code


def _remove_single(
    name: str,
    mf: manifest.Manifest,
    manifest_path: Path,
    agent_ids: list[str] | None,
    dry_run: bool,
) -> int:
    """Remove a single skill from manifest and filesystem.

    Returns:
        0 on success, 1 on error.
    """
    if name not in mf.skills:
        output.info(f"'{name}' is not installed.")
        return 0

    entry = mf.skills[name]

    # Determine which agents to remove
    agents_to_remove = agent_ids if agent_ids else list(entry.agents.keys())

    for agent_id in agents_to_remove:
        if agent_id not in entry.agents:
            continue

        placement = entry.agents[agent_id]
        placement_path = Path(placement.path).expanduser()

        if dry_run:
            output.would(f"remove placement {placement_path}")
        else:
            if placement_path.exists():
                shutil.rmtree(placement_path)
                output.success(f"Removed placement: {placement_path}")
            else:
                output.dim(f"  Placement already gone: {placement_path}")

    if dry_run:
        return 0

    # Update manifest - remove skill or just the agent placements
    mf = manifest.remove_skill_from_manifest(mf, name, agent_ids)
    output.success(f"Removed '{name}'")

    return 0
