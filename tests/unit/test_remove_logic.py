"""Tests for napoln.commands.remove — source matching logic."""

from __future__ import annotations

import pytest

from napoln.commands.remove import _resolve_from_source
from napoln.core import manifest as manifest_mod


def _entry(source: str) -> manifest_mod.SkillEntry:
    """Build a minimal SkillEntry with the given source."""
    return manifest_mod.SkillEntry(
        source=source,
        version="1.0.0",
        store_hash="abc123",
        installed="2024-01-01T00:00:00Z",
        updated="2024-01-01T00:00:00Z",
        agents={},
    )


class TestResolveFromSource:
    """Match --from-source against manifest entries."""

    def test_no_skills(self):
        mf = manifest_mod.Manifest()
        assert _resolve_from_source("owner/repo", mf) == []

    def test_no_match(self):
        mf = manifest_mod.Manifest()
        mf.skills["my-skill"] = _entry("github.com/alice/tools")
        assert _resolve_from_source("bob/other", mf) == []

    def test_shorthand_matches_full_source(self):
        mf = manifest_mod.Manifest()
        mf.skills["audit"] = _entry("https://github.com/raiderrobert/flow")
        assert _resolve_from_source("raiderrobert/flow", mf) == ["audit"]

    def test_multiple_skills_from_same_source(self):
        mf = manifest_mod.Manifest()
        for name in ("skill-a", "skill-b"):
            mf.skills[name] = _entry("https://github.com/owner/mono")
        assert sorted(_resolve_from_source("owner/mono", mf)) == ["skill-a", "skill-b"]

    @pytest.mark.parametrize(
        "source_in_manifest, query",
        [
            ("https://github.com/owner/repo.git", "owner/repo"),
            ("github.com/owner/repo", "owner/repo"),
            ("git@github.com:owner/repo.git", "owner/repo"),
        ],
        ids=["https-dotgit", "bare-host", "ssh"],
    )
    def test_normalization_variants(self, source_in_manifest, query):
        mf = manifest_mod.Manifest()
        mf.skills["the-skill"] = _entry(source_in_manifest)
        assert _resolve_from_source(query, mf) == ["the-skill"]
