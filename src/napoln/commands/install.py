"""napoln install — Restore skill placements from manifests."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import linker, manifest, store


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _sync_manifest(
    mf: manifest.Manifest,
    label: str,
    dry_run: bool,
) -> tuple[int, int]:
    """Sync placements for a single manifest.

    Returns:
        (synced_count, error_count)
    """
    synced = 0
    errors = 0
    napoln_home = _get_napoln_home()

    for skill_name, entry in sorted(mf.skills.items()):
        store_path = store.get_stored_skill(
            skill_name, entry.version, entry.store_hash, napoln_home
        )

        if store_path is None:
            from napoln.commands.add import resolve_and_store
            from napoln.errors import NapolnError

            try:
                store_path, _ = resolve_and_store(
                    entry.source, skill_name, napoln_home, version_constraint=entry.version
                )
                output.info(f"Re-fetched '{skill_name}' from source")
            except (NapolnError, OSError):
                output.warning(
                    f"Cannot restore '{skill_name}' — source unavailable. "
                    f"Run `napoln add` to re-fetch."
                )
                errors += 1
                continue

        for agent_id, placement in entry.agents.items():
            placement_path = Path(placement.path).expanduser()

            if placement_path.exists():
                continue

            if dry_run:
                output.would(f"place '{skill_name}' at {placement_path}")
                synced += 1
            else:
                try:
                    link_mode = linker.place_skill(store_path, placement_path)

                    from napoln.commands.add import write_provenance

                    write_provenance(
                        placement_path,
                        entry.source,
                        entry.version,
                        entry.store_hash,
                        link_mode,
                    )

                    output.success(f"Restored '{skill_name}' to {placement_path}")
                    synced += 1
                except Exception as e:
                    output.error(f"Failed to restore '{skill_name}' to {placement_path}: {e}")
                    errors += 1

    return synced, errors


def run_install(
    project_only: bool = False,
    global_only: bool = False,
    dry_run: bool = False,
) -> int:
    """Execute the install command.

    Syncs both global and project manifests by default.

    Returns:
        Exit code (0=success, 1=errors).
    """
    napoln_home = _get_napoln_home()

    if dry_run:
        output.dry_run_header()

    total_synced = 0
    total_errors = 0
    total_skills = 0

    # Global manifest
    if not project_only:
        global_path = manifest.get_manifest_path(napoln_home)
        global_mf = manifest.read_manifest(global_path)
        if global_mf.skills:
            synced, errors = _sync_manifest(global_mf, "global", dry_run)
            total_synced += synced
            total_errors += errors
            total_skills += len(global_mf.skills)
            if not dry_run:
                if synced > 0:
                    output.success(
                        f"Synced {len(global_mf.skills)} global skills ({synced} restored)"
                    )
                else:
                    output.success(f"Synced {len(global_mf.skills)} global skills (all up to date)")

    # Project manifest
    if not global_only:
        project_path = Path.cwd() / ".napoln" / "manifest.toml"
        if project_path.exists():
            project_mf = manifest.read_manifest(project_path)
            if project_mf.skills:
                synced, errors = _sync_manifest(project_mf, "project", dry_run)
                total_synced += synced
                total_errors += errors
                total_skills += len(project_mf.skills)
                if not dry_run:
                    if synced > 0:
                        output.success(
                            f"Synced {len(project_mf.skills)} project skills ({synced} restored)"
                        )
                    else:
                        output.success(
                            f"Synced {len(project_mf.skills)} project skills (all up to date)"
                        )

    if total_skills == 0:
        output.info("No manifests found.")

    if dry_run:
        output.dry_run_footer()

    return 1 if total_errors > 0 else 0
