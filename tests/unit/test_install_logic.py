"""Tests for napoln.commands.install — exception specificity."""

from __future__ import annotations

import pytest

from napoln.commands.install import _sync_manifest
from napoln.core import manifest as manifest_mod
from napoln.errors import NapolnError, PlacementError


class TestSyncManifestExceptions:
    """Regression: broad except Exception swallows programming bugs."""

    @pytest.fixture
    def manifest_with_skill(self):
        mf = manifest_mod.Manifest()
        mf.skills["my-skill"] = manifest_mod.SkillEntry(
            source="owner/repo",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={
                "claude-code": manifest_mod.AgentPlacement(
                    path="~/.claude/skills/my-skill",
                    link_mode="clone",
                    scope="global",
                )
            },
        )
        return mf

    def test_napoln_error_outputs_and_counts_error(
        self, manifest_with_skill, monkeypatch, tmp_path
    ):
        errors = []

        def capture_error(msg, **_kwargs):
            errors.append(msg)

        monkeypatch.setattr("napoln.commands.install.output.error", capture_error)
        monkeypatch.setattr(
            "napoln.commands.install.store.ensure_stored",
            lambda *_a, **_k: (_ for _ in ()).throw(NapolnError("store missing")),
        )

        synced, error_count = _sync_manifest(manifest_with_skill, "global", False)
        assert error_count == 1

    def test_placement_error_outputs_and_counts_error(
        self, manifest_with_skill, monkeypatch, tmp_path
    ):
        errors = []

        def capture_error(msg, **_kwargs):
            errors.append(msg)

        monkeypatch.setattr("napoln.commands.install.output.error", capture_error)
        monkeypatch.setattr(
            "napoln.commands.install.store.ensure_stored",
            lambda *_a, **_k: tmp_path / "store",
        )
        monkeypatch.setattr(
            "napoln.commands.install.linker.restore_placement",
            lambda *_a, **_k: (_ for _ in ()).throw(PlacementError("placement failed")),
        )

        synced, error_count = _sync_manifest(manifest_with_skill, "global", False)
        assert error_count == 1
        assert any("Failed to restore" in e for e in errors)

    def test_type_error_propagates(self, manifest_with_skill, monkeypatch, tmp_path):
        """Programming bugs must not be swallowed."""
        monkeypatch.setattr(
            "napoln.commands.install.store.ensure_stored",
            lambda *_a, **_k: tmp_path / "store",
        )
        monkeypatch.setattr(
            "napoln.commands.install.linker.restore_placement",
            lambda *_a, **_k: (_ for _ in ()).throw(TypeError("programming bug")),
        )

        with pytest.raises(TypeError, match="programming bug"):
            _sync_manifest(manifest_with_skill, "global", False)
