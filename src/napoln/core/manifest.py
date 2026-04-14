"""Manifest TOML read/write.

The manifest tracks installed skills, versions, and placements.
Located at ~/.napoln/manifest.toml (global) or .napoln/manifest.toml (project).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import tomli_w

from napoln.errors import ManifestError


SCHEMA_VERSION = 1


@dataclass
class AgentPlacement:
    """A skill placement for a specific agent."""

    path: str
    link_mode: str  # "clone" or "copy"
    scope: str  # "global" or "project"


@dataclass
class SkillEntry:
    """A skill entry in the manifest."""

    source: str
    version: str
    store_hash: str
    installed: str  # ISO-8601
    updated: str  # ISO-8601
    agents: dict[str, AgentPlacement] = field(default_factory=dict)


@dataclass
class Manifest:
    """The complete manifest structure."""

    schema: int = SCHEMA_VERSION
    skills: dict[str, SkillEntry] = field(default_factory=dict)


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_manifest(path: Path) -> Manifest:
    """Read a manifest file.

    Args:
        path: Path to the manifest TOML file.

    Returns:
        Manifest object.

    Raises:
        ManifestError: If the file cannot be read or parsed.
    """
    if not path.exists():
        return Manifest()

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ManifestError(
            f"Could not read manifest: {path}",
            cause=str(e),
            fix="Check the file for syntax errors or run `napoln doctor`.",
        )

    manifest = Manifest()
    manifest.schema = data.get("napoln", {}).get("schema", SCHEMA_VERSION)

    for name, skill_data in data.get("skills", {}).items():
        agents = {}
        for agent_id, agent_data in skill_data.get("agents", {}).items():
            agents[agent_id] = AgentPlacement(
                path=agent_data.get("path", ""),
                link_mode=agent_data.get("link_mode", "copy"),
                scope=agent_data.get("scope", "global"),
            )

        manifest.skills[name] = SkillEntry(
            source=skill_data.get("source", ""),
            version=skill_data.get("version", ""),
            store_hash=skill_data.get("store_hash", ""),
            installed=skill_data.get("installed", ""),
            updated=skill_data.get("updated", ""),
            agents=agents,
        )

    return manifest


def write_manifest(manifest: Manifest, path: Path) -> None:
    """Write a manifest to a TOML file.

    Args:
        manifest: Manifest object to write.
        path: Path to write the manifest to.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "napoln": {"schema": manifest.schema},
        "skills": {},
    }

    for name, entry in sorted(manifest.skills.items()):
        skill_data: dict = {
            "source": entry.source,
            "version": entry.version,
            "store_hash": entry.store_hash,
            "installed": entry.installed,
            "updated": entry.updated,
        }

        if entry.agents:
            agents_data: dict = {}
            for agent_id, placement in sorted(entry.agents.items()):
                agents_data[agent_id] = {
                    "path": placement.path,
                    "link_mode": placement.link_mode,
                    "scope": placement.scope,
                }
            skill_data["agents"] = agents_data

        data["skills"][name] = skill_data

    path.write_text(tomli_w.dumps(data), encoding="utf-8")


def add_skill_to_manifest(
    manifest: Manifest,
    skill_name: str,
    source: str,
    version: str,
    store_hash: str,
    agents: dict[str, AgentPlacement],
) -> Manifest:
    """Add or update a skill in the manifest.

    Args:
        manifest: The current manifest.
        skill_name: Name of the skill.
        source: Source identifier (git URL, local path).
        version: Version string.
        store_hash: Content hash prefix.
        agents: Dict of agent_id -> AgentPlacement.

    Returns:
        Updated manifest.
    """
    now = _now_iso()

    if skill_name in manifest.skills:
        entry = manifest.skills[skill_name]
        entry.source = source
        entry.version = version
        entry.store_hash = store_hash
        entry.updated = now
        entry.agents.update(agents)
    else:
        manifest.skills[skill_name] = SkillEntry(
            source=source,
            version=version,
            store_hash=store_hash,
            installed=now,
            updated=now,
            agents=agents,
        )

    return manifest


def remove_skill_from_manifest(
    manifest: Manifest, skill_name: str, agent_ids: list[str] | None = None
) -> Manifest:
    """Remove a skill (or specific agent placements) from the manifest.

    Args:
        manifest: The current manifest.
        skill_name: Name of the skill to remove.
        agent_ids: If specified, only remove these agent placements.
                   If None, remove the entire skill entry.

    Returns:
        Updated manifest.
    """
    if skill_name not in manifest.skills:
        return manifest

    if agent_ids:
        entry = manifest.skills[skill_name]
        for aid in agent_ids:
            entry.agents.pop(aid, None)
        # If no agents left, remove the skill entirely
        if not entry.agents:
            del manifest.skills[skill_name]
    else:
        del manifest.skills[skill_name]

    return manifest


def get_manifest_path(napoln_home: Path, scope: str = "global",
                      project_root: Path | None = None) -> Path:
    """Get the manifest file path for a given scope.

    Args:
        napoln_home: Path to ~/.napoln/.
        scope: "global" or "project".
        project_root: Project root directory (required for project scope).

    Returns:
        Path to the manifest.toml file.
    """
    if scope == "project" and project_root:
        return project_root / ".napoln" / "manifest.toml"
    return napoln_home / "manifest.toml"
