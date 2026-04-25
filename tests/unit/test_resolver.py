"""Tests for napoln.core.resolver — source parsing and resolution."""

import subprocess

import pytest

from napoln.core import resolver
from napoln.core.resolver import (
    ParsedSource,
    _fetch_sentinel,
    _should_fetch,
    parse_source,
    resolve_local,
)
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


class TestNormalizeSourceForMatch:
    """Source normalization for --from-source matching."""

    def test_full_github_url(self):
        """Full URLs are normalized by stripping scheme."""
        from napoln.core.resolver import normalize_source_for_match

        assert (
            normalize_source_for_match("https://github.com/raiderrobert/flow")
            == "github.com/raiderrobert/flow"
        )

    def test_github_url_with_git_suffix(self):
        """URLs with .git suffix are normalized."""
        from napoln.core.resolver import normalize_source_for_match

        assert (
            normalize_source_for_match("https://github.com/raiderrobert/flow.git")
            == "github.com/raiderrobert/flow"
        )

    def test_git_shorthand(self):
        """GitHub shorthand is normalized to full host/path form."""
        from napoln.core.resolver import normalize_source_for_match

        assert normalize_source_for_match("raiderrobert/flow") == "github.com/raiderrobert/flow"

    def test_already_normalized(self):
        """Already normalized sources pass through unchanged."""
        from napoln.core.resolver import normalize_source_for_match

        assert (
            normalize_source_for_match("github.com/raiderrobert/flow")
            == "github.com/raiderrobert/flow"
        )

    def test_local_path_unchanged(self):
        """Local paths are not normalized."""
        from napoln.core.resolver import normalize_source_for_match

        assert normalize_source_for_match("/path/to/skill") == "/path/to/skill"

    def test_http_url_stripped(self):
        """HTTP URLs are normalized."""
        from napoln.core.resolver import normalize_source_for_match

        assert normalize_source_for_match("http://github.com/owner/repo") == "github.com/owner/repo"

    def test_git_ssh_url(self):
        """Git SSH URLs (git@host:owner/repo) are normalized."""
        from napoln.core.resolver import normalize_source_for_match

        assert (
            normalize_source_for_match("git@github.com:owner/repo.git") == "github.com/owner/repo"
        )


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


class TestShouldFetch:
    """Throttle decision for cached git fetches."""

    def test_missing_sentinel_triggers_fetch(self, tmp_path):
        assert _should_fetch(tmp_path / ".missing") is True

    def test_recent_sentinel_skips_fetch(self, tmp_path):
        sentinel = tmp_path / ".last-fetch"
        sentinel.touch()
        assert _should_fetch(sentinel, now=sentinel.stat().st_mtime + 10) is False

    def test_stale_sentinel_triggers_fetch(self, tmp_path):
        sentinel = tmp_path / ".last-fetch"
        sentinel.touch()
        assert _should_fetch(sentinel, now=sentinel.stat().st_mtime + 3600) is True


class TestResolveGitFetch:
    """resolve_git fetch scope and throttling."""

    @pytest.fixture
    def git_parsed(self):
        return ParsedSource(
            source_type="git",
            host="github.com",
            owner="owner",
            repo="repo",
            path="",
            version="main",
            original="owner/repo@main",
        )

    @pytest.fixture
    def populated_cache(self, tmp_path, git_parsed):
        """A cache dir with an already-cloned repo containing a SKILL.md."""
        cache_dir = tmp_path / "cache"
        clone_dir = cache_dir / f"{git_parsed.owner}-{git_parsed.repo}"
        clone_dir.mkdir(parents=True)
        (clone_dir / "SKILL.md").write_text("---\nname: repo\ndescription: x\n---\n# Hi")
        return cache_dir, clone_dir

    def _install_fake_git(self, monkeypatch, calls):
        monkeypatch.setattr(resolver.shutil, "which", lambda _: "/usr/bin/git")

        def fake_run(cmd, *_args, **_kwargs):
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

        monkeypatch.setattr(resolver.subprocess, "run", fake_run)

    def test_fetch_uses_origin_not_all_and_writes_sentinel(
        self, monkeypatch, git_parsed, populated_cache
    ):
        cache_dir, _ = populated_cache
        calls: list[list[str]] = []
        self._install_fake_git(monkeypatch, calls)

        resolver.resolve_git(git_parsed, cache_dir)

        fetch_calls = [c for c in calls if c[:2] == ["git", "fetch"]]
        assert fetch_calls == [["git", "fetch", "origin", "--tags"]]
        assert _fetch_sentinel(cache_dir, git_parsed.owner, git_parsed.repo).exists()

    def test_second_resolve_within_throttle_skips_fetch(
        self, monkeypatch, git_parsed, populated_cache
    ):
        cache_dir, _ = populated_cache
        calls: list[list[str]] = []
        self._install_fake_git(monkeypatch, calls)

        resolver.resolve_git(git_parsed, cache_dir)
        fetch_count_after_first = sum(1 for c in calls if c[:2] == ["git", "fetch"])
        resolver.resolve_git(git_parsed, cache_dir)
        fetch_count_after_second = sum(1 for c in calls if c[:2] == ["git", "fetch"])

        assert fetch_count_after_first == 1
        assert fetch_count_after_second == 1  # second call reused the cache

    def test_stale_sentinel_re_fetches(self, monkeypatch, git_parsed, populated_cache):
        cache_dir, _ = populated_cache
        calls: list[list[str]] = []
        self._install_fake_git(monkeypatch, calls)

        resolver.resolve_git(git_parsed, cache_dir)

        sentinel = _fetch_sentinel(cache_dir, git_parsed.owner, git_parsed.repo)
        import os as _os

        old = sentinel.stat().st_mtime - (resolver._FETCH_THROTTLE_SECONDS + 60)
        _os.utime(sentinel, (old, old))

        resolver.resolve_git(git_parsed, cache_dir)

        fetch_calls = [c for c in calls if c[:2] == ["git", "fetch"]]
        assert len(fetch_calls) == 2
