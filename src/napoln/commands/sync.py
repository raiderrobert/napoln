"""napoln sync / install — Re-create missing placements from manifest + store."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import linker, manifest, store


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_sync(
    dry_run: bool = False,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the sync/install command.

    Returns:
        Exit code (0=success, 1=error).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if not mf.skills:
        output.info("No skills in manifest.")
        return 0

    if dry_run:
        output.dry_run_header()

    synced = 0
    errors = 0

    for skill_name, entry in sorted(mf.skills.items()):
        store_path = store.get_stored_skill(
            skill_name, entry.version, entry.store_hash, napoln_home
        )

        if store_path is None:
            output.error(
                f"Store entry missing for '{skill_name}' v{entry.version}",
                fix="Run `napoln add` to re-fetch from the original source.",
            )
            errors += 1
            continue

        for agent_id, placement in entry.agents.items():
            placement_path = Path(placement.path).expanduser()

            if placement_path.exists():
                # Already placed
                continue

            if dry_run:
                output.would(f"place '{skill_name}' at {placement_path}")
                synced += 1
            else:
                try:
                    link_mode = linker.place_skill(store_path, placement_path)

                    # Write provenance
                    from napoln.commands.add import _write_provenance
                    _write_provenance(
                        placement_path, entry.source, entry.version,
                        entry.store_hash, link_mode,
                    )

                    output.success(f"Synced '{skill_name}' to {placement_path}")
                    synced += 1
                except Exception as e:
                    output.error(f"Failed to sync '{skill_name}' to {placement_path}: {e}")
                    errors += 1

    if dry_run:
        if synced == 0:
            output.info("Everything is in sync.")
        output.dry_run_footer()
    else:
        if synced == 0 and errors == 0:
            output.info("Everything is in sync.")
        elif synced > 0:
            output.success(f"Synced {synced} placement(s).")

    return 1 if errors > 0 else 0
