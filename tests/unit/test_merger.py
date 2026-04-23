"""Tests for napoln.core.merger — three-way merge."""

import pytest

from napoln.core import merger
from napoln.core.merger import has_conflict_markers, merge_file, merge_skill


def _write_triplet(tmp_path, ours, base, theirs):
    (tmp_path / "ours").write_text(ours)
    (tmp_path / "base").write_text(base)
    (tmp_path / "theirs").write_text(theirs)
    return tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"


class TestMergeFile:
    """Three-way file merge."""

    @pytest.mark.parametrize(
        "ours_text, base_text, theirs_text, expect_conflicts, expect_contains",
        [
            # No changes anywhere
            ("Same content", "Same content", "Same content", False, "Same content"),
            # Only upstream changed → fast-forward
            ("original", "original", "new from upstream", False, "new from upstream"),
            # Only local changed → keep ours
            ("locally modified", "original", "original", False, "locally modified"),
        ],
        ids=["no-changes", "only-upstream", "only-local"],
    )
    def test_one_side_or_no_changes(
        self,
        tmp_path,
        ours_text,
        base_text,
        theirs_text,
        expect_conflicts,
        expect_contains,
    ):
        (tmp_path / "ours").write_text(ours_text)
        (tmp_path / "base").write_text(base_text)
        (tmp_path / "theirs").write_text(theirs_text)

        merged, has_conflicts = merge_file(
            tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"
        )
        assert has_conflicts is expect_conflicts
        assert expect_contains in merged

    def test_both_changed_different_lines(self, tmp_path):
        """Clean merge when changes don't overlap."""
        base_content = "line 1\nline 2\nline 3\nline 4\nline 5\n"
        ours_content = "line 1 local\nline 2\nline 3\nline 4\nline 5\n"
        theirs_content = "line 1\nline 2\nline 3\nline 4\nline 5 upstream\n"

        (tmp_path / "ours").write_text(ours_content)
        (tmp_path / "base").write_text(base_content)
        (tmp_path / "theirs").write_text(theirs_content)

        merged, has_conflicts = merge_file(
            tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"
        )
        assert merged  # Non-empty result

    def test_both_changed_same_line_conflicts(self, tmp_path):
        """Conflict when both change the same line."""
        (tmp_path / "base").write_text("original line\n")
        (tmp_path / "ours").write_text("local change\n")
        (tmp_path / "theirs").write_text("upstream change\n")

        merged, has_conflicts = merge_file(
            tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"
        )
        assert has_conflicts
        assert "<<<<<<<" in merged


class TestPythonFallbackMerge:
    """Python fallback merge (used when git is unavailable)."""

    @pytest.fixture(autouse=True)
    def _force_fallback(self, monkeypatch):
        monkeypatch.setattr(merger, "has_git", lambda: False)

    def test_disjoint_additions_merge_cleanly(self, tmp_path):
        """Adding lines at opposite ends of the file must not conflict."""
        base = "# Skill\n\n## Instructions\n1. Step one\n2. Step two\n"
        ours = "# Skill\n\n## Instructions\n1. Step one\n2. Step two\n\n## Tips\nAsk for help if stuck.\n"
        theirs = (
            "# Skill\n\n## Prerequisites\nRequires Python 3.11+\n\n"
            "## Instructions\n1. Step one\n2. Step two\n"
        )

        ours_p, base_p, theirs_p = _write_triplet(tmp_path, ours, base, theirs)
        merged, has_conflicts = merge_file(ours_p, base_p, theirs_p)

        assert not has_conflicts
        assert "<<<<<<<" not in merged
        assert "## Tips" in merged
        assert "## Prerequisites" in merged
        assert "Requires Python 3.11+" in merged
        assert "Ask for help if stuck." in merged

    def test_overlapping_edits_emit_conflict_markers(self, tmp_path):
        """When both sides edit the same region the result has conflict markers."""
        base = "line 1\nline 2\nline 3\n"
        ours = "line 1\nlocal change\nline 3\n"
        theirs = "line 1\nupstream change\nline 3\n"

        ours_p, base_p, theirs_p = _write_triplet(tmp_path, ours, base, theirs)
        merged, has_conflicts = merge_file(ours_p, base_p, theirs_p)

        assert has_conflicts
        assert "<<<<<<<" in merged
        assert "=======" in merged
        assert ">>>>>>>" in merged
        assert "local change" in merged
        assert "upstream change" in merged
        # Unchanged context around the conflict is preserved outside the markers.
        assert merged.startswith("line 1\n")
        assert merged.rstrip().endswith("line 3")

    def test_identical_changes_merge_cleanly(self, tmp_path):
        """If both sides make the same change, no conflict."""
        ours_p, base_p, theirs_p = _write_triplet(tmp_path, "v2\n", "v1\n", "v2\n")
        merged, has_conflicts = merge_file(ours_p, base_p, theirs_p)
        assert not has_conflicts
        assert merged == "v2\n"

    def test_only_local_changes(self, tmp_path):
        ours_p, base_p, theirs_p = _write_triplet(tmp_path, "local\n", "base\n", "base\n")
        merged, has_conflicts = merge_file(ours_p, base_p, theirs_p)
        assert not has_conflicts
        assert merged == "local\n"

    def test_only_upstream_changes(self, tmp_path):
        ours_p, base_p, theirs_p = _write_triplet(tmp_path, "base\n", "base\n", "upstream\n")
        merged, has_conflicts = merge_file(ours_p, base_p, theirs_p)
        assert not has_conflicts
        assert merged == "upstream\n"


@pytest.fixture
def merge_dirs(tmp_path):
    """Create working/base/new directories for merge_skill tests."""
    dirs = {}
    for name in ("working", "base", "new"):
        d = tmp_path / name
        d.mkdir()
        dirs[name] = d
    return dirs


class TestMergeSkill:
    """Full skill directory merge."""

    def test_fast_forward_unmodified(self, merge_dirs):
        """Unmodified files are fast-forwarded to new upstream."""
        merge_dirs["base"] / "SKILL.md" and (merge_dirs["base"] / "SKILL.md").write_text(
            "V1 content"
        )
        (merge_dirs["working"] / "SKILL.md").write_text("V1 content")
        (merge_dirs["new"] / "SKILL.md").write_text("V2 content")

        updated, conflicted = merge_skill(
            merge_dirs["working"], merge_dirs["base"], merge_dirs["new"]
        )

        assert "SKILL.md" in updated
        assert not conflicted
        assert (merge_dirs["working"] / "SKILL.md").read_text() == "V2 content"

    def test_keeps_local_changes_when_upstream_unchanged(self, merge_dirs):
        """Local changes preserved when upstream didn't change the file."""
        (merge_dirs["base"] / "SKILL.md").write_text("V1 content")
        (merge_dirs["working"] / "SKILL.md").write_text("V1 locally modified")
        (merge_dirs["new"] / "SKILL.md").write_text("V1 content")

        updated, conflicted = merge_skill(
            merge_dirs["working"], merge_dirs["base"], merge_dirs["new"]
        )

        assert not updated
        assert not conflicted
        assert (merge_dirs["working"] / "SKILL.md").read_text() == "V1 locally modified"

    def test_new_file_from_upstream(self, merge_dirs):
        """New files from upstream are added."""
        for d in merge_dirs.values():
            (d / "SKILL.md").write_text("V1")
        (merge_dirs["new"] / "NEW.md").write_text("New file from upstream")

        updated, conflicted = merge_skill(
            merge_dirs["working"], merge_dirs["base"], merge_dirs["new"]
        )

        assert "NEW.md" in updated
        assert (merge_dirs["working"] / "NEW.md").read_text() == "New file from upstream"

    def test_deleted_upstream_unmodified_locally(self, merge_dirs):
        """Files deleted in upstream are removed if unmodified locally."""
        (merge_dirs["base"] / "SKILL.md").write_text("V1")
        (merge_dirs["base"] / "old.md").write_text("to be removed")
        (merge_dirs["working"] / "SKILL.md").write_text("V1")
        (merge_dirs["working"] / "old.md").write_text("to be removed")
        (merge_dirs["new"] / "SKILL.md").write_text("V1")

        updated, conflicted = merge_skill(
            merge_dirs["working"], merge_dirs["base"], merge_dirs["new"]
        )

        assert "old.md" in updated
        assert not (merge_dirs["working"] / "old.md").exists()


class TestHasConflictMarkers:
    """Conflict marker detection."""

    @pytest.mark.parametrize(
        "content, expected",
        [
            ("<<<<<<< local\nfoo\n=======\nbar\n>>>>>>> upstream\n", True),
            ("# Clean file\nNo conflicts here.\n", False),
        ],
        ids=["with-markers", "clean"],
    )
    def test_detects_markers(self, tmp_path, content, expected):
        f = tmp_path / "test.md"
        f.write_text(content)
        assert has_conflict_markers(f) is expected

    def test_nonexistent_file(self, tmp_path):
        assert has_conflict_markers(tmp_path / "nope.md") is False
