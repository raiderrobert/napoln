"""napoln add — Install a skill from a git source or local path."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from napoln import output
from napoln.core import agents as agents_mod
from napoln.core import linker, manifest, store, validator
from napoln.core.resolver import (
    ParsedSource,
    ResolvedSource,
    _extract_description,
    _resolve_version,
    parse_source,
    resolve_git,
    resolve_local,
)
from napoln.errors import MultipleSkillsError, ResolverError
from napoln.prompts import SkillChoice, pick_skills


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
    store_path, content_hash = store.store_skill(skill_dir, "napoln-manage", "0.1.0", napoln_home)

    # Place it
    placements_map = agents_mod.deduplicate_placements(
        agent_configs, "napoln-manage", home, scope, project_root
    )
    agent_placements: dict[str, manifest.AgentPlacement] = {}

    for target_path, path_agents in placements_map.items():
        link_mode = linker.place_skill(store_path, target_path)
        linker.write_provenance(target_path, "bundled", "0.1.0", content_hash, link_mode)
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
            linker.write_provenance(
                target_path, resolved.source_id, version, content_hash, link_mode
            )
            output.success(f"Placed '{skill_name}' in {target_path} ({link_mode})")
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


def _pick_from_multi_skill_repo(
    err: MultipleSkillsError,
    parsed: ParsedSource,
    source: str,
    version_constraint: str | None,
    napoln_home: Path,
) -> list[ResolvedSource] | None:
    """Show an interactive picker for multi-skill repos.

    Returns a list of ResolvedSource, or None if the user cancels.
    """

    output.info(f"Found {len(err.skill_dirs)} skills in {source}")

    # Collect sources already recorded in any reachable manifest so we can
    # flag matching entries in the picker as installed.
    installed_sources: set[str] = set()
    for scope, root in (("global", None), ("project", Path.cwd())):
        mf_path = manifest.get_manifest_path(napoln_home, scope, root)
        if not mf_path.exists():
            continue
        try:
            mf = manifest.read_manifest(mf_path)
        except Exception:
            continue
        for entry in mf.skills.values():
            installed_sources.add(entry.source)

    source_id = f"{parsed.host}/{parsed.owner}/{parsed.repo}" if parsed.host else source

    choices = []
    for sd in sorted(err.skill_dirs, key=lambda d: d.name):
        rel = sd.relative_to(err.repo_dir)
        sid = f"{source_id}/{rel}" if str(rel) != "." else source_id
        choices.append(
            SkillChoice(
                name=sd.name,
                description=_extract_description(sd),
                path=sd,
                installed=sid in installed_sources,
            )
        )

    selected = pick_skills(choices)
    if not selected:
        output.info("No skills selected.")
        return None

    # Resolve the git ref for version
    ref = parsed.version or version_constraint or ""

    results = []
    for choice in selected:
        version = _resolve_version(choice.path, ref, err.repo_dir)
        rel = choice.path.relative_to(err.repo_dir)
        sid = f"{source_id}/{rel}" if str(rel) != "." else source_id
        results.append(
            ResolvedSource(
                source_type="git",
                source_id=sid,
                skill_dir=choice.path,
                version=version,
                cleanup=False,
                skill_name=choice.name,
            )
        )

    return results


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
    except MultipleSkillsError as e:
        # Interactive picker for multi-skill repos
        resolved_result = _pick_from_multi_skill_repo(
            e, parsed, source, version_constraint, napoln_home
        )
        if resolved_result is None:
            return 1
    except ResolverError as e:
        output.error(str(e), cause=e.cause, fix=e.fix)
        return 1

    # Normalize to a list. ty's isinstance narrowing on a `T | list[T]` union
    # leaves a quirky intersection, so cast through after the runtime check.
    if isinstance(resolved_result, list):
        resolved_list: list[ResolvedSource] = cast(list[ResolvedSource], resolved_result)
    else:
        resolved_list = [resolved_result]

    # Detect agents — prefer configured defaults over auto-detection
    default_agent_ids = agents_mod.load_default_agent_ids(napoln_home)
    try:
        agent_configs = agents_mod.resolve_agents(
            agent_ids, home, project_root, scope, default_agent_ids=default_agent_ids
        )
    except ValueError as e:
        output.error(str(e))
        return 1

    if not agent_configs:
        output.error(
            "No agents detected.",
            fix="Specify agents with --agents, e.g.:\n  napoln add <source> --agents claude-code,pi",
        )
        return 1

    # If the user has multiple agents installed but never configured defaults,
    # nudge them toward `napoln setup` so they don't keep spray-installing.
    if agent_ids is None and not default_agent_ids and scope == "global" and len(agent_configs) > 1:
        output.info(
            f"Installing to all {len(agent_configs)} detected agents. "
            "Run `napoln setup` to choose defaults."
        )

    if dry_run:
        output.dry_run_header()

    # Install bootstrap skill on first run
    _install_bootstrap_skill(napoln_home, home, agent_configs, scope, project_root, dry_run)

    # Load manifest once
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    # Show summary when installing multiple skills
    if len(resolved_list) > 1 and not dry_run:
        skill_names = [r.skill_name or r.skill_dir.name for r in resolved_list]
        agent_names = [a.display_name for a in agent_configs]
        output.install_summary(skill_names, agent_names, scope)

    # Install each skill
    worst_exit = 0
    installed_count = 0
    for resolved in resolved_list:
        skill_name = skill_name_override or resolved.skill_name or resolved.skill_dir.name
        code = _install_single_skill(
            resolved,
            skill_name,
            agent_configs,
            napoln_home,
            home,
            scope,
            project_root,
            mf,
            manifest_path,
            dry_run,
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
