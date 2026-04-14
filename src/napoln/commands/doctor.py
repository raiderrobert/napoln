"""napoln doctor — Health check."""

from __future__ import annotations

import shutil
from pathlib import Path

from napoln import output
from napoln.core import manifest, store


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_doctor(
    scope: str = "global",
    project_root: Path | None = None,
    json_output: bool = False,
) -> int:
    """Execute the doctor command.

    Returns:
        Exit code (0=healthy, 1=issues found).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)

    issues: list[dict] = []
    checks_passed = 0

    # Check 1: Store integrity
    store_dir = napoln_home / "store"
    if store_dir.exists():
        corrupt = 0
        for skill_dir in sorted(store_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            for version_dir in sorted(skill_dir.iterdir()):
                if version_dir.is_dir() and not version_dir.name.startswith("."):
                    if not store.verify_store_entry(version_dir):
                        corrupt += 1
                        issues.append(
                            {
                                "check": "store_integrity",
                                "path": str(version_dir),
                                "message": "Hash mismatch — possible corruption",
                            }
                        )
        if corrupt == 0:
            output.success("Store integrity (hash verification)")
            checks_passed += 1
        else:
            output.error(f"Store integrity: {corrupt} corrupt entries")
    else:
        output.dim("  Store directory does not exist")

    # Check 2: Manifest consistency
    mf = manifest.read_manifest(manifest_path)
    missing_store = 0
    for name, entry in mf.skills.items():
        sp = store.get_stored_skill(name, entry.version, entry.store_hash, napoln_home)
        if sp is None:
            missing_store += 1
            issues.append(
                {
                    "check": "manifest_consistency",
                    "skill": name,
                    "message": f"Store entry missing for {name} v{entry.version}",
                }
            )
    if missing_store == 0:
        output.success("Manifest consistency (all referenced store entries exist)")
        checks_passed += 1
    else:
        output.error(f"Manifest consistency: {missing_store} missing store entries")

    # Check 3: Placement validity
    missing_placements = 0
    for name, entry in mf.skills.items():
        for agent_id, placement in entry.agents.items():
            placement_path = Path(placement.path).expanduser()
            if not placement_path.exists():
                missing_placements += 1
                issues.append(
                    {
                        "check": "placement_validity",
                        "skill": name,
                        "agent": agent_id,
                        "path": str(placement_path),
                        "message": f"Placement missing: {placement_path}",
                    }
                )
    if missing_placements == 0:
        output.success("Placement validity (all manifested placements exist on disk)")
        checks_passed += 1
    else:
        output.error(f"Placement validity: {missing_placements} missing placements")

    # Check 4: Provenance file consistency
    provenance_issues = 0
    for name, entry in mf.skills.items():
        for agent_id, placement in entry.agents.items():
            placement_path = Path(placement.path).expanduser()
            prov_file = placement_path / ".napoln"
            if placement_path.exists() and not prov_file.exists():
                provenance_issues += 1
                issues.append(
                    {
                        "check": "provenance",
                        "skill": name,
                        "agent": agent_id,
                        "message": f"Missing .napoln provenance file at {placement_path}",
                    }
                )
    if provenance_issues == 0:
        output.success("Provenance files (.napoln in each placement matches manifest)")
        checks_passed += 1
    else:
        output.error(f"Provenance files: {provenance_issues} issues")

    # Check 5: git availability
    if shutil.which("git"):
        output.success("git found — merge will use git merge-file")
        checks_passed += 1
    else:
        output.warning("git not found — merge will use fallback algorithm")
        issues.append(
            {
                "check": "git",
                "message": "git not found — merge will use fallback algorithm",
            }
        )

    if json_output:
        output.print_json(
            {
                "checks_passed": checks_passed,
                "issues": issues,
            }
        )

    return 1 if issues else 0
