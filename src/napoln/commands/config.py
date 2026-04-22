"""napoln config — View/edit configuration, doctor, and gc."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import tomli_w

from napoln import output
from napoln.core import agents as agents_mod
from napoln.core import manifest, store
from napoln.core.home import get_napoln_home


# ─── config (bare) ───────────────────────────────────────────────────────────


def run_config_show() -> int:
    """Show current configuration: home, store, agents, manifests."""
    import os

    napoln_home = get_napoln_home()
    home = Path(os.environ.get("HOME", Path.home()))

    output.header("napoln config")

    # Home
    output.info(f"Home:      {napoln_home}")

    # Store
    store_dir = napoln_home / "store"
    if store_dir.exists():
        entries = sum(1 for d in store_dir.rglob("*") if d.is_dir() and "-" in d.name)
        output.info(f"Store:     {store_dir} ({entries} entries)")
    else:
        output.info(f"Store:     {store_dir} (empty)")

    # Detected agents
    detected = agents_mod.detect_agents(home)
    if detected:
        names = ", ".join(a.display_name for a in detected)
        output.info(f"Agents:    {names}")
    else:
        output.info("Agents:    (none detected)")

    # Global manifest
    global_path = manifest.get_manifest_path(napoln_home)
    if global_path.exists():
        mf = manifest.read_manifest(global_path)
        output.info(f"Global:    {global_path} ({len(mf.skills)} skills)")
    else:
        output.info(f"Global:    {global_path} (not created)")

    # Project manifest
    project_path = Path.cwd() / ".napoln" / "manifest.toml"
    if project_path.exists():
        pmf = manifest.read_manifest(project_path)
        output.info(f"Project:   {project_path} ({len(pmf.skills)} skills)")
    else:
        output.info("Project:   (none)")

    return 0


# ─── config set ───────────────────────────────────────────────────────────────


def run_config_set(key: str, value: str) -> int:
    """Set a configuration value.

    Keys use dot notation: e.g., "napoln.default_scope"
    """
    napoln_home = get_napoln_home()
    config_path = napoln_home / "config.toml"

    if config_path.exists():
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    else:
        data = {}

    parts = key.split(".")
    if len(parts) != 2:
        output.error(
            f"Invalid key: {key}",
            fix="Use dot notation, e.g.: napoln config set napoln.default_scope project",
        )
        return 1

    section, field = parts
    if section not in data:
        data[section] = {}

    # Parse value
    parsed_value: str | bool | int | list
    if value.lower() in ("true", "yes"):
        parsed_value = True
    elif value.lower() in ("false", "no"):
        parsed_value = False
    elif value.isdigit():
        parsed_value = int(value)
    elif "," in value:
        parsed_value = [v.strip() for v in value.split(",")]
    else:
        parsed_value = value

    data[section][field] = parsed_value

    napoln_home.mkdir(parents=True, exist_ok=True)
    config_path.write_text(tomli_w.dumps(data), encoding="utf-8")
    output.success(f"Set {key} = {parsed_value}")

    return 0


# ─── config doctor ────────────────────────────────────────────────────────────


def run_config_doctor(
    scope: str = "global",
    project_root: Path | None = None,
    json_output: bool = False,
) -> int:
    """Health check: store integrity, placements, provenance, git."""
    napoln_home = get_napoln_home()
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

    # Check 4: Provenance files
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
        output.success("Provenance files (.napoln in each placement)")
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


# ─── config gc ────────────────────────────────────────────────────────────────


def run_config_gc(dry_run: bool = False) -> int:
    """Remove unreferenced store entries."""
    napoln_home = get_napoln_home()

    # Collect all referenced store entries from both manifests
    referenced: set[str] = set()

    global_manifest_path = manifest.get_manifest_path(napoln_home)
    global_mf = manifest.read_manifest(global_manifest_path)
    for name, entry in global_mf.skills.items():
        referenced.add(f"{name}/{entry.version}-{entry.store_hash}")

    # Also check project manifest if present
    project_path = Path.cwd() / ".napoln" / "manifest.toml"
    if project_path.exists():
        project_mf = manifest.read_manifest(project_path)
        for name, entry in project_mf.skills.items():
            referenced.add(f"{name}/{entry.version}-{entry.store_hash}")

    store_dir = napoln_home / "store"
    if not store_dir.exists():
        output.info("Store is empty.")
        return 0

    if dry_run:
        output.dry_run_header()

    removed = 0
    for skill_dir in sorted(store_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        for version_dir in sorted(skill_dir.iterdir()):
            if not version_dir.is_dir() or version_dir.name.startswith("."):
                continue

            key = f"{skill_dir.name}/{version_dir.name}"
            if key not in referenced:
                if dry_run:
                    output.would(f"remove store entry: {key}")
                else:
                    shutil.rmtree(version_dir)
                    output.success(f"Removed: {key}")
                removed += 1

        # Clean up empty skill directories
        if not dry_run and skill_dir.exists() and not list(skill_dir.iterdir()):
            skill_dir.rmdir()

    if removed == 0:
        output.info("No unreferenced store entries.")
    elif not dry_run:
        output.success(f"Removed {removed} unreferenced store entries.")

    if dry_run:
        output.dry_run_footer()

    return 0
