"""Agent detection and path configuration.

Supports: Claude Code, Gemini CLI, pi, Codex, Cursor.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for a supported agent."""

    id: str
    display_name: str
    global_skill_dir: str  # Relative to home, e.g. ".claude/skills"
    project_skill_dir: str  # Relative to project root, e.g. ".claude/skills"

    def global_path(self, home: Path) -> Path:
        return home / self.global_skill_dir

    def project_path(self, project_root: Path) -> Path:
        return project_root / self.project_skill_dir

    def skill_path(
        self, home: Path, skill_name: str, scope: str = "global", project_root: Path | None = None
    ) -> Path:
        if scope == "project" and project_root:
            return self.project_path(project_root) / skill_name
        return self.global_path(home) / skill_name


# Agent configurations — hardcoded per spec
AGENTS: dict[str, AgentConfig] = {
    "claude-code": AgentConfig(
        id="claude-code",
        display_name="Claude Code",
        global_skill_dir=".claude/skills",
        project_skill_dir=".claude/skills",
    ),
    "gemini-cli": AgentConfig(
        id="gemini-cli",
        display_name="Gemini CLI",
        global_skill_dir=".agents/skills",
        project_skill_dir=".agents/skills",
    ),
    "pi": AgentConfig(
        id="pi",
        display_name="pi",
        global_skill_dir=".agents/skills",
        project_skill_dir=".agents/skills",
    ),
    "codex": AgentConfig(
        id="codex",
        display_name="Codex",
        global_skill_dir=".agents/skills",
        project_skill_dir=".agents/skills",
    ),
    "cursor": AgentConfig(
        id="cursor",
        display_name="Cursor",
        global_skill_dir=".cursor/skills",
        project_skill_dir=".agents/skills",
    ),
}


def _check_dir_exists(path: Path) -> bool:
    """Check if a directory exists."""
    return path.is_dir()


def _check_on_path(command: str) -> bool:
    """Check if a command is on PATH."""
    return shutil.which(command) is not None


def detect_agents(
    home: Path, project_root: Path | None = None, scope: str = "global"
) -> list[AgentConfig]:
    """Auto-detect installed agents.

    For global scope, checks:
        - Claude Code: ~/.claude/ exists
        - Gemini CLI: ~/.gemini/ exists
        - pi: ~/.pi/ exists OR `pi` on PATH
        - Codex: `codex` on PATH
        - Cursor: ~/.cursor/ exists

    For project scope, checks for agent directories in project root.

    Args:
        home: User home directory.
        project_root: Project root (for project-scope detection).
        scope: "global" or "project".

    Returns:
        List of detected AgentConfig objects.
    """
    detected: list[AgentConfig] = []

    if scope == "global":
        if _check_dir_exists(home / ".claude"):
            detected.append(AGENTS["claude-code"])

        if _check_dir_exists(home / ".gemini"):
            detected.append(AGENTS["gemini-cli"])

        if _check_dir_exists(home / ".pi") or _check_on_path("pi"):
            detected.append(AGENTS["pi"])

        if _check_on_path("codex"):
            detected.append(AGENTS["codex"])

        if _check_dir_exists(home / ".cursor"):
            detected.append(AGENTS["cursor"])
    elif scope == "project" and project_root:
        if _check_dir_exists(project_root / ".claude"):
            detected.append(AGENTS["claude-code"])

        if _check_dir_exists(project_root / ".gemini"):
            detected.append(AGENTS["gemini-cli"])

        if _check_dir_exists(project_root / ".pi") or _check_dir_exists(project_root / ".agents"):
            detected.append(AGENTS["pi"])

        # Codex and Cursor share .agents/ at project level
        if _check_dir_exists(project_root / ".agents"):
            if AGENTS["codex"] not in detected:
                detected.append(AGENTS["codex"])
            if AGENTS["cursor"] not in detected:
                detected.append(AGENTS["cursor"])

    return detected


def resolve_agents(
    agent_ids: list[str] | None, home: Path, project_root: Path | None = None, scope: str = "global"
) -> list[AgentConfig]:
    """Resolve agent list from explicit IDs or auto-detection.

    Args:
        agent_ids: Explicit agent IDs, or None for auto-detect.
        home: User home directory.
        project_root: Project root (for project-scope).
        scope: "global" or "project".

    Returns:
        List of AgentConfig objects.

    Raises:
        ValueError: If an unknown agent ID is specified.
    """
    if agent_ids:
        configs = []
        for aid in agent_ids:
            if aid not in AGENTS:
                raise ValueError(f"Unknown agent: {aid}. Available: {', '.join(AGENTS.keys())}")
            configs.append(AGENTS[aid])
        return configs

    return detect_agents(home, project_root, scope)


def deduplicate_placements(
    agents: list[AgentConfig],
    skill_name: str,
    home: Path,
    scope: str = "global",
    project_root: Path | None = None,
) -> dict[Path, list[AgentConfig]]:
    """Group agents by their target path to avoid duplicate placements.

    Multiple agents may share the same skill directory (e.g., gemini-cli, pi, codex
    all use ~/.agents/skills/ at the global level). This returns a mapping from
    target path to the agents served by that path.

    Returns:
        Dict mapping target skill path to list of agents sharing that path.
    """
    path_to_agents: dict[Path, list[AgentConfig]] = {}
    for agent in agents:
        path = agent.skill_path(home, skill_name, scope, project_root)
        if path not in path_to_agents:
            path_to_agents[path] = []
        path_to_agents[path].append(agent)
    return path_to_agents
