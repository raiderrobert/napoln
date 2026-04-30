"""Skill name namespacing for collision avoidance."""

from __future__ import annotations

from pathlib import Path

from napoln.core.resolver import ResolvedSource


def namespace_for(resolved: ResolvedSource, skill_name: str) -> str:
    """Compute a deterministic namespaced skill name.

    Used when a skill name already exists in the target manifest under a
    different source. The namespace is derived from the source identity, not
    the skill name, so the same source always produces the same namespace.

    Format:
        git    -> "<owner>.<repo>:<skill_name>"
        local  -> "<parent-dir-name>:<skill_name>"
    """
    if resolved.source_type == "git" and resolved.parsed is not None:
        return f"{resolved.parsed.owner}.{resolved.parsed.repo}:{skill_name}"

    if resolved.source_type == "local":
        parent = Path(resolved.source_id).parent.name
        if parent:
            return f"{parent}:{skill_name}"
        # No parent segment available — use the skill dir name itself as a
        # last-resort namespace. Better than producing "<empty>:<name>".
        return f"{Path(resolved.source_id).name}:{skill_name}"

    # Defensive fallback for any future source_type. Should be unreachable today.
    safe = resolved.source_id.replace("/", ".").replace(":", "")
    return f"{safe}:{skill_name}"
