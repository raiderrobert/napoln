"""Tests for napoln.core.naming."""

from __future__ import annotations

from pathlib import Path

import pytest

from napoln.core.manifest import Manifest, SkillEntry
from napoln.core.naming import namespace_for, resolve_install_id
from napoln.core.resolver import ParsedSource, ResolvedSource


def _git_resolved(host: str, owner: str, repo: str, path: str = "") -> ResolvedSource:
    parsed = ParsedSource(
        source_type="git",
        host=host,
        owner=owner,
        repo=repo,
        path=path,
        version="",
        original=f"{host}/{owner}/{repo}" + (f"/{path}" if path else ""),
    )
    source_id = f"{host}/{owner}/{repo}" + (f"/{path}" if path else "")
    return ResolvedSource(
        source_type="git",
        source_id=source_id,
        skill_dir=Path("/tmp/unused"),
        version="1.0.0",
        parsed=parsed,
    )


def _local_resolved(path: str) -> ResolvedSource:
    return ResolvedSource(
        source_type="local",
        source_id=path,
        skill_dir=Path(path),
        version="1.0.0",
    )


@pytest.mark.parametrize(
    "resolved,skill_name,expected",
    [
        # git, single-skill repo
        (
            _git_resolved("github.com", "obra", "superpowers"),
            "writing-skills",
            "obra.superpowers:writing-skills",
        ),
        # git, multi-skill repo — owner/repo namespace, NOT including subpath
        (
            _git_resolved("github.com", "obra", "superpowers", "skills/writing"),
            "writing-skills",
            "obra.superpowers:writing-skills",
        ),
        # local path — namespace from parent directory of the skill dir
        (_local_resolved("/path/to/repo-b/shared-name"), "shared-name", "repo-b:shared-name"),
        # local path with single-segment parent
        (_local_resolved("/repo-b/shared-name"), "shared-name", "repo-b:shared-name"),
    ],
)
def test_namespace_for(resolved, skill_name, expected):
    assert namespace_for(resolved, skill_name) == expected


def test_namespace_for_local_root_skill_falls_back_to_dir_name():
    """A skill whose source_id has no parent (e.g. '/skill') uses the skill dir name itself."""
    resolved = _local_resolved("/shared-name")
    # No parent segment available; deterministic fallback uses the skill dir name.
    assert namespace_for(resolved, "shared-name") == "shared-name:shared-name"


def _entry(source: str, name: str = "", version: str = "1.0.0") -> SkillEntry:
    return SkillEntry(
        source=source,
        version=version,
        store_hash="abc1234",
        installed="2026-04-14T10:00:00Z",
        updated="2026-04-14T10:00:00Z",
        name=name or "",
    )


class TestResolveInstallId:
    def test_fresh_install_uses_upstream_name(self):
        mf = Manifest()
        resolved = _git_resolved("github.com", "obra", "superpowers")

        r = resolve_install_id(mf, resolved, "writing-skills")

        assert r.install_id == "writing-skills"
        assert r.existing is None
        assert r.collision_with is None

    def test_same_source_returns_existing_entry_for_idempotency(self):
        mf = Manifest()
        mf.skills["writing-skills"] = _entry(
            source="github.com/obra/superpowers", name="writing-skills"
        )
        resolved = _git_resolved("github.com", "obra", "superpowers")

        r = resolve_install_id(mf, resolved, "writing-skills")

        assert r.install_id == "writing-skills"
        assert r.existing is mf.skills["writing-skills"]
        assert r.collision_with is None

    def test_same_source_already_namespaced_is_found_by_walk(self):
        """Once a source is namespaced, re-installing it must reuse the namespaced id."""
        mf = Manifest()
        mf.skills["shared-name"] = _entry(source="/repo-a/shared-name", name="shared-name")
        mf.skills["repo-b:shared-name"] = _entry(source="/repo-b/shared-name", name="shared-name")
        resolved = _local_resolved("/repo-b/shared-name")

        r = resolve_install_id(mf, resolved, "shared-name")

        assert r.install_id == "repo-b:shared-name"
        assert r.existing is mf.skills["repo-b:shared-name"]
        assert r.collision_with is None

    def test_collision_with_different_source_namespaces_id(self):
        mf = Manifest()
        mf.skills["shared-name"] = _entry(source="/repo-a/shared-name", name="shared-name")
        resolved = _local_resolved("/repo-b/shared-name")

        r = resolve_install_id(mf, resolved, "shared-name")

        assert r.install_id == "repo-b:shared-name"
        assert r.existing is None
        assert r.collision_with == "/repo-a/shared-name"
