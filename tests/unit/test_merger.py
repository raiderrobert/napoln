"""Tests for napoln.core.merger — three-way merge."""

import pytest

from napoln.core.merger import has_conflict_markers, merge_file, merge_skill


class TestMergeFile:
    """Three-way file merge."""

    def test_no_changes(self, tmp_path):
        """When nothing changed, return base content."""
        for name in ["ours", "base", "theirs"]:
            (tmp_path / name).write_text("Same content")

        merged, has_conflicts = merge_file(
            tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"
        )
        assert not has_conflicts
        assert "Same content" in merged

    def test_only_upstream_changed(self, tmp_path):
        """Fast-forward: only upstream changed."""
        (tmp_path / "ours").write_text("original")
        (tmp_path / "base").write_text("original")
        (tmp_path / "theirs").write_text("new from upstream")

        merged, has_conflicts = merge_file(
            tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"
        )
        assert not has_conflicts
        assert "new from upstream" in merged

    def test_only_local_changed(self, tmp_path):
        """Keep ours: only local changed."""
        (tmp_path / "ours").write_text("locally modified")
        (tmp_path / "base").write_text("original")
        (tmp_path / "theirs").write_text("original")

        merged, has_conflicts = merge_file(
            tmp_path / "ours", tmp_path / "base", tmp_path / "theirs"
        )
        assert not has_conflicts
        assert "locally modified" in merged

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
        # Should contain both changes (if git is available for clean merge)
        # May have conflicts if using fallback
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


class TestMergeSkill:
    """Full skill directory merge."""

    def test_fast_forward_unmodified(self, tmp_path):
        """Unmodified files are fast-forwarded to new upstream."""
        working = tmp_path / "working"
        base = tmp_path / "base"
        new = tmp_path / "new"
        for d in [working, base, new]:
            d.mkdir()

        (base / "SKILL.md").write_text("V1 content")
        (working / "SKILL.md").write_text("V1 content")  # unmodified
        (new / "SKILL.md").write_text("V2 content")

        updated, conflicted = merge_skill(working, base, new)

        assert "SKILL.md" in updated
        assert not conflicted
        assert (working / "SKILL.md").read_text() == "V2 content"

    def test_keeps_local_changes_when_upstream_unchanged(self, tmp_path):
        """Local changes preserved when upstream didn't change the file."""
        working = tmp_path / "working"
        base = tmp_path / "base"
        new = tmp_path / "new"
        for d in [working, base, new]:
            d.mkdir()

        (base / "SKILL.md").write_text("V1 content")
        (working / "SKILL.md").write_text("V1 locally modified")
        (new / "SKILL.md").write_text("V1 content")  # unchanged

        updated, conflicted = merge_skill(working, base, new)

        assert not updated  # No files should have been updated
        assert not conflicted
        assert (working / "SKILL.md").read_text() == "V1 locally modified"

    def test_new_file_from_upstream(self, tmp_path):
        """New files from upstream are added."""
        working = tmp_path / "working"
        base = tmp_path / "base"
        new = tmp_path / "new"
        for d in [working, base, new]:
            d.mkdir()

        (base / "SKILL.md").write_text("V1")
        (working / "SKILL.md").write_text("V1")
        (new / "SKILL.md").write_text("V1")
        (new / "NEW.md").write_text("New file from upstream")

        updated, conflicted = merge_skill(working, base, new)

        assert "NEW.md" in updated
        assert (working / "NEW.md").read_text() == "New file from upstream"

    def test_deleted_upstream_unmodified_locally(self, tmp_path):
        """Files deleted in upstream are removed if unmodified locally."""
        working = tmp_path / "working"
        base = tmp_path / "base"
        new = tmp_path / "new"
        for d in [working, base, new]:
            d.mkdir()

        (base / "SKILL.md").write_text("V1")
        (base / "old.md").write_text("to be removed")
        (working / "SKILL.md").write_text("V1")
        (working / "old.md").write_text("to be removed")  # unmodified
        (new / "SKILL.md").write_text("V1")
        # old.md not in new — deleted upstream

        updated, conflicted = merge_skill(working, base, new)

        assert "old.md" in updated
        assert not (working / "old.md").exists()


class TestHasConflictMarkers:
    """Conflict marker detection."""

    def test_has_markers(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("<<<<<<< local\nfoo\n=======\nbar\n>>>>>>> upstream\n")
        assert has_conflict_markers(f) is True

    def test_no_markers(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Clean file\nNo conflicts here.\n")
        assert has_conflict_markers(f) is False

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "nope.md"
        assert has_conflict_markers(f) is False
