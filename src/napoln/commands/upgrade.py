"""napoln upgrade — Upgrade one or all skills."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import linker, manifest, merger, store
from napoln.core.resolver import parse_source, resolve_git, resolve_local
from napoln.errors import ResolverError


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_upgrade(
    name: str | None = None,
    version_constraint: str | None = None,
    agent_ids: list[str] | None = None,
    dry_run: bool = False,
    force: bool = False,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the upgrade command.

    Returns:
        Exit code (0=success, 1=error, 2=conflicts).
    """
    import os

    napoln_home = _get_napoln_home()
    home = Path(os.environ.get("HOME", Path.home()))
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if not mf.skills:
        output.info("No skills installed.")
        return 0

    skills_to_upgrade = [name] if name else list(mf.skills.keys())
    exit_code = 0

    if dry_run:
        output.dry_run_header()

    for skill_name in skills_to_upgrade:
        if skill_name not in mf.skills:
            output.error(f"Skill '{skill_name}' is not installed.")
            exit_code = 1
            continue

        entry = mf.skills[skill_name]
        code = _upgrade_skill(
            skill_name,
            entry,
            napoln_home,
            home,
            mf,
            manifest_path,
            version_constraint,
            agent_ids,
            dry_run,
            force,
            scope,
            project_root,
        )
        if code > exit_code:
            exit_code = code

    if dry_run:
        output.dry_run_footer()

    return exit_code


def _upgrade_skill(
    skill_name: str,
    entry: manifest.SkillEntry,
    napoln_home: Path,
    home: Path,
    mf: manifest.Manifest,
    manifest_path: Path,
    version_constraint: str | None,
    agent_ids: list[str] | None,
    dry_run: bool,
    force: bool,
    scope: str,
    project_root: Path | None,
) -> int:
    """Upgrade a single skill. Returns exit code."""
    # Resolve new version from source
    try:
        parsed = parse_source(entry.source)
        if version_constraint:
            parsed.version = version_constraint

        if parsed.source_type == "local":
            resolved = resolve_local(parsed)
        elif parsed.source_type == "git":
            cache_dir = napoln_home / "cache"
            result = resolve_git(parsed, cache_dir)
            # resolve_git can return a list for multi-skill repos;
            # during upgrade the manifest source already has a path,
            # so we always expect a single result.
            if isinstance(result, list):
                match = [r for r in result if r.skill_name == skill_name]
                if not match:
                    output.error(f"Skill '{skill_name}' not found in resolved sources.")
                    return 1
                resolved = match[0]
            else:
                resolved = result
        else:
            output.info(f"Cannot upgrade '{skill_name}': unsupported source type.")
            return 0
    except ResolverError as e:
        output.error(f"Failed to resolve update for '{skill_name}': {e}")
        return 1

    # Check if there's actually a new version
    from napoln.core.hasher import hash_skill

    new_hash = hash_skill(resolved.skill_dir)
    if new_hash == entry.store_hash and not force:
        output.info(f"'{skill_name}' is already up to date (v{entry.version}).")
        return 0

    new_version = resolved.version

    if dry_run:
        output.would(f"upgrade '{skill_name}' from v{entry.version} to v{new_version}")

    # Store new version
    if not dry_run:
        new_store_path, new_content_hash = store.store_skill(
            resolved.skill_dir, skill_name, new_version, napoln_home
        )
    else:
        new_content_hash = new_hash
        output.would(f"store '{skill_name}' v{new_version}")

    # Get old store base
    old_store = store.get_stored_skill(skill_name, entry.version, entry.store_hash, napoln_home)

    # Merge/replace placements
    agents_to_upgrade = agent_ids if agent_ids else list(entry.agents.keys())
    has_conflicts = False

    for agent_id in agents_to_upgrade:
        if agent_id not in entry.agents:
            continue

        placement = entry.agents[agent_id]
        placement_path = Path(placement.path).expanduser()
        placement_conflicted = False

        if dry_run:
            if force or not old_store or not placement_path.exists():
                output.would(f"replace placement at {placement_path}")
            else:
                output.would(f"merge changes into {placement_path}")
            continue

        if force or not old_store or not placement_path.exists():
            # Force or no base for merge — full replace
            linker.place_skill(new_store_path, placement_path)
            output.success(f"Replaced '{skill_name}' at {placement_path}")
        else:
            # Three-way merge
            updated, conflicted = merger.merge_skill(placement_path, old_store, new_store_path)
            if conflicted:
                has_conflicts = True
                placement_conflicted = True
                output.warning(
                    f"Conflicts in '{skill_name}' at {placement_path}: " + ", ".join(conflicted)
                )
            elif updated:
                output.success(
                    f"Merged '{skill_name}' at {placement_path} ({len(updated)} files updated)"
                )
            else:
                output.info(f"No changes needed for '{skill_name}' at {placement_path}")

        # Only update provenance for clean placements
        if not placement_conflicted:
            from napoln.commands.add import _write_provenance

            _write_provenance(
                placement_path,
                entry.source,
                new_version,
                new_content_hash,
                placement.link_mode,
            )

    if not dry_run:
        if has_conflicts:
            # Keep old version in manifest so re-running upgrade works.
            # The new version is in the store for the next merge attempt.
            output.warning(
                f"'{skill_name}' upgraded with conflicts. "
                f"Resolve them, then run `napoln upgrade {skill_name}` again."
            )
        else:
            entry.version = new_version
            entry.store_hash = new_content_hash
            from napoln.core.manifest import _now_iso

            entry.updated = _now_iso()
            manifest.write_manifest(mf, manifest_path)
            output.success(f"Upgraded '{skill_name}' to v{new_version}")

    return 2 if has_conflicts else 0
