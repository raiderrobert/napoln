"""Tests for napoln.core.resolver — source parsing and resolution."""

import pytest

from napoln.core.resolver import ParsedSource, parse_source, resolve_local
from napoln.errors import ResolverError


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

    def test_local_path_relative(self, tmp_path):
        """Relative paths are parsed as local sources."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")

        parsed = parse_source(str(skill_dir))
        assert parsed.source_type == "local"

    def test_local_path_absolute(self, tmp_path):
        """Absolute paths starting with / are local sources."""
        parsed = parse_source("/absolute/path/to/skill")
        assert parsed.source_type == "local"

    def test_local_relative_dot(self):
        """Paths starting with ./ are local sources."""
        parsed = parse_source("./path/to/skill")
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

        parsed = ParsedSource(
            source_type="local", host="", owner="", repo="",
            path="", version="", original=str(skill_dir),
            local_path=skill_dir,
        )
        resolved = resolve_local(parsed)

        assert resolved.source_type == "local"
        assert resolved.version == "1.0.0"
        assert resolved.skill_dir == skill_dir

    def test_resolve_nonexistent_raises(self, tmp_path):
        parsed = ParsedSource(
            source_type="local", host="", owner="", repo="",
            path="", version="", original="/nope",
            local_path=tmp_path / "nope",
        )
        with pytest.raises(ResolverError, match="does not exist"):
            resolve_local(parsed)

    def test_resolve_file_not_dir_raises(self, tmp_path):
        f = tmp_path / "not-a-dir"
        f.write_text("hi")

        parsed = ParsedSource(
            source_type="local", host="", owner="", repo="",
            path="", version="", original=str(f),
            local_path=f,
        )
        with pytest.raises(ResolverError, match="Not a directory"):
            resolve_local(parsed)

    def test_resolve_no_version_defaults(self, tmp_path):
        """Skills without version metadata default to 0.0.0."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\ndescription: x\n---\n# Hello")

        parsed = ParsedSource(
            source_type="local", host="", owner="", repo="",
            path="", version="", original=str(skill_dir),
            local_path=skill_dir,
        )
        resolved = resolve_local(parsed)
        assert resolved.version == "0.0.0"
