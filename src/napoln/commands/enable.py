"""napoln enable — Extend installed skills to additional agents."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from napoln import output
from napoln.core import agents as agents_mod
from napoln.core import linker, manifest, store
from napoln.core.home import get_napoln_home
from napoln.prompts import SkillChoice, pick_agents, pick_skills


def _get_skills_to_enable(
    mf: manifest.Manifest,
    agent_id: str,
) -> list[tuple[str, manifest.SkillEntry]]:
    """Return skills not yet placed for the given agent.

    Args:
        mf: The manifest to check.
        agent_id: The agent ID to filter by.

    Returns:
        List of (skill_name, SkillEntry) tuples for skills not placed for this agent.
    """
    skills = []
    for name, entry in mf.skills.items():
        if agent_id not in entry.agents:
            skills.append((name, entry))
    return skills


def _place_skill_for_agent(
    skill_name: str,
    skill_entry: manifest.SkillEntry,
    agent_config: agents_mod.AgentConfig,
    napoln_home: Path,
    home: Path,
    scope: str,
    project_root: Path | None,
) -> str | None:
    """Place a single skill for an agent.

    Args:
        skill_name: Name of the skill.
        skill_entry: Skill entry from manifest.
        agent_config: Agent configuration.
        napoln_home: napoln home path.
        home: User home path.
        scope: "global" or "project".
        project_root: Project root for project scope.

    Returns:
        Link mode on success, None on failure.
    """
    # Get store path - will re-fetch if needed
    try:
        store_path = store.ensure_stored(
            skill_name,
            skill_entry.version,
            skill_entry.store_hash,
            skill_entry.source,
            napoln_home,
        )
    except Exception as e:
        output.error(f"Failed to retrieve '{skill_name}' from store: {e}")
        return None

    # Get target path
    target_path = agent_config.skill_path(home, skill_name, scope, project_root)

    # Place
    try:
        link_mode = linker.place_skill(store_path, target_path)
        linker.write_provenance(
            target_path,
            skill_entry.source,
            skill_entry.version,
            skill_entry.store_hash,
            link_mode,
        )
        return link_mode
    except Exception as e:
        output.error(f"Failed to place '{skill_name}': {e}")
        return None


def run_enable(
    agent_ids: list[str] | None,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the enable command.

    Args:
        agent_ids: Specific agent IDs to enable, or None to pick interactively.
        scope: "global" or "project".
        project_root: Project root for project scope.

    Returns:
        Exit code (0=success, 1=error).
    """
    import os

    napoln_home = get_napoln_home()
    home = Path(os.environ.get("HOME", Path.home()))

    # Determine which agents to enable
    if agent_ids:
        # Validate agent IDs
        for aid in agent_ids:
            if aid not in agents_mod.AGENTS:
                output.error(
                    f"Unknown agent: {aid}. Available: {', '.join(agents_mod.AGENTS.keys())}"
                )
                return 1
        target_agents = [agents_mod.AGENTS[aid] for aid in agent_ids]
    else:
        # Interactive agent picker
        available = agents_mod.detect_agents(home, project_root, scope)
        if not available:
            output.error("No agents detected. Install an agent first.")
            return 1

        selected = pick_agents(available)
        if selected is None:
            return 1  # User cancelled
        if not selected:
            output.info("No agents selected.")
            return 0
        target_agents = cast(list[agents_mod.AgentConfig], selected)

    # Load manifest
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if not mf.skills:
        output.info("No skills installed.")
        return 0

    # Process each agent
    for agent in target_agents:
        skills_to_enable = _get_skills_to_enable(mf, agent.id)

        if not skills_to_enable:
            output.success(f"All skills already enabled for {agent.display_name}")
            continue

        skill_count = len(skills_to_enable)
        output.info(
            f"Found {skill_count} skill(s). Select skills to enable for {agent.display_name}:"
        )

        # Build picker choices
        choices = [
            SkillChoice(
                name=name,
                description=f"{entry.source} (v{entry.version})",
                path=Path(entry.source),
            )
            for name, entry in skills_to_enable
        ]

        selected = pick_skills(choices)
        if not selected:
            output.info(f"No skills selected for {agent.display_name}")
            continue

        # Place selected skills
        enabled_count = 0
        for choice in selected:
            skill_entry = mf.skills[choice.name]
            link_mode = _place_skill_for_agent(
                choice.name,
                skill_entry,
                agent,
                napoln_home,
                home,
                scope,
                project_root,
            )
            if link_mode:
                output.success(f"Enabled '{choice.name}' for {agent.display_name}")
                # Update manifest
                skill_entry.agents[agent.id] = manifest.AgentPlacement(
                    path=str(agent.skill_path(home, choice.name, scope, project_root)),
                    link_mode=link_mode,
                    scope=scope,
                )
                enabled_count += 1

        # Write manifest after processing this agent
        manifest.write_manifest(mf, manifest_path)

        if enabled_count > 0:
            output.success(f"Enabled {enabled_count} skill(s) for {agent.display_name}")

    return 0
