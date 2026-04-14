"""napoln resolve — Mark merge conflicts as resolved."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import manifest
from napoln.core.merger import has_conflict_markers


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_resolve(
    name: str,
    agent_id: str | None = None,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the resolve command.

    Returns:
        Exit code (0=success, 1=error, 2=unresolved conflicts).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if name not in mf.skills:
        output.error(f"Skill '{name}' is not installed.")
        return 1

    entry = mf.skills[name]
    agents_to_check = [agent_id] if agent_id else list(entry.agents.keys())
    still_conflicted = []

    for aid in agents_to_check:
        if aid not in entry.agents:
            continue

        placement = entry.agents[aid]
        placement_path = Path(placement.path).expanduser()

        if not placement_path.exists():
            output.warning(f"Placement missing: {placement_path}")
            continue

        # Check for conflict markers in SKILL.md
        skill_md = placement_path / "SKILL.md"
        if skill_md.exists() and has_conflict_markers(skill_md):
            still_conflicted.append(f"{aid}: {placement_path}")
            output.error(
                f"Conflict markers still present in {skill_md}",
                fix="Edit the file to resolve all <<<<<<< / ======= / >>>>>>> markers.",
            )

    if still_conflicted:
        return 2

    # Update manifest timestamp
    from napoln.core.manifest import _now_iso
    entry.updated = _now_iso()
    manifest.write_manifest(mf, manifest_path)
    output.success(f"'{name}' marked as resolved.")

    return 0
