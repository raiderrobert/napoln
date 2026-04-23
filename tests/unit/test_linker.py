"""Tests for napoln.core.linker — reflink/copy placement."""

import pytest

from napoln.core import linker
from napoln.core.linker import clone_file, place_skill


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

    def test_existing_placement_survives_failed_replacement(
        self, tmp_path, store_skill, monkeypatch
    ):
        """If placement fails partway, the existing target directory is preserved."""
        target = tmp_path / "target" / "my-skill"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("# Old content")
        (target / "existing.txt").write_text("still here")

        calls = {"n": 0}
        real_clone_file = linker.clone_file

        def flaky_clone(src, dst):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise RuntimeError("simulated interruption")
            return real_clone_file(src, dst)

        monkeypatch.setattr(linker, "clone_file", flaky_clone)

        with pytest.raises(RuntimeError, match="simulated interruption"):
            place_skill(store_skill, target)

        assert (target / "SKILL.md").read_text() == "# Old content"
        assert (target / "existing.txt").read_text() == "still here"
        # No temp dir should be left behind.
        leftovers = sorted(p.name for p in target.parent.iterdir() if p.name != target.name)
        assert leftovers == [], f"unexpected siblings: {leftovers}"

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
