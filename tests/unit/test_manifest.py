"""Tests for napoln.core.manifest — manifest TOML read/write."""

import pytest

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

    def test_atomic_write_preserves_prior_contents_on_failure(self, tmp_path, monkeypatch):
        """If the write is interrupted mid-stream, the original manifest must survive."""
        from pathlib import Path as _Path

        path = tmp_path / "manifest.toml"

        # Seed a known-good manifest.
        original = Manifest()
        original.skills["alpha"] = SkillEntry(
            source="local/alpha",
            version="1.0.0",
            store_hash="abc1234",
            installed="2026-04-14T10:00:00Z",
            updated="2026-04-14T10:00:00Z",
        )
        write_manifest(original, path)
        original_bytes = path.read_bytes()

        # Simulate an interruption: the bytes have started to land on disk,
        # but the write does not complete. A non-atomic writer clobbers the
        # target; an atomic writer must leave the target untouched.
        real_write_text = _Path.write_text

        def failing_write_text(self, data, *args, **kwargs):
            # Write a truncated prefix, then raise to mimic a killed process.
            real_write_text(self, data[: len(data) // 2], *args, **kwargs)
            raise RuntimeError("simulated interruption")

        monkeypatch.setattr(_Path, "write_text", failing_write_text)

        replacement = Manifest()
        replacement.skills["beta"] = SkillEntry(
            source="local/beta",
            version="2.0.0",
            store_hash="def5678",
            installed="2026-04-14T11:00:00Z",
            updated="2026-04-14T11:00:00Z",
        )
        with pytest.raises(RuntimeError, match="simulated interruption"):
            write_manifest(replacement, path)

        # Target must still contain the original contents and no stray temp file.
        assert path.read_bytes() == original_bytes
        leftovers = sorted(p.name for p in tmp_path.iterdir() if p.name != "manifest.toml")
        assert leftovers == [], f"unexpected files: {leftovers}"


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

    def test_round_trips_namespaced_skill_name(self, tmp_path):
        """Skill names containing '.' and ':' must survive a write/read round-trip.

        TOML treats '.' as a key separator unless quoted; this test guards against
        a regression where tomli_w (or a future replacement) stops quoting.
        """
        namespaced = "obra.superpowers:writing-skills"
        mf = Manifest()
        mf = add_skill_to_manifest(
            mf,
            namespaced,
            "github.com/obra/superpowers",
            "1.0.0",
            "abc123",
            {},
        )

        path = tmp_path / "manifest.toml"
        write_manifest(mf, path)

        reloaded = read_manifest(path)
        assert namespaced in reloaded.skills
        assert reloaded.skills[namespaced].source == "github.com/obra/superpowers"
        assert reloaded.skills[namespaced].version == "1.0.0"

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
