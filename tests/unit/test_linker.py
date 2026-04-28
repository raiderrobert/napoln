"""Tests for napoln.core.linker — reflink/copy placement."""

import pytest

from napoln.core.linker import clone_file, place_skill, restore_placement


@pytest.fixture
def store_skill(tmp_path):
    """Create a store skill with SKILL.md and a script."""
    store = tmp_path / "store" / "my-skill"
    store.mkdir(parents=True)
    (store / "SKILL.md").write_text("# Hello")
    (store / "scripts").mkdir()
    (store / "scripts" / "run.sh").write_text("#!/bin/bash")
    return store


class TestPlaceSkill:
    """Skill placement via reflink with copy fallback."""

    def test_places_all_files(self, tmp_path, store_skill):
        """All files from store are placed in target directory."""
        target = tmp_path / "target" / "my-skill"
        place_skill(store_skill, target)

        assert (target / "SKILL.md").read_text() == "# Hello"
        assert (target / "scripts" / "run.sh").read_text() == "#!/bin/bash"

    def test_returns_link_mode(self, tmp_path, store_skill):
        """Returns 'clone' or 'copy' depending on filesystem support."""
        target = tmp_path / "target" / "my-skill"
        mode = place_skill(store_skill, target)
        assert mode in ("clone", "copy")

    def test_creates_parent_directories(self, tmp_path, store_skill):
        """Target parent directories are created if they don't exist."""
        target = tmp_path / "deep" / "nested" / "path" / "my-skill"
        place_skill(store_skill, target)
        assert (target / "SKILL.md").exists()

    @pytest.mark.parametrize(
        "existing_content",
        [None, "# Old"],
        ids=["fresh", "overwrite"],
    )
    def test_overwrite_behavior(self, tmp_path, store_skill, existing_content):
        target = tmp_path / "target" / "my-skill"
        target.mkdir(parents=True)
        if existing_content:
            (target / "SKILL.md").write_text(existing_content)

        place_skill(store_skill, target)
        assert (target / "SKILL.md").read_text() == "# Hello"

    def test_preserves_subdirectory_structure(self, tmp_path):
        """Nested directories are preserved during placement."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Root")
        refs = store / "references"
        refs.mkdir()
        (refs / "guide.md").write_text("# Guide")
        deep = refs / "deep"
        deep.mkdir()
        (deep / "nested.md").write_text("# Nested")

        target = tmp_path / "target" / "my-skill"
        place_skill(store, target)

        assert (target / "references" / "guide.md").read_text() == "# Guide"
        assert (target / "references" / "deep" / "nested.md").read_text() == "# Nested"


class TestCloneFile:
    """File-level clone with copy fallback."""

    @pytest.fixture
    def src_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        return src

    def test_content_matches(self, tmp_path, src_file):
        dst = tmp_path / "dst.txt"
        clone_file(src_file, dst)
        assert dst.read_text() == "hello"

    def test_independence(self, tmp_path, src_file):
        """Modifying the clone does not affect the original."""
        dst = tmp_path / "dst.txt"
        clone_file(src_file, dst)
        dst.write_text("modified")
        assert src_file.read_text() == "hello"

    def test_returns_mode(self, tmp_path, src_file):
        """Returns 'clone' or 'copy'."""
        dst = tmp_path / "dst.txt"
        mode = clone_file(src_file, dst)
        assert mode in ("clone", "copy")


class TestRestorePlacement:
    """restore_placement — idempotent placement from store."""

    def test_places_when_missing(self, tmp_path, skill_builder):
        skill_path = skill_builder(name="restore-test")
        from napoln.core import store as store_mod

        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "store").mkdir()
        store_path, content_hash = store_mod.store_skill(
            skill_path, "restore-test", "1.0.0", napoln_home
        )

        placement = tmp_path / "agents" / "skills" / "restore-test"
        result = restore_placement(store_path, placement, "owner/repo", "1.0.0", content_hash)

        assert result is not None
        assert (placement / "SKILL.md").exists()
        assert (placement / ".napoln").exists()

    def test_skips_when_already_exists(self, tmp_path, skill_builder):
        skill_path = skill_builder(name="exists-test")
        from napoln.core import store as store_mod

        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "store").mkdir()
        store_path, content_hash = store_mod.store_skill(
            skill_path, "exists-test", "1.0.0", napoln_home
        )

        placement = tmp_path / "agents" / "skills" / "exists-test"
        placement.mkdir(parents=True)
        (placement / "SKILL.md").write_text("already here")

        result = restore_placement(store_path, placement, "owner/repo", "1.0.0", content_hash)

        assert result is None
        assert (placement / "SKILL.md").read_text() == "already here"
