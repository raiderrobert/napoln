"""Project detection and scope resolution."""

from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_MARKERS = frozenset({".git", ".napoln", ".claude", ".agents", ".cursor"})


def is_inside_project(cwd: Path | None = None) -> bool:
    """Return whether the current directory appears to be inside a project.

    Walks upward from *cwd* (or :func:`os.getcwd`) looking for common
    project markers: ``.git``, ``.napoln``, ``.claude``, ``.agents``,
    or ``.cursor``.
    """
    if cwd is None:
        cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        # Don't cross filesystem root
        if parent == parent.parent:
            break
        for marker in PROJECT_MARKERS:
            if (parent / marker).exists():
                return True
    return False


def load_config_default_scope(napoln_home: Path) -> str | None:
    """Read the user's configured default_scope from config.toml.

    Returns ``None`` if the config does not exist or has no default_scope set.
    """
    config_path = napoln_home / "config.toml"
    if not config_path.exists():
        return None
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    raw = data.get("napoln", {}).get("default_scope")
    if isinstance(raw, str) and raw in ("global", "project"):
        return raw
    return None


def resolve_scope(
    *,
    global_flag: bool = False,
    project_flag: bool = False,
    cwd: Path | None = None,
    config_default: str | None = None,
) -> str:
    """Resolve the effective scope for a command.

    Resolution order:
    1. Explicit flags: ``--global`` > ``--project``
    2. Config default: the user's configured default_scope
    3. Auto-detect: ``project`` if inside a project, else ``global``

    If *config_default* is set and the user is outside a project,
    falls back to ``global`` regardless of config (project scope
    requires a project).
    """
    if global_flag:
        return "global"
    if project_flag:
        return "project"
    if config_default:
        if config_default == "global":
            return "global"
        if config_default == "project" and is_inside_project(cwd):
            return "project"
    return "project" if is_inside_project(cwd) else "global"
