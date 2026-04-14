"""napoln gc — Remove unreferenced store entries."""

from __future__ import annotations

import shutil
from pathlib import Path

from napoln import output
from napoln.core import manifest, store


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_gc(
    dry_run: bool = False,
    clean_cache: bool = False,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the gc command.

    Returns:
        Exit code (0=success).
    """
    napoln_home = _get_napoln_home()

    # Collect all referenced store entries from manifests
    referenced: set[str] = set()

    # Global manifest
    global_manifest_path = manifest.get_manifest_path(napoln_home)
    global_mf = manifest.read_manifest(global_manifest_path)
    for name, entry in global_mf.skills.items():
        referenced.add(f"{name}/{entry.version}-{entry.store_hash}")

    # Project manifest (if in a project)
    if project_root:
        project_manifest_path = manifest.get_manifest_path(
            napoln_home, "project", project_root
        )
        project_mf = manifest.read_manifest(project_manifest_path)
        for name, entry in project_mf.skills.items():
            referenced.add(f"{name}/{entry.version}-{entry.store_hash}")

    # Scan store for unreferenced entries
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

    # Clean cache if requested
    if clean_cache:
        cache_dir = napoln_home / "cache"
        if cache_dir.exists():
            if dry_run:
                output.would("remove cache directory")
            else:
                shutil.rmtree(cache_dir)
                cache_dir.mkdir()
                output.success("Cleaned cache.")

    if removed == 0:
        output.info("No unreferenced store entries.")
    elif not dry_run:
        output.success(f"Removed {removed} unreferenced store entries.")

    if dry_run:
        output.dry_run_footer()

    return 0
