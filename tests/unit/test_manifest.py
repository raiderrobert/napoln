"""Tests for napoln.core.manifest — manifest TOML read/write."""

from napoln.core.manifest import (
    AgentPlacement,
    Manifest,
    SkillEntry,
    add_skill_to_manifest,
    read_manifest,
    remove_skill_from_manifest,
    write_manifest,
)


class TestReadWriteManifest:
    """Manifest serialization round-trips correctly."""

    def test_empty_manifest(self, tmp_path):
        """Reading a non-existent manifest returns empty Manifest."""
        mf = read_manifest(tmp_path / "manifest.toml")
        assert mf.schema == 1
        assert mf.skills == {}

    def test_round_trip(self, tmp_path):
        """Writing then reading produces identical data."""
        path = tmp_path / "manifest.toml"

        mf = Manifest()
        mf.skills["my-skill"] = SkillEntry(
            source="github.com/owner/repo",
            version="1.0.0",
            store_hash="abc1234",
            installed="2026-04-14T10:00:00Z",
            updated="2026-04-14T10:00:00Z",
            agents={
                "claude-code": AgentPlacement(
                    path="~/.claude/skills/my-skill",
                    link_mode="clone",
                    scope="global",
                ),
            },
        )

        write_manifest(mf, path)
        loaded = read_manifest(path)

        assert loaded.schema == 1
        assert "my-skill" in loaded.skills
        entry = loaded.skills["my-skill"]
        assert entry.source == "github.com/owner/repo"
        assert entry.version == "1.0.0"
        assert entry.store_hash == "abc1234"
        assert "claude-code" in entry.agents
        assert entry.agents["claude-code"].link_mode == "clone"

    def test_multiple_skills(self, tmp_path):
        """Multiple skills serialize correctly."""
        path = tmp_path / "manifest.toml"

        mf = Manifest()
        for name in ["alpha", "beta", "gamma"]:
            mf.skills[name] = SkillEntry(
                source=f"local/{name}",
                version="1.0.0",
                store_hash="abc1234",
                installed="2026-04-14T10:00:00Z",
                updated="2026-04-14T10:00:00Z",
            )

        write_manifest(mf, path)
        loaded = read_manifest(path)

        assert set(loaded.skills.keys()) == {"alpha", "beta", "gamma"}

    def test_creates_parent_dirs(self, tmp_path):
        """Writing creates parent directories if needed."""
        path = tmp_path / "deep" / "nested" / "manifest.toml"
        write_manifest(Manifest(), path)
        assert path.exists()


class TestAddSkillToManifest:
    """Adding skills to the manifest."""

    def test_add_new_skill(self):
        mf = Manifest()
        mf = add_skill_to_manifest(
            mf,
            "my-skill",
            "github.com/owner/repo",
            "1.0.0",
            "abc1234",
            {"claude-code": AgentPlacement("~/.claude/skills/my-skill", "clone", "global")},
        )

        assert "my-skill" in mf.skills
        assert mf.skills["my-skill"].version == "1.0.0"

    def test_update_existing_skill(self):
        mf = Manifest()
        mf = add_skill_to_manifest(mf, "my-skill", "local/path", "1.0.0", "abc1234", {})
        mf = add_skill_to_manifest(mf, "my-skill", "local/path", "2.0.0", "def5678", {})

        assert mf.skills["my-skill"].version == "2.0.0"
        assert mf.skills["my-skill"].store_hash == "def5678"


class TestRemoveSkillFromManifest:
    """Removing skills from the manifest."""

    def test_remove_entire_skill(self):
        mf = Manifest()
        mf.skills["my-skill"] = SkillEntry(
            source="local",
            version="1.0.0",
            store_hash="abc",
            installed="",
            updated="",
        )

        mf = remove_skill_from_manifest(mf, "my-skill")
        assert "my-skill" not in mf.skills

    def test_remove_specific_agents(self):
        mf = Manifest()
        mf.skills["my-skill"] = SkillEntry(
            source="local",
            version="1.0.0",
            store_hash="abc",
            installed="",
            updated="",
            agents={
                "claude-code": AgentPlacement("path1", "clone", "global"),
                "pi": AgentPlacement("path2", "clone", "global"),
            },
        )

        mf = remove_skill_from_manifest(mf, "my-skill", ["claude-code"])
        assert "my-skill" in mf.skills
        assert "claude-code" not in mf.skills["my-skill"].agents
        assert "pi" in mf.skills["my-skill"].agents

    def test_remove_all_agents_removes_skill(self):
        mf = Manifest()
        mf.skills["my-skill"] = SkillEntry(
            source="local",
            version="1.0.0",
            store_hash="abc",
            installed="",
            updated="",
            agents={"claude-code": AgentPlacement("path1", "clone", "global")},
        )

        mf = remove_skill_from_manifest(mf, "my-skill", ["claude-code"])
        assert "my-skill" not in mf.skills

    def test_remove_nonexistent_noop(self):
        mf = Manifest()
        mf = remove_skill_from_manifest(mf, "does-not-exist")
        assert mf.skills == {}
