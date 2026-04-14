"""napoln remove — Remove an installed skill."""

from __future__ import annotations

import shutil
from pathlib import Path

from napoln import output
from napoln.core import manifest


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_remove(
    name: str,
    agent_ids: list[str] | None = None,
    scope: str = "global",
    project_root: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Execute the remove command.

    Returns:
        Exit code (0=success, 1=error).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if name not in mf.skills:
        output.info(f"'{name}' is not installed.")
        return 0

    entry = mf.skills[name]

    if dry_run:
        output.dry_run_header()

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
        output.would("update manifest")
        output.dry_run_footer()
        return 0

    # Update manifest
    mf = manifest.remove_skill_from_manifest(mf, name, agent_ids)
    manifest.write_manifest(mf, manifest_path)
    output.success(f"Removed '{name}'")

    return 0
