"""Skill name namespacing for collision avoidance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from napoln.core.manifest import Manifest, SkillEntry
from napoln.core.resolver import ResolvedSource, SourceType


@dataclass(frozen=True)
class InstallIdResolution:
    """Outcome of resolving a `(manifest, resolved_source, upstream_name)` triple
    to the install id used as the manifest's primary key and placement directory.

    `existing` is set when this exact source already has an entry in the manifest
    (under any id). The caller can short-circuit re-installs by checking
    `existing.version` and `existing.store_hash`.

    `collision_with` is set when the upstream name is already taken in the
    manifest by a *different* source — the install id was namespaced and the
    field carries the conflicting source for messaging.
    """

    install_id: str
    existing: SkillEntry | None
    collision_with: str | None


def resolve_install_id(
    manifest: Manifest, resolved: ResolvedSource, upstream_name: str
) -> InstallIdResolution:
    """Decide what install id to use when installing `resolved` as `upstream_name`.

    Three cases:
      1. This exact source is already recorded under some id → reuse that id,
         return its `existing` entry so the caller can detect a no-op re-install.
      2. The upstream name is taken by a different source → namespace the install
         id and report the conflicting source via `collision_with`.
      3. Neither → install id equals `upstream_name`.
    """
    for install_id, entry in manifest.skills.items():
        if entry.source == resolved.source_id and entry.name == upstream_name:
            return InstallIdResolution(install_id, entry, None)

    conflict = manifest.skills.get(upstream_name)
    if conflict is not None and conflict.source != resolved.source_id:
        return InstallIdResolution(namespace_for(resolved, upstream_name), None, conflict.source)

    return InstallIdResolution(upstream_name, None, None)


def namespace_for(resolved: ResolvedSource, skill_name: str) -> str:
    """Compute a deterministic namespaced skill name.

    Used when a skill name already exists in the target manifest under a
    different source. The namespace is derived from the source identity, not
    the skill name, so the same source always produces the same namespace.

    Format:
        git    -> "<owner>.<repo>:<skill_name>"
        local  -> "<parent-dir-name>:<skill_name>"
    """
    if resolved.source_type == SourceType.GIT and resolved.parsed is not None:
        return f"{resolved.parsed.owner}.{resolved.parsed.repo}:{skill_name}"

    if resolved.source_type == SourceType.LOCAL:
        parent = Path(resolved.source_id).parent.name
        if parent:
            return f"{parent}:{skill_name}"
        # No parent segment available — use the skill dir name itself as a
        # last-resort namespace. Better than producing "<empty>:<name>".
        return f"{Path(resolved.source_id).name}:{skill_name}"

    # Defensive fallback for any future source_type. Should be unreachable today.
    safe = resolved.source_id.replace("/", ".").replace(":", "")
    return f"{safe}:{skill_name}"
