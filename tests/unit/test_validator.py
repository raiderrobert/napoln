"""Tests for napoln.core.validator — SKILL.md validation."""

import pytest

from napoln.core.validator import validate_skill


class TestValidateSkill:
    """SKILL.md validation catches issues but remains lenient."""

    @pytest.mark.parametrize(
        "frontmatter, expect_valid",
        [
            ("name: my-skill\ndescription: Does things", True),
            ("name: my-skill\ndescription: Does things\nlicense: MIT", True),
            ("name: MY-SKILL\ndescription: Does things", True),  # warning, not error
            ("name: my-skill", False),  # missing description
            ("description: Does things", False),  # missing name
        ],
        ids=["minimal-valid", "with-optional", "uppercase-name", "no-desc", "no-name"],
    )
    def test_frontmatter_validation(self, tmp_path, frontmatter, expect_valid):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Body")

        result = validate_skill(skill_dir)
        assert result.is_valid == expect_valid

    def test_missing_skill_md(self, tmp_path):
        """Skill directory without SKILL.md fails validation."""
        skill_dir = tmp_path / "no-skill"
        skill_dir.mkdir()

        result = validate_skill(skill_dir)
        assert not result.is_valid
        assert any("SKILL.md not found" in e.message for e in result.errors)

    def test_empty_frontmatter(self, tmp_path):
        """Empty frontmatter fails validation."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\n\n---\n# Body")

        result = validate_skill(skill_dir)
        assert not result.is_valid

    def test_no_frontmatter(self, tmp_path):
        """No frontmatter delimiters fails validation."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Just a heading")

        result = validate_skill(skill_dir)
        assert not result.is_valid

    @pytest.mark.parametrize(
        "name, expected_warnings",
        [
            ("good-name", []),
            ("a", []),  # min length
            ("a" * 64, []),  # max length
            ("a" * 65, ["name exceeds 64 characters"]),  # too long
            ("UPPER", ["name must be lowercase"]),
            ("-leading", ["name must not start with hyphen"]),
            ("trailing-", ["name must not end with hyphen"]),
            ("double--hyphen", ["consecutive hyphens"]),
            ("has_underscore", ["invalid characters"]),
        ],
        ids=[
            "valid",
            "min-len",
            "max-len",
            "too-long",
            "uppercase",
            "leading-hyphen",
            "trailing-hyphen",
            "double-hyphen",
            "underscore",
        ],
    )
    def test_name_validation(self, tmp_path, name, expected_warnings):
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test\n---\n# Body")

        result = validate_skill(skill_dir)
        warning_messages = [w.message for w in result.warnings]
        for expected in expected_warnings:
            assert any(expected in msg for msg in warning_messages)

    @pytest.mark.parametrize(
        "dir_name, yaml_name, expect_warning",
        [
            ("my-skill", "my-skill", False),
            ("my-skill", "other-name", True),
        ],
        ids=["matching", "mismatched"],
    )
    def test_name_matches_directory(self, tmp_path, dir_name, yaml_name, expect_warning):
        skill_dir = tmp_path / dir_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {yaml_name}\ndescription: Test\n---\n# Body"
        )

        result = validate_skill(skill_dir)
        has_mismatch_warning = any("match" in w.message.lower() for w in result.warnings)
        assert has_mismatch_warning == expect_warning

    def test_returns_name_and_description(self, tmp_path):
        """Validation result includes parsed name and description."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: My description\n---\n# Body"
        )

        result = validate_skill(skill_dir)
        assert result.name == "my-skill"
        assert result.description == "My description"

    def test_returns_metadata(self, tmp_path):
        """Validation result includes metadata dict."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: my-skill\ndescription: Test\nmetadata:\n  version: "1.0.0"\n  author: test\n---\n# Body'
        )

        result = validate_skill(skill_dir)
        assert result.metadata == {"version": "1.0.0", "author": "test"}
