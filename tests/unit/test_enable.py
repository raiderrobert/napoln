"""Tests for napoln.commands.enable."""

from __future__ import annotations

from napoln.commands.enable import _get_skills_to_enable
from napoln.core import manifest as manifest_mod


class TestGetSkillsToEnable:
    """Filter skills not yet placed for an agent."""

    def test_no_skills(self):
        """Empty manifest returns empty list."""
        mf = manifest_mod.Manifest()
        result = _get_skills_to_enable(mf, "hermes")
        assert result == []

    def test_all_enabled(self):
        """Skill already placed for agent is filtered out."""
        mf = manifest_mod.Manifest()
        mf.skills["test-skill"] = manifest_mod.SkillEntry(
            source="owner/repo",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={
                "hermes": manifest_mod.AgentPlacement(
                    path="/home/.hermes/skills/test-skill",
                    link_mode="clone",
                    scope="global",
                )
            },
        )
        result = _get_skills_to_enable(mf, "hermes")
        assert result == []

    def test_some_enabled(self):
        """Skills not placed for agent are returned."""
        mf = manifest_mod.Manifest()
        mf.skills["skill-a"] = manifest_mod.SkillEntry(
            source="owner/repo",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={
                "claude-code": manifest_mod.AgentPlacement(
                    path="/home/.claude/skills/skill-a",
                    link_mode="clone",
                    scope="global",
                )
            },
        )
        mf.skills["skill-b"] = manifest_mod.SkillEntry(
            source="other/repo",
            version="2.0.0",
            store_hash="def456",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={},  # Not placed for anyone
        )
        result = _get_skills_to_enable(mf, "hermes")
        assert len(result) == 2
        names = {name for name, _ in result}
        assert "skill-a" in names
        assert "skill-b" in names

    def test_mixed_placement(self):
        """Some skills placed, some not, for the same agent."""
        mf = manifest_mod.Manifest()
        mf.skills["placed"] = manifest_mod.SkillEntry(
            source="owner/placed",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={
                "hermes": manifest_mod.AgentPlacement(
                    path="/home/.hermes/skills/placed",
                    link_mode="clone",
                    scope="global",
                )
            },
        )
        mf.skills["not-placed"] = manifest_mod.SkillEntry(
            source="owner/not-placed",
            version="1.0.0",
            store_hash="def456",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={},
        )
        result = _get_skills_to_enable(mf, "hermes")
        assert len(result) == 1
        assert result[0][0] == "not-placed"

    def test_skill_placed_for_different_agent(self):
        """Skill placed for another agent is included."""
        mf = manifest_mod.Manifest()
        mf.skills["skill-a"] = manifest_mod.SkillEntry(
            source="owner/repo",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={
                "claude-code": manifest_mod.AgentPlacement(
                    path="/home/.claude/skills/skill-a",
                    link_mode="clone",
                    scope="global",
                )
            },
        )
        result = _get_skills_to_enable(mf, "hermes")
        assert len(result) == 1
        assert result[0][0] == "skill-a"
