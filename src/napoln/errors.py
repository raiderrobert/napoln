"""Error types for napoln."""

from __future__ import annotations

from pathlib import Path


class NapolnError(Exception):
    """Base error for all napoln errors."""

    def __init__(self, message: str, cause: str = "", fix: str = ""):
        super().__init__(message)
        self.cause = cause
        self.fix = fix


class SkillNotFoundError(NapolnError):
    """Raised when a skill directory does not exist or has no SKILL.md."""


class ValidationError(NapolnError):
    """Raised when skill validation fails (hard error, not warning)."""


class StoreError(NapolnError):
    """Raised on store corruption or integrity failure."""


class ManifestError(NapolnError):
    """Raised on manifest read/write issues."""


class PlacementError(NapolnError):
    """Raised when skill placement fails."""


class ResolverError(NapolnError):
    """Raised when source resolution fails."""


class MultipleSkillsError(ResolverError):
    """Raised when a repo has multiple skills and no filter was given."""

    def __init__(self, repo_dir: Path, skill_dirs: list[Path]):

        names = ", ".join(d.name for d in sorted(skill_dirs))
        super().__init__(
            f"Found {len(skill_dirs)} skills: {names}",
            fix="Use --skill <name> or --all to install all.",
        )
        self.repo_dir = repo_dir
        self.skill_dirs = skill_dirs


class MergeConflictError(NapolnError):
    """Raised when a three-way merge results in conflicts."""

    def __init__(self, message: str, conflicts: list[str] | None = None):
        super().__init__(message)
        self.conflicts = conflicts or []


class AgentNotFoundError(NapolnError):
    """Raised when no agents are detected."""
