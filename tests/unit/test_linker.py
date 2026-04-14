"""Tests for napoln.core.linker — reflink/copy placement."""

import pytest

from napoln.core.linker import clone_file, place_skill


class TestPlaceSkill:
    """Skill placement via reflink with copy fallback."""

    def test_places_all_files(self, tmp_path):
        """All files from store are placed in target directory."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Hello")
        (store / "scripts").mkdir()
        (store / "scripts" / "run.sh").write_text("#!/bin/bash")

        target = tmp_path / "target" / "my-skill"
        place_skill(store, target)

        assert (target / "SKILL.md").read_text() == "# Hello"
        assert (target / "scripts" / "run.sh").read_text() == "#!/bin/bash"

    def test_returns_link_mode(self, tmp_path):
        """Returns 'clone' or 'copy' depending on filesystem support."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Hello")

        target = tmp_path / "target" / "my-skill"
        mode = place_skill(store, target)

        assert mode in ("clone", "copy")

    def test_creates_parent_directories(self, tmp_path):
        """Target parent directories are created if they don't exist."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Hello")

        target = tmp_path / "deep" / "nested" / "path" / "my-skill"
        place_skill(store, target)

        assert (target / "SKILL.md").exists()

    @pytest.mark.parametrize(
        "existing_content",
        [None, "# Old"],
        ids=["fresh", "overwrite"],
    )
    def test_overwrite_behavior(self, tmp_path, existing_content):
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# New")

        target = tmp_path / "target" / "my-skill"
        target.mkdir(parents=True)
        if existing_content:
            (target / "SKILL.md").write_text(existing_content)

        place_skill(store, target)
        assert (target / "SKILL.md").read_text() == "# New"

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

    def test_content_matches(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("hello")

        clone_file(src, dst)

        assert dst.read_text() == "hello"

    def test_independence(self, tmp_path):
        """Modifying the clone does not affect the original."""
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("original")

        clone_file(src, dst)
        dst.write_text("modified")

        assert src.read_text() == "original"

    def test_returns_mode(self, tmp_path):
        """Returns 'clone' or 'copy'."""
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("test")

        mode = clone_file(src, dst)
        assert mode in ("clone", "copy")
