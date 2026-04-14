"""Tests for napoln.core.resolver — source parsing and resolution."""

import pytest

from napoln.core.resolver import ParsedSource, parse_source, resolve_local
from napoln.errors import ResolverError


def _local_parsed(path, original=None):
    """Build a ParsedSource for a local path."""
    return ParsedSource(
        source_type="local",
        host="",
        owner="",
        repo="",
        path="",
        version="",
        original=original or str(path),
        local_path=path,
    )


class TestParseSource:
    """Source identifier parsing."""

    @pytest.mark.parametrize(
        "source, expected_type, expected_host, expected_owner, expected_repo",
        [
            ("owner/repo", "git", "github.com", "owner", "repo"),
            ("owner/repo/skills/my-skill", "git", "github.com", "owner", "repo"),
            ("github.com/owner/repo", "git", "github.com", "owner", "repo"),
            ("gitlab.com/owner/repo", "git", "gitlab.com", "owner", "repo"),
        ],
        ids=["shorthand", "shorthand-path", "github-full", "gitlab-full"],
    )
    def test_git_sources(self, source, expected_type, expected_host, expected_owner, expected_repo):
        parsed = parse_source(source)
        assert parsed.source_type == expected_type
        assert parsed.host == expected_host
        assert parsed.owner == expected_owner
        assert parsed.repo == expected_repo

    @pytest.mark.parametrize(
        "source, expected_version",
        [
            ("owner/repo@v1.2.0", "v1.2.0"),
            ("owner/repo@main", "main"),
            ("owner/repo@abc1234", "abc1234"),
            ("github.com/owner/repo@v1.2.0", "v1.2.0"),
        ],
        ids=["semver-tag", "branch", "commit", "full-with-version"],
    )
    def test_version_parsing(self, source, expected_version):
        parsed = parse_source(source)
        assert parsed.version == expected_version

    @pytest.mark.parametrize(
        "source",
        ["./path/to/skill", "../relative", "/absolute/path/to/skill"],
        ids=["dot-relative", "parent-relative", "absolute"],
    )
    def test_local_paths(self, source):
        """Paths starting with ./, ../, or / are parsed as local sources."""
        parsed = parse_source(source)
        assert parsed.source_type == "local"

    def test_local_path_existing_dir(self, tmp_path):
        """Existing directories are detected as local sources."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")

        parsed = parse_source(str(skill_dir))
        assert parsed.source_type == "local"

    def test_path_extraction(self):
        """Subdirectory paths within repos are extracted."""
        parsed = parse_source("owner/repo/skills/my-skill")
        assert parsed.path == "skills/my-skill"

    def test_github_url(self):
        """Full HTTPS GitHub URLs are parsed."""
        parsed = parse_source("https://github.com/owner/repo.git")
        assert parsed.source_type == "git"
        assert parsed.host == "github.com"
        assert parsed.owner == "owner"
        assert parsed.repo == "repo"


class TestResolveLocal:
    """Local source resolution."""

    def test_resolve_valid_skill(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: my-skill\ndescription: Test\nmetadata:\n  version: "1.0.0"\n---\n# Hello'
        )

        resolved = resolve_local(_local_parsed(skill_dir))

        assert resolved.source_type == "local"
        assert resolved.version == "1.0.0"
        assert resolved.skill_dir == skill_dir

    @pytest.mark.parametrize(
        "setup, match",
        [
            ("nonexistent", "does not exist"),
            ("file", "Not a directory"),
        ],
        ids=["nonexistent", "not-a-dir"],
    )
    def test_resolve_invalid_raises(self, tmp_path, setup, match):
        if setup == "nonexistent":
            path = tmp_path / "nope"
        else:
            path = tmp_path / "not-a-dir"
            path.write_text("hi")

        with pytest.raises(ResolverError, match=match):
            resolve_local(_local_parsed(path))

    def test_resolve_no_version_defaults(self, tmp_path):
        """Skills without version metadata default to 0.0.0."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\ndescription: x\n---\n# Hello")

        resolved = resolve_local(_local_parsed(skill_dir))
        assert resolved.version == "0.0.0"
