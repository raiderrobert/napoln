"""Tests for napoln.commands.add — initialization logic."""

from __future__ import annotations

import tomllib

from napoln.commands.add import _ensure_initialized


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
