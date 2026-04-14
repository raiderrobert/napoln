"""Error types for napoln."""

from __future__ import annotations


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


class MergeConflictError(NapolnError):
    """Raised when a three-way merge results in conflicts."""

    def __init__(self, message: str, conflicts: list[str] | None = None):
        super().__init__(message)
        self.conflicts = conflicts or []


class AgentNotFoundError(NapolnError):
    """Raised when no agents are detected."""
