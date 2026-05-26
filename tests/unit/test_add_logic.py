"""Tests for napoln.commands.add — initialization logic."""

from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from napoln.commands.add import (
    _ensure_initialized,
    _install_single_skill,
    _pick_from_multi_skill_repo,
)
from napoln.core import manifest as manifest_mod
from napoln.core.resolver import ResolvedSource, SourceType
from napoln.errors import ManifestError, MultipleSkillsError, PlacementError, StoreError


class TestEnsureInitialized:
    def test_creates_directory_structure(self, tmp_path):
        home = tmp_path / ".napoln"
        _ensure_initialized(home)

        assert home.is_dir()
        assert (home / "store").is_dir()
        assert (home / "cache").is_dir()

    def test_writes_default_config(self, tmp_path):
        home = tmp_path / ".napoln"
        _ensure_initialized(home)

        config_path = home / "config.toml"
        assert config_path.exists()
        data = tomllib.loads(config_path.read_text())
        assert data["napoln"]["default_agents"] == []
        assert data["napoln"]["default_scope"] == "global"
        assert data["telemetry"]["enabled"] is False

    def test_does_not_overwrite_existing_config(self, tmp_path):
        home = tmp_path / ".napoln"
        _ensure_initialized(home)

        config_path = home / "config.toml"
        config_path.write_text('[napoln]\ndefault_scope = "project"\n')

        _ensure_initialized(home)

        data = tomllib.loads(config_path.read_text())
        assert data["napoln"]["default_scope"] == "project"

    def test_creates_nested_parent_dirs(self, tmp_path):
        home = tmp_path / "deep" / "nested" / ".napoln"
        _ensure_initialized(home)

        assert home.is_dir()
        assert (home / "store").is_dir()


class TestInstallSingleSkillExceptions:
    """Regression: broad except Exception swallows programming bugs."""

    @pytest.fixture
    def resolved(self, tmp_path):
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: test-skill\ndescription: x\nmetadata:\n  version: "1.0.0"\n---\n# Hello'
        )
        return ResolvedSource(
            source_type=SourceType.LOCAL,
            source_id=str(skill_dir),
            skill_dir=skill_dir,
            version="1.0.0",
        )

    @pytest.fixture
    def agent_config(self):
        cfg = MagicMock()
        cfg.id = "claude-code"
        cfg.display_name = "Claude Code"
        return cfg

    @pytest.fixture
    def manifest_and_path(self, tmp_path):
        path = tmp_path / "manifest.toml"
        mf = manifest_mod.Manifest()
        return mf, path

    def test_store_error_outputs_and_returns_1(
        self, resolved, agent_config, manifest_and_path, monkeypatch
    ):
        mf, path = manifest_and_path
        errors = []

        def capture_error(msg, **_kwargs):
            errors.append(msg)

        monkeypatch.setattr("napoln.commands.add.output.error", capture_error)
        monkeypatch.setattr(
            "napoln.commands.add.store.store_skill",
            lambda *_a, **_k: (_ for _ in ()).throw(StoreError("store failed")),
        )

        code = _install_single_skill(
            resolved,
            "test-skill",
            [agent_config],
            Path.home(),
            Path.home(),
            "global",
            None,
            mf,
            path,
            False,
        )
        assert code == 1
        assert any("Failed to store skill" in e for e in errors)

    def test_store_type_error_propagates(
        self, resolved, agent_config, manifest_and_path, monkeypatch
    ):
        """Programming bugs must not be swallowed."""
        mf, path = manifest_and_path

        monkeypatch.setattr(
            "napoln.commands.add.store.store_skill",
            lambda *_a, **_k: (_ for _ in ()).throw(TypeError("programming bug")),
        )

        with pytest.raises(TypeError, match="programming bug"):
            _install_single_skill(
                resolved,
                "test-skill",
                [agent_config],
                Path.home(),
                Path.home(),
                "global",
                None,
                mf,
                path,
                False,
            )

    def test_placement_error_outputs_and_returns_1(
        self, resolved, agent_config, manifest_and_path, monkeypatch, tmp_path
    ):
        mf, path = manifest_and_path
        errors = []

        def capture_error(msg, **_kwargs):
            errors.append(msg)

        monkeypatch.setattr("napoln.commands.add.output.error", capture_error)
        monkeypatch.setattr(
            "napoln.commands.add.store.store_skill",
            lambda *_a, **_k: (tmp_path / "store", "hash123"),
        )
        monkeypatch.setattr(
            "napoln.commands.add.linker.place_skill",
            lambda *_a, **_k: (_ for _ in ()).throw(PlacementError("placement failed")),
        )

        code = _install_single_skill(
            resolved,
            "test-skill",
            [agent_config],
            Path.home(),
            Path.home(),
            "global",
            None,
            mf,
            path,
            False,
        )
        assert code == 1
        assert any("Failed to place" in e for e in errors)

    def test_placement_type_error_propagates(
        self, resolved, agent_config, manifest_and_path, monkeypatch, tmp_path
    ):
        """Programming bugs must not be swallowed."""
        mf, path = manifest_and_path

        monkeypatch.setattr(
            "napoln.commands.add.store.store_skill",
            lambda *_a, **_k: (tmp_path / "store", "hash123"),
        )
        monkeypatch.setattr(
            "napoln.commands.add.linker.place_skill",
            lambda *_a, **_k: (_ for _ in ()).throw(TypeError("programming bug")),
        )

        with pytest.raises(TypeError, match="programming bug"):
            _install_single_skill(
                resolved,
                "test-skill",
                [agent_config],
                Path.home(),
                Path.home(),
                "global",
                None,
                mf,
                path,
                False,
            )


class TestPickFromMultiSkillRepoExceptions:
    """Regression: broad except Exception swallows programming bugs."""

    def test_manifest_error_continues(self, tmp_path, monkeypatch):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        skill_dir = repo_dir / "skill-a"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        err = MultipleSkillsError(repo_dir, [skill_dir])
        parsed = MagicMock()
        parsed.host = "github.com"
        parsed.owner = "owner"
        parsed.repo = "repo"
        parsed.version = ""

        monkeypatch.setattr(
            "napoln.commands.add.manifest.read_manifest",
            lambda *_a, **_k: (_ for _ in ()).throw(ManifestError("bad manifest")),
        )
        monkeypatch.setattr("napoln.commands.add.pick_skills", lambda _choices: [])

        result = _pick_from_multi_skill_repo(err, parsed, "owner/repo", None, tmp_path / ".napoln")
        assert result is None

    def test_manifest_type_error_propagates(self, tmp_path, monkeypatch):
        """Programming bugs must not be swallowed."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        skill_dir = repo_dir / "skill-a"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        err = MultipleSkillsError(repo_dir, [skill_dir])
        parsed = MagicMock()
        parsed.host = "github.com"
        parsed.owner = "owner"
        parsed.repo = "repo"
        parsed.version = ""

        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "manifest.toml").write_text("[napoln]\nschema = 1\n", encoding="utf-8")

        monkeypatch.setattr(
            "napoln.commands.add.manifest.read_manifest",
            lambda *_a, **_k: (_ for _ in ()).throw(TypeError("programming bug")),
        )

        with pytest.raises(TypeError, match="programming bug"):
            _pick_from_multi_skill_repo(err, parsed, "owner/repo", None, napoln_home)
