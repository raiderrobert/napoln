"""napoln add — Install a skill from a git source or local path."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from napoln import output
from napoln.core import agents as agents_mod
from napoln.core import linker, manifest, store, validator
from napoln.core.resolver import (
    ResolvedSource,
    parse_source,
    resolve_git,
    resolve_local,
)
from napoln.errors import AgentNotFoundError, NapolnError, ResolverError


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _ensure_initialized(napoln_home: Path) -> None:
    """Ensure napoln home directory structure exists."""
    napoln_home.mkdir(parents=True, exist_ok=True)
    (napoln_home / "store").mkdir(exist_ok=True)
    (napoln_home / "cache").mkdir(exist_ok=True)

    config_path = napoln_home / "config.toml"
    if not config_path.exists():
        import tomli_w
        config = {
            "napoln": {
                "default_agents": [],
                "default_scope": "global",
            },
            "telemetry": {
                "enabled": False,
                "anonymous_id": "",
            },
        }
        config_path.write_text(tomli_w.dumps(config))


def _write_provenance(
    target_dir: Path, source: str, version: str,
    store_hash: str, link_mode: str,
) -> None:
    """Write the .napoln provenance file to a placement."""
    from datetime import datetime, timezone
    from napoln import __version__

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    provenance = (
        f'source = "{source}"\n'
        f'version = "{version}"\n'
        f'store_hash = "{store_hash}"\n'
        f'link_mode = "{link_mode}"\n'
        f'installed = "{now}"\n'
        f'napoln_version = "{__version__}"\n'
    )
    (target_dir / ".napoln").write_text(provenance)


def _install_bootstrap_skill(
    napoln_home: Path,
    home: Path,
    agent_configs: list[agents_mod.AgentConfig],
    scope: str,
    project_root: Path | None,
    dry_run: bool = False,
) -> None:
    """Install the napoln-manage bootstrap skill if not already installed."""
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if "napoln-manage" in mf.skills:
        return

    # Find bundled skill
    skill_dir = Path(__file__).parent.parent / "skills" / "napoln-manage"
    if not skill_dir.exists() or not (skill_dir / "SKILL.md").exists():
        return

    if dry_run:
        output.would("install bootstrap skill 'napoln-manage'")
        return

    # Store it
    store_path, content_hash = store.store_skill(
        skill_dir, "napoln-manage", "0.1.0", napoln_home
    )

    # Place it
    placements_map = agents_mod.deduplicate_placements(
        agent_configs, "napoln-manage", home, scope, project_root
    )
    agent_placements: dict[str, manifest.AgentPlacement] = {}

    for target_path, path_agents in placements_map.items():
        link_mode = linker.place_skill(store_path, target_path)
        _write_provenance(
            target_path, "bundled", "0.1.0", content_hash, link_mode
        )
        for agent in path_agents:
            agent_placements[agent.id] = manifest.AgentPlacement(
                path=str(target_path),
                link_mode=link_mode,
                scope=scope,
            )

    mf = manifest.add_skill_to_manifest(
        mf, "napoln-manage", "bundled", "0.1.0", content_hash, agent_placements
    )
    manifest.write_manifest(mf, manifest_path)


def _install_single_skill(
    resolved: ResolvedSource,
    skill_name: str,
    agent_configs: list[agents_mod.AgentConfig],
    napoln_home: Path,
    home: Path,
    scope: str,
    project_root: Path | None,
    mf: manifest.Manifest,
    manifest_path: Path,
    dry_run: bool,
) -> int:
    """Install a single resolved skill. Returns exit code."""
    # Validate
    result = validator.validate_skill(resolved.skill_dir)
    exit_code = 0

    if not result.is_valid:
        for err in result.errors:
            output.error(err.message)
        if not result.name:
            output.error(f"Cannot install '{skill_name}': skill has no valid name.")
            return 1

    if result.has_warnings:
        for warn in result.warnings:
            output.warning(warn.message)
        exit_code = 2

    version = resolved.version

    # Check if already installed
    if skill_name in mf.skills:
        existing = mf.skills[skill_name]
        if existing.version == version and existing.store_hash:
            output.info(f"'{skill_name}' v{version} is already installed.")
            return 0

    if dry_run:
        output.would(f"store skill '{skill_name}' v{version}")
        placements_map = agents_mod.deduplicate_placements(
            agent_configs, skill_name, home, scope, project_root
        )
        for target_path, path_agents in placements_map.items():
            agent_names = ", ".join(a.display_name for a in path_agents)
            output.would(f"place '{skill_name}' in {target_path} ({agent_names})")
        return exit_code

    # Store
    try:
        store_path, content_hash = store.store_skill(
            resolved.skill_dir, skill_name, version, napoln_home
        )
    except Exception as e:
        output.error(f"Failed to store skill '{skill_name}': {e}")
        return 1

    # Place
    placements_map = agents_mod.deduplicate_placements(
        agent_configs, skill_name, home, scope, project_root
    )
    agent_placements: dict[str, manifest.AgentPlacement] = {}

    for target_path, path_agents in placements_map.items():
        try:
            link_mode = linker.place_skill(store_path, target_path)
            _write_provenance(
                target_path, resolved.source_id, version, content_hash, link_mode
            )
            output.success(
                f"Placed '{skill_name}' in {target_path} ({link_mode})"
            )
            for agent in path_agents:
                agent_placements[agent.id] = manifest.AgentPlacement(
                    path=str(target_path),
                    link_mode=link_mode,
                    scope=scope,
                )
        except Exception as e:
            output.error(f"Failed to place '{skill_name}' for {path_agents[0].display_name}: {e}")
            return 1

    # Update manifest
    manifest.add_skill_to_manifest(
        mf, skill_name, resolved.source_id, version, content_hash, agent_placements
    )
    manifest.write_manifest(mf, manifest_path)
    output.success(f"Added '{skill_name}' v{version}")

    return exit_code


def run_add(
    source: str,
    agent_ids: list[str] | None = None,
    version_constraint: str | None = None,
    scope: str = "global",
    project_root: Path | None = None,
    skill_name_override: str | None = None,
    skill_filter: str | None = None,
    dry_run: bool = False,
) -> int:
    """Execute the add command.

    Args:
        skill_filter: '--skill' value. '*' = all, 'name' = specific, None = single/error.

    Returns:
        Exit code (0=success, 1=error, 2=warnings).
    """
    import os

    napoln_home = _get_napoln_home()
    home = Path(os.environ.get("HOME", Path.home()))

    _ensure_initialized(napoln_home)

    # Parse source
    try:
        parsed = parse_source(source)
    except ResolverError as e:
        output.error(str(e), cause=e.cause, fix=e.fix)
        return 1

    # Registry not yet available
    if parsed.source_type == "registry":
        output.error(
            "Registry sources are not yet available.",
            fix=f"Use a git source instead:\n  napoln add github.com/owner/{source}",
        )
        return 1

    # Resolve source
    try:
        if parsed.source_type == "local":
            resolved_result = resolve_local(parsed)
        elif parsed.source_type == "git":
            if version_constraint:
                parsed.version = version_constraint
            cache_dir = napoln_home / "cache"
            resolved_result = resolve_git(parsed, cache_dir, skill_filter=skill_filter)
        else:
            output.error(f"Unknown source type: {parsed.source_type}")
            return 1
    except ResolverError as e:
        output.error(str(e), cause=e.cause, fix=e.fix)
        return 1

    # Normalize to a list
    if isinstance(resolved_result, list):
        resolved_list = resolved_result
    else:
        resolved_list = [resolved_result]

    # Detect agents
    try:
        agent_configs = agents_mod.resolve_agents(agent_ids, home, project_root, scope)
    except ValueError as e:
        output.error(str(e))
        return 1

    if not agent_configs:
        output.error(
            "No agents detected.",
            fix="Specify agents with --agents, e.g.:\n  napoln add <source> --agents claude-code,pi",
        )
        return 1

    if dry_run:
        output.dry_run_header()

    # Install bootstrap skill on first run
    _install_bootstrap_skill(
        napoln_home, home, agent_configs, scope, project_root, dry_run
    )

    # Load manifest once
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    # Install each skill
    worst_exit = 0
    installed_count = 0
    for resolved in resolved_list:
        skill_name = skill_name_override or resolved.skill_name or resolved.skill_dir.name
        code = _install_single_skill(
            resolved, skill_name, agent_configs,
            napoln_home, home, scope, project_root,
            mf, manifest_path, dry_run,
        )
        if code > worst_exit:
            worst_exit = code
        if code <= 2:
            installed_count += 1

    if dry_run:
        output.would("update manifest")
        output.dry_run_footer()

    if len(resolved_list) > 1 and not dry_run:
        output.success(f"Installed {installed_count} skill(s) from {source}")

    return worst_exit
