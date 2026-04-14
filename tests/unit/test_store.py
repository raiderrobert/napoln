"""Tests for napoln.core.store — content-addressed store operations."""

import pytest

from napoln.core.store import (
    get_stored_skill,
    list_stored_versions,
    store_skill,
    verify_store_entry,
)


class TestStoreSkill:
    """Storing skills in the content-addressed store."""

    def test_stores_skill(self, tmp_path, skill_builder):
        """A skill is stored with version-hash directory name."""
        skill_dir = skill_builder("my-skill")
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        store_path, content_hash = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)

        assert store_path.exists()
        assert store_path.name == f"1.0.0-{content_hash}"
        assert (store_path / "SKILL.md").exists()

    def test_idempotent(self, tmp_path, skill_builder):
        """Storing the same skill twice is a no-op."""
        skill_dir = skill_builder("my-skill")
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        path1, hash1 = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)
        path2, hash2 = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)

        assert path1 == path2
        assert hash1 == hash2

    def test_different_versions(self, tmp_path, skill_builder):
        """Different content produces different store entries."""
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        skill_v1 = skill_builder("my-skill", version="1.0.0", body="# V1")
        path1, hash1 = store_skill(skill_v1, "my-skill", "1.0.0", napoln_home)

        skill_v2 = skill_builder("my-skill", version="2.0.0", body="# V2")
        path2, hash2 = store_skill(skill_v2, "my-skill", "2.0.0", napoln_home)

        assert path1 != path2
        assert hash1 != hash2

    def test_excludes_napoln_file(self, tmp_path, skill_builder):
        """The .napoln provenance file is not stored."""
        skill_dir = skill_builder("my-skill")
        (skill_dir / ".napoln").write_text('version = "1.0.0"')

        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        store_path, _ = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)
        assert not (store_path / ".napoln").exists()


class TestGetStoredSkill:
    """Looking up stored skills."""

    def test_found(self, tmp_path, skill_builder):
        skill_dir = skill_builder("my-skill")
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        _, content_hash = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)
        result = get_stored_skill("my-skill", "1.0.0", content_hash, napoln_home)

        assert result is not None
        assert result.exists()

    def test_not_found(self, tmp_path):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "store").mkdir()

        result = get_stored_skill("nope", "1.0.0", "0000000", napoln_home)
        assert result is None


class TestListStoredVersions:
    """Listing stored versions of a skill."""

    def test_lists_versions(self, tmp_path, skill_builder):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        for ver, body in [("1.0.0", "# V1"), ("2.0.0", "# V2")]:
            skill = skill_builder("my-skill", version=ver, body=body)
            store_skill(skill, "my-skill", ver, napoln_home)

        versions = list_stored_versions("my-skill", napoln_home)
        assert len(versions) == 2
        ver_strings = [v[0] for v in versions]
        assert "1.0.0" in ver_strings
        assert "2.0.0" in ver_strings

    def test_empty(self, tmp_path):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "store").mkdir()

        versions = list_stored_versions("nope", napoln_home)
        assert versions == []


class TestVerifyStoreEntry:
    """Store entry integrity verification."""

    def test_valid_entry(self, tmp_path, skill_builder):
        skill_dir = skill_builder("my-skill")
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        store_path, _ = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)
        assert verify_store_entry(store_path) is True

    def test_corrupted_entry(self, tmp_path, skill_builder):
        skill_dir = skill_builder("my-skill")
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()

        store_path, _ = store_skill(skill_dir, "my-skill", "1.0.0", napoln_home)

        # Corrupt the stored file
        (store_path / "SKILL.md").write_text("CORRUPTED")

        assert verify_store_entry(store_path) is False
