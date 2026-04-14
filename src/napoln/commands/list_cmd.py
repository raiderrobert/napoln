"""napoln list — List available skills from a source without installing."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core.resolver import (
    discover_skills_in_repo,
    parse_source,
    resolve_git,
    resolve_local,
)
from napoln.core.validator import validate_skill
from napoln.errors import ResolverError


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_list(source: str) -> int:
    """Execute the list command.

    Returns:
        Exit code (0=success, 1=error).
    """
    napoln_home = _get_napoln_home()

    try:
        parsed = parse_source(source)
    except ResolverError as e:
        output.error(str(e), cause=e.cause, fix=e.fix)
        return 1

    if parsed.source_type == "registry":
        output.error(
            "Registry sources are not yet available.",
            fix=f"Use a git source or local path.",
        )
        return 1

    # Get the repo/directory
    try:
        if parsed.source_type == "local":
            base_dir = parsed.local_path
            if base_dir is None:
                output.error("No local path specified.")
                return 1
        elif parsed.source_type == "git":
            cache_dir = napoln_home / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            resolved = resolve_git(parsed, cache_dir)
            base_dir = resolved.skill_dir.parent if (resolved.skill_dir / "SKILL.md").exists() else resolved.skill_dir
        else:
            output.error(f"Unknown source type: {parsed.source_type}")
            return 1
    except ResolverError as e:
        output.error(str(e), cause=e.cause, fix=e.fix)
        return 1

    # Discover skills
    skill_dirs = discover_skills_in_repo(base_dir)

    if not skill_dirs:
        output.info(f"No skills found in {source}")
        return 0

    output.header(f"Skills in {source}:")
    for skill_dir in skill_dirs:
        result = validate_skill(skill_dir)
        name = result.name or skill_dir.name
        desc = result.description or "(no description)"
        version = ""
        if result.metadata and isinstance(result.metadata, dict):
            version = result.metadata.get("version", "")

        version_str = f" v{version}" if version else ""
        output.info(f"  {name}{version_str} — {desc}")

    return 0
