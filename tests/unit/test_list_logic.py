"""Tests for napoln.commands.list_cmd — display helper functions."""

from __future__ import annotations

import pytest

from napoln.commands.list_cmd import (
    _abbreviate_path,
    _common_agent_dirs,
    _get_agent_dirs,
    _get_placement_dirs,
)
from napoln.core import manifest as manifest_mod


def _entry_with_agents(agents: dict[str, str]) -> manifest_mod.SkillEntry:
    """Build a SkillEntry with agent placements at the given paths."""
    agent_placements = {}
    for agent_id, path in agents.items():
        agent_placements[agent_id] = manifest_mod.AgentPlacement(
            path=path, link_mode="copy", scope="global"
        )
    return manifest_mod.SkillEntry(
        source="owner/repo",
        version="1.0.0",
        store_hash="abc",
        installed="2024-01-01T00:00:00Z",
        updated="2024-01-01T00:00:00Z",
        agents=agent_placements,
    )


class TestAbbreviatePath:
    @pytest.mark.parametrize(
        "path, home, expected",
        [
            ("/home/user/.claude/skills/foo", "/home/user", "~/.claude/skills/foo"),
            ("/other/path/skills/foo", "/home/user", "/other/path/skills/foo"),
            ("/home/user", "/home/user", "~"),
        ],
        ids=["under-home", "outside-home", "exact-home"],
    )
    def test_abbreviation(self, path, home, expected):
        assert _abbreviate_path(path, home) == expected


class TestGetAgentDirs:
    def test_single_agent(self):
        entry = _entry_with_agents({"claude-code": "/home/user/.claude/skills/my-skill"})
        assert _get_agent_dirs(entry, "/home/user") == [".claude"]

    def test_shared_placement_deduplicates(self):
        entry = _entry_with_agents({
            "pi": "/home/user/.agents/skills/my-skill",
            "codex": "/home/user/.agents/skills/my-skill",
        })
        assert _get_agent_dirs(entry, "/home/user") == [".agents"]

    def test_no_agents(self):
        entry = _entry_with_agents({})
        assert _get_agent_dirs(entry, "/home/user") == []


class TestCommonAgentDirs:
    def test_all_same(self):
        mf = manifest_mod.Manifest()
        for name in ("skill-a", "skill-b"):
            mf.skills[name] = _entry_with_agents(
                {"claude-code": f"/home/user/.claude/skills/{name}"}
            )
        assert _common_agent_dirs(mf, "/home/user") == [".claude"]

    def test_mixed_returns_none(self):
        mf = manifest_mod.Manifest()
        mf.skills["a"] = _entry_with_agents({"claude-code": "/home/user/.claude/skills/a"})
        mf.skills["b"] = _entry_with_agents({"cursor": "/home/user/.cursor/skills/b"})
        assert _common_agent_dirs(mf, "/home/user") is None

    def test_empty_manifest(self):
        mf = manifest_mod.Manifest()
        assert _common_agent_dirs(mf, "/home/user") is None


class TestGetPlacementDirs:
    def test_deduplicates_shared_path(self):
        entry = _entry_with_agents({
            "pi": "/home/user/.agents/skills/my-skill",
            "codex": "/home/user/.agents/skills/my-skill",
        })
        assert _get_placement_dirs(entry, "/home/user") == ["~/.agents/skills"]

    def test_multiple_distinct_paths(self):
        entry = _entry_with_agents({
            "claude-code": "/home/user/.claude/skills/my-skill",
            "cursor": "/home/user/.cursor/skills/my-skill",
        })
        dirs = _get_placement_dirs(entry, "/home/user")
        assert "~/.claude/skills" in dirs
        assert "~/.cursor/skills" in dirs
