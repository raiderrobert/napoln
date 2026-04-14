"""Tests for napoln.core.hasher — content-addressed hashing."""

import pytest

from napoln.core.hasher import hash_skill, hash_skill_full


class TestHashSkill:
    """Content hashing produces deterministic, content-sensitive hashes."""

    def test_deterministic(self, tmp_path):
        """Same content always produces the same hash."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")

        assert hash_skill(skill) == hash_skill(skill)

    def test_returns_7_chars(self, tmp_path):
        """Hash prefix is exactly 7 hex characters."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")

        result = hash_skill(skill)
        assert len(result) == 7
        assert all(c in "0123456789abcdef" for c in result)

    def test_full_hash_is_64_chars(self, tmp_path):
        """Full SHA-256 hash is 64 hex characters."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Hello")

        result = hash_skill_full(skill)
        assert len(result) == 64

    def test_content_sensitive(self, tmp_path):
        """Changing any file content changes the hash."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# V1")
        hash_v1 = hash_skill(skill)

        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# V2")
        hash_v2 = hash_skill(skill)

        assert hash_v1 != hash_v2

    def test_excludes_napoln_provenance(self, tmp_path):
        """The .napoln provenance file is excluded from hashing."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")
        hash_without = hash_skill(skill)

        (skill / ".napoln").write_text('version = "1.0.0"')
        hash_with = hash_skill(skill)

        assert hash_without == hash_with

    @pytest.mark.parametrize(
        "files, expected_different",
        [
            # Adding a file changes the hash
            ({"SKILL.md": "# A"}, {"SKILL.md": "# A", "scripts/run.sh": "#!/bin/bash"}),
            # Renaming a file changes the hash
            ({"SKILL.md": "# A", "old.txt": "x"}, {"SKILL.md": "# A", "new.txt": "x"}),
            # Same content, different structure
            ({"SKILL.md": "# A", "a/b.md": "x"}, {"SKILL.md": "# A", "a-b.md": "x"}),
        ],
        ids=["add-file", "rename-file", "restructure"],
    )
    def test_path_sensitive(self, tmp_path, files, expected_different):
        """Hash changes when file paths change, even if content is the same."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        for d, file_map in [(dir_a, files), (dir_b, expected_different)]:
            d.mkdir()
            for path, content in file_map.items():
                f = d / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content)

        assert hash_skill(dir_a) != hash_skill(dir_b)

    def test_empty_directory(self, tmp_path):
        """Empty directory produces a valid hash."""
        skill = tmp_path / "empty"
        skill.mkdir()

        result = hash_skill(skill)
        assert len(result) == 7

    def test_subdirectory_ordering(self, tmp_path):
        """Files in subdirectories are sorted by relative path."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "b.md").write_text("B")
        (skill / "a.md").write_text("A")
        sub = skill / "sub"
        sub.mkdir()
        (sub / "c.md").write_text("C")

        # Hash should be the same regardless of creation order
        hash1 = hash_skill(skill)

        skill2 = tmp_path / "my-skill2"
        skill2.mkdir()
        sub2 = skill2 / "sub"
        sub2.mkdir()
        (sub2 / "c.md").write_text("C")
        (skill2 / "a.md").write_text("A")
        (skill2 / "b.md").write_text("B")

        hash2 = hash_skill(skill2)
        assert hash1 == hash2
