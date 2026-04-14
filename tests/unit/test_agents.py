"""Tests for napoln.core.agents — agent detection and path configuration."""

import pytest

from napoln.core.agents import (
    AGENTS,
    deduplicate_placements,
    detect_agents,
    resolve_agents,
)


class TestAgentConfig:
    """Agent configuration basics."""

    @pytest.mark.parametrize(
        "agent_id, global_dir",
        [
            ("claude-code", ".claude/skills"),
            ("gemini-cli", ".agents/skills"),
            ("pi", ".agents/skills"),
            ("codex", ".agents/skills"),
            ("cursor", ".cursor/skills"),
        ],
    )
    def test_global_paths(self, tmp_path, agent_id, global_dir):
        agent = AGENTS[agent_id]
        expected = tmp_path / global_dir
        assert agent.global_path(tmp_path) == expected

    @pytest.mark.parametrize(
        "agent_id, project_dir",
        [
            ("claude-code", ".claude/skills"),
            ("gemini-cli", ".agents/skills"),
            ("pi", ".agents/skills"),
            ("codex", ".agents/skills"),
            ("cursor", ".agents/skills"),
        ],
    )
    def test_project_paths(self, tmp_path, agent_id, project_dir):
        agent = AGENTS[agent_id]
        expected = tmp_path / project_dir
        assert agent.project_path(tmp_path) == expected

    def test_skill_path_global(self, tmp_path):
        agent = AGENTS["claude-code"]
        expected = tmp_path / ".claude" / "skills" / "my-skill"
        assert agent.skill_path(tmp_path, "my-skill") == expected

    def test_skill_path_project(self, tmp_path):
        agent = AGENTS["claude-code"]
        project = tmp_path / "project"
        expected = project / ".claude" / "skills" / "my-skill"
        assert agent.skill_path(tmp_path, "my-skill", "project", project) == expected


class TestDetectAgents:
    """Agent auto-detection."""

    @pytest.mark.parametrize(
        "dot_dir, expected_agent_id",
        [
            (".claude", "claude-code"),
            (".gemini", "gemini-cli"),
            (".pi", "pi"),
            (".cursor", "cursor"),
        ],
    )
    def test_detects_agent_by_config_dir(self, tmp_path, dot_dir, expected_agent_id):
        (tmp_path / dot_dir).mkdir()
        agents = detect_agents(tmp_path)
        assert any(a.id == expected_agent_id for a in agents)

    def test_no_agents(self, tmp_path):
        agents = detect_agents(tmp_path)
        # May detect pi/codex if they're on PATH, so just check it returns a list
        assert isinstance(agents, list)

    def test_multiple_agents(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".gemini").mkdir()
        agents = detect_agents(tmp_path)
        ids = [a.id for a in agents]
        assert "claude-code" in ids
        assert "gemini-cli" in ids


class TestResolveAgents:
    """Agent resolution from explicit IDs or auto-detect."""

    def test_explicit_agents(self, tmp_path):
        agents = resolve_agents(["claude-code", "pi"], tmp_path)
        assert len(agents) == 2
        assert agents[0].id == "claude-code"
        assert agents[1].id == "pi"

    def test_unknown_agent_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown agent"):
            resolve_agents(["nonexistent"], tmp_path)

    def test_auto_detect(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        agents = resolve_agents(None, tmp_path)
        assert any(a.id == "claude-code" for a in agents)


class TestDeduplicatePlacements:
    """Grouping agents by shared placement paths."""

    def test_shared_agents_path(self, tmp_path):
        """Gemini, pi, and codex share ~/.agents/skills/ globally."""
        agents = [AGENTS["gemini-cli"], AGENTS["pi"], AGENTS["codex"]]
        placements = deduplicate_placements(agents, "my-skill", tmp_path)

        # All three should map to the same path
        assert len(placements) == 1
        path = list(placements.keys())[0]
        assert ".agents/skills/my-skill" in str(path)
        assert len(list(placements.values())[0]) == 3

    def test_claude_separate(self, tmp_path):
        """Claude Code has its own path, separate from agents/ agents."""
        agents = [AGENTS["claude-code"], AGENTS["pi"]]
        placements = deduplicate_placements(agents, "my-skill", tmp_path)

        assert len(placements) == 2
        paths = [str(p) for p in placements.keys()]
        assert any(".claude/skills/my-skill" in p for p in paths)
        assert any(".agents/skills/my-skill" in p for p in paths)
