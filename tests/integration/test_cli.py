"""Integration tests for the napoln CLI."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from napoln.cli import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Create an isolated environment for CLI tests."""
    home = tmp_path / "home"
    home.mkdir()
    napoln_home = home / ".napoln"

    # Create agent directories so auto-detect works
    (home / ".claude").mkdir()

    # Chdir into a sandbox so commands that resolve project scope via Path.cwd()
    # (e.g. `add --project`) don't write into the real repo.
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    env = {
        "HOME": str(home),
        "NAPOLN_HOME": str(napoln_home),
    }

    return home, napoln_home, env


@pytest.fixture
def local_skill(tmp_path):
    """Create a local skill for testing."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: A test skill.\n"
        'metadata:\n  version: "1.0.0"\n---\n\n# Test Skill\n\nHello.\n'
    )
    return skill_dir


class TestVersionCommand:
    def test_version(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "napoln" in result.output
        # Check for semver-like pattern (e.g. "0.2.0", "1.0.0+abc123")
        import re

        assert re.search(r"\d+\.\d+\.\d+", result.output)


class TestHelpCommand:
    def test_help(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "agent skills" in result.output.lower()

    def test_help_shows_seven_commands(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("add", "remove", "upgrade", "list", "install", "init", "config"):
            assert cmd in result.output

    def test_help_hides_cut_commands(self, runner):
        result = runner.invoke(app, ["--help"])
        for cmd in ("status", "diff", "resolve", "sync", "doctor", "gc", "telemetry"):
            # These should NOT be in top-level help
            # (doctor and gc are subcommands of config)
            assert f"  {cmd} " not in result.output or cmd in ("doctor", "gc")

    def test_add_help(self, runner):
        result = runner.invoke(app, ["add", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--skill" in result.output
        assert "--project" in result.output

    def test_no_completion_in_help(self, runner):
        result = runner.invoke(app, ["--help"])
        assert "--install-completion" not in result.output
        assert "--show-completion" not in result.output


class TestAddCommand:
    def test_add_local_skill(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        result = runner.invoke(app, ["add", str(local_skill)], env=env)

        assert result.exit_code == 0
        assert "Added" in result.output or "test-skill" in result.output

        # Verify manifest was created
        assert (napoln_home / "manifest.toml").exists()

        # Verify store entry
        store = napoln_home / "store" / "test-skill"
        assert store.exists()
        assert len(list(store.iterdir())) >= 1

        # Verify placement
        assert (home / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()

    def test_add_dry_run(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        result = runner.invoke(app, ["add", str(local_skill), "--dry-run"], env=env)

        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Would" in result.output

        # Nothing should be written
        assert not (napoln_home / "manifest.toml").exists()

    def test_add_with_explicit_agent(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        result = runner.invoke(app, ["add", str(local_skill), "--agents", "claude-code"], env=env)

        assert result.exit_code == 0
        assert (home / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()

    def test_add_idempotent(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["add", str(local_skill)], env=env)

        assert result.exit_code == 0
        assert "already installed" in result.output

    def test_add_registry_not_available(self, runner, isolated_env):
        _, _, env = isolated_env
        result = runner.invoke(app, ["add", "my-skill"], env=env)
        assert result.exit_code == 1
        assert "not yet available" in result.output

    def test_add_with_project(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        result = runner.invoke(
            app, ["add", str(local_skill), "--project", "--agents", "claude-code"], env=env
        )
        assert result.exit_code == 0


class TestRemoveCommand:
    def test_remove_installed(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["remove", "test-skill"], env=env)

        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_remove_not_installed(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)

        import tomli_w

        (napoln_home / "manifest.toml").write_text(
            tomli_w.dumps({"napoln": {"schema": 1}, "skills": {}})
        )

        result = runner.invoke(app, ["remove", "nonexistent"], env=env)
        assert result.exit_code == 0
        assert "not installed" in result.output

    def test_remove_dry_run(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["remove", "test-skill", "--dry-run"], env=env)

        assert result.exit_code == 0
        assert "Dry run" in result.output
        # Skill should still be placed
        assert (home / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()


class TestListCommand:
    def test_list_empty(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["list", "--global"], env=env)
        assert result.exit_code == 0
        assert "No skills installed" in result.output

    def test_list_with_skills(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["list", "--global"], env=env)

        assert result.exit_code == 0
        assert "test-skill" in result.output
        assert "1.0.0" in result.output

    def test_list_json(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["list", "--global", "--json"], env=env)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "global" in data
        assert "test-skill" in data["global"]


class TestInstallCommand:
    def test_install_all_in_sync(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["install", "--global"], env=env)

        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_install_no_manifests(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["install", "--global"], env=env)
        assert result.exit_code == 0

    def test_install_dry_run(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["install", "--global", "--dry-run"], env=env)
        assert result.exit_code == 0


class TestInitCommand:
    def test_init_with_name(self, runner, tmp_path):
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["init", "my-skill"])
            assert result.exit_code == 0
            assert (tmp_path / "my-skill" / "SKILL.md").exists()
        finally:
            os.chdir(old_cwd)

    def test_init_refuses_overwrite(self, runner, tmp_path):
        import os

        (tmp_path / "my-skill").mkdir()
        (tmp_path / "my-skill" / "SKILL.md").write_text("# Existing\n")
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["init", "my-skill"])
            assert result.exit_code == 1
            assert "already exists" in result.output
        finally:
            os.chdir(old_cwd)

    def test_init_help(self, runner):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Scaffold" in result.output


class TestConfigCommand:
    def test_config_show(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["config"], env=env)
        assert result.exit_code == 0
        assert "Home" in result.output

    def test_config_set(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["config", "set", "napoln.default_scope", "project"], env=env)
        assert result.exit_code == 0
        assert "Set" in result.output

    def test_config_doctor(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["config", "doctor"], env=env)
        assert "✓" in result.output or "integrity" in result.output.lower()

    def test_config_doctor_json(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["config", "doctor", "--json"], env=env)
        assert "checks_passed" in result.output

    def test_config_gc_nothing(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["config", "gc"], env=env)
        assert result.exit_code == 0
        assert "No unreferenced" in result.output

    def test_config_gc_dry_run(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["config", "gc", "--dry-run"], env=env)
        assert result.exit_code == 0
        assert "Dry run" in result.output
