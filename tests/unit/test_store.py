"""Tests for napoln.core.store — content-addressed store operations."""

import pytest

from napoln.core.store import (
    get_stored_skill,
    list_stored_versions,
    store_skill,
    verify_store_entry,
)


@pytest.fixture
def store_home(tmp_path):
    """Napoln home with store and cache dirs."""
    nh = tmp_path / ".napoln"
    nh.mkdir()
    (nh / "store").mkdir()
    return nh


class TestStoreSkill:
    """Storing skills in the content-addressed store."""

    def test_stores_skill(self, skill_builder, store_home):
        """A skill is stored with version-hash directory name."""
        skill_dir = skill_builder("my-skill")
        store_path, content_hash = store_skill(skill_dir, "my-skill", "1.0.0", store_home)

        assert store_path.exists()
        assert store_path.name == f"1.0.0-{content_hash}"
        assert (store_path / "SKILL.md").exists()

    def test_idempotent(self, skill_builder, store_home):
        """Storing the same skill twice is a no-op."""
        skill_dir = skill_builder("my-skill")

        path1, hash1 = store_skill(skill_dir, "my-skill", "1.0.0", store_home)
        path2, hash2 = store_skill(skill_dir, "my-skill", "1.0.0", store_home)

        assert path1 == path2
        assert hash1 == hash2

    def test_different_versions(self, skill_builder, store_home):
        """Different content produces different store entries."""
        skill_v1 = skill_builder("my-skill", version="1.0.0", body="# V1")
        path1, hash1 = store_skill(skill_v1, "my-skill", "1.0.0", store_home)

        skill_v2 = skill_builder("my-skill", version="2.0.0", body="# V2")
        path2, hash2 = store_skill(skill_v2, "my-skill", "2.0.0", store_home)

        assert path1 != path2
        assert hash1 != hash2

    def test_excludes_napoln_file(self, skill_builder, store_home):
        """The .napoln provenance file is not stored."""
        skill_dir = skill_builder("my-skill")
        (skill_dir / ".napoln").write_text('version = "1.0.0"')

        store_path, _ = store_skill(skill_dir, "my-skill", "1.0.0", store_home)
        assert not (store_path / ".napoln").exists()


class TestGetStoredSkill:
    """Looking up stored skills."""

    def test_found(self, skill_builder, store_home):
        skill_dir = skill_builder("my-skill")
        _, content_hash = store_skill(skill_dir, "my-skill", "1.0.0", store_home)
        result = get_stored_skill("my-skill", "1.0.0", content_hash, store_home)

        assert result is not None
        assert result.exists()

    def test_not_found(self, store_home):
        result = get_stored_skill("nope", "1.0.0", "0000000", store_home)
        assert result is None


class TestListStoredVersions:
    """Listing stored versions of a skill."""

    def test_lists_versions(self, skill_builder, store_home):
        for ver, body in [("1.0.0", "# V1"), ("2.0.0", "# V2")]:
            skill = skill_builder("my-skill", version=ver, body=body)
            store_skill(skill, "my-skill", ver, store_home)

        versions = list_stored_versions("my-skill", store_home)
        assert len(versions) == 2
        ver_strings = [v[0] for v in versions]
        assert "1.0.0" in ver_strings
        assert "2.0.0" in ver_strings

    def test_empty(self, store_home):
        versions = list_stored_versions("nope", store_home)
        assert versions == []


class TestVerifyStoreEntry:
    """Store entry integrity verification."""

    def test_valid_entry(self, skill_builder, store_home):
        skill_dir = skill_builder("my-skill")
        store_path, _ = store_skill(skill_dir, "my-skill", "1.0.0", store_home)
        assert verify_store_entry(store_path) is True

    def test_corrupted_entry(self, skill_builder, store_home):
        skill_dir = skill_builder("my-skill")
        store_path, _ = store_skill(skill_dir, "my-skill", "1.0.0", store_home)

        (store_path / "SKILL.md").write_text("CORRUPTED")
        assert verify_store_entry(store_path) is False

    def test_cleans_up_temp_on_os_error(self, skill_builder, store_home, monkeypatch):
        """OSError during copytree should clean up the temp directory."""
        skill_dir = skill_builder("my-skill")
        import shutil

        def failing_copytree(*_args, **_kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, "copytree", failing_copytree)

        with pytest.raises(OSError, match="disk full"):
            store_skill(skill_dir, "my-skill", "1.0.0", store_home)

        # No stray temp directory should remain
        skill_store = store_home / "store" / "my-skill"
        if skill_store.exists():
            temps = [p for p in skill_store.iterdir() if p.name.startswith(".")]
            assert temps == [], f"unexpected temp dirs: {temps}"

    def test_propagates_type_error(self, skill_builder, store_home, monkeypatch):
        """Programming bugs must not be swallowed."""
        skill_dir = skill_builder("my-skill")

        import shutil

        def failing_copytree(*_args, **_kwargs):
            raise TypeError("programming bug")

        monkeypatch.setattr(shutil, "copytree", failing_copytree)

        with pytest.raises(TypeError, match="programming bug"):
            store_skill(skill_dir, "my-skill", "1.0.0", store_home)
