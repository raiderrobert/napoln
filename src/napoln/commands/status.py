"""napoln status — Show installed skills and their state."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import manifest
from napoln.core.store import get_stored_skill


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _check_placement_status(placement_path: Path, store_path: Path | None) -> str:
    """Check if a placement is clean, modified, or missing."""
    if not placement_path.exists():
        return "missing"

    if store_path is None:
        return "unknown"

    # Compare files
    for f in store_path.rglob("*"):
        if f.is_file() and f.name != ".napoln":
            rel = f.relative_to(store_path)
            placement_file = placement_path / rel
            if not placement_file.exists():
                return "modified"
            if placement_file.read_bytes() != f.read_bytes():
                return "modified"

    # Check for extra files in placement
    for f in placement_path.rglob("*"):
        if f.is_file() and f.name != ".napoln":
            rel = f.relative_to(placement_path)
            store_file = store_path / rel
            if not store_file.exists():
                return "modified"

    return "clean"


def run_status(
    scope: str = "global",
    project_root: Path | None = None,
    json_output: bool = False,
) -> int:
    """Execute the status command.

    Returns:
        Exit code (0=success).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if not mf.skills:
        output.info("No skills installed.")
        return 0

    if json_output:
        data = {}
        for name, entry in sorted(mf.skills.items()):
            store_path = get_stored_skill(name, entry.version, entry.store_hash, napoln_home)
            agents_data = {}
            for agent_id, placement in entry.agents.items():
                placement_path = Path(placement.path).expanduser()
                status = _check_placement_status(placement_path, store_path)
                agents_data[agent_id] = {
                    "path": str(placement_path),
                    "status": status,
                    "link_mode": placement.link_mode,
                    "scope": placement.scope,
                }
            data[name] = {
                "version": entry.version,
                "source": entry.source,
                "store_hash": entry.store_hash,
                "installed": entry.installed,
                "updated": entry.updated,
                "agents": agents_data,
            }
        output.print_json(data)
        return 0

    for name, entry in sorted(mf.skills.items()):
        store_path = get_stored_skill(name, entry.version, entry.store_hash, napoln_home)
        agents_info = []
        for agent_id, placement in sorted(entry.agents.items()):
            placement_path = Path(placement.path).expanduser()
            status = _check_placement_status(placement_path, store_path)
            agents_info.append((agent_id, str(placement_path), status))

        output.skill_status_line(
            name,
            entry.version,
            entry.source,
            agents=agents_info,
            scope=list(entry.agents.values())[0].scope if entry.agents else "global",
        )

    return 0
