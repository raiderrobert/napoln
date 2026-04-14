"""Integration tests for the napoln CLI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from napoln.cli import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def isolated_env(tmp_path):
    """Create an isolated environment for CLI tests."""
    home = tmp_path / "home"
    home.mkdir()
    napoln_home = home / ".napoln"

    # Create agent directories so auto-detect works
    (home / ".claude").mkdir()

    env = {
        "HOME": str(home),
        "NAPOLN_HOME": str(napoln_home),
        "NAPOLN_TELEMETRY": "off",
    }

    return home, napoln_home, env


@pytest.fixture
def local_skill(tmp_path):
    """Create a local skill for testing."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        '---\nname: test-skill\ndescription: A test skill.\n'
        'metadata:\n  version: "1.0.0"\n---\n\n# Test Skill\n\nHello.\n'
    )
    return skill_dir


class TestVersionCommand:
    def test_version(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "napoln" in result.output
        assert "0.1.0" in result.output


class TestHelpCommand:
    def test_help(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "agent skills" in result.output.lower()

    def test_add_help(self, runner):
        result = runner.invoke(app, ["add", "--help"])
        assert result.exit_code == 0
        assert "source" in result.output.lower()


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
        result = runner.invoke(
            app, ["add", str(local_skill), "--agents", "claude-code"], env=env
        )

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


class TestRemoveCommand:
    def test_remove_installed(self, runner, isolated_env, local_skill):
        home, napoln_home, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["remove", "test-skill"], env=env)

        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_remove_not_installed(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        # Create empty manifest
        (napoln_home).mkdir(parents=True, exist_ok=True)

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


class TestStatusCommand:
    def test_status_empty(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        (napoln_home).mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["status"], env=env)
        assert result.exit_code == 0

    def test_status_with_skills(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["status"], env=env)

        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_status_json(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["status", "--json"], env=env)

        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "test-skill" in data


class TestDiffCommand:
    def test_diff_clean(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["diff", "test-skill"], env=env)

        assert result.exit_code == 0
        assert "no local modifications" in result.output.lower()

    def test_diff_modified(self, runner, isolated_env, local_skill):
        home, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)

        # Modify the placement
        skill_md = home / ".claude" / "skills" / "test-skill" / "SKILL.md"
        skill_md.write_text(skill_md.read_text() + "\n## Custom Addition\n")

        result = runner.invoke(app, ["diff", "test-skill"], env=env)
        assert result.exit_code == 0


class TestDoctorCommand:
    def test_doctor_healthy(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["doctor"], env=env)

        # Check output mentions checks
        assert "✓" in result.output or "integrity" in result.output.lower()

    def test_doctor_json(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["doctor", "--json"], env=env)

        import json
        # Output may contain both human-readable and JSON
        # Find the JSON part
        output = result.output
        assert "checks_passed" in output


class TestSyncCommand:
    def test_sync_in_sync(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["sync"], env=env)

        assert result.exit_code == 0
        assert "in sync" in result.output.lower()


class TestInstallCommand:
    def test_install_is_sync_alias(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["install"], env=env)

        assert result.exit_code == 0


class TestGcCommand:
    def test_gc_nothing_to_collect(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["gc"], env=env)

        assert result.exit_code == 0
        assert "No unreferenced" in result.output

    def test_gc_dry_run(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["gc", "--dry-run"], env=env)

        assert result.exit_code == 0
        assert "Dry run" in result.output


class TestConfigCommand:
    def test_config_show(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        # First do an add to create config
        runner.invoke(app, ["add", str(local_skill)], env=env)
        result = runner.invoke(app, ["config"], env=env)
        assert result.exit_code == 0

    def test_config_set(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(
            app, ["config", "set", "telemetry.enabled", "false"], env=env
        )
        assert result.exit_code == 0
        assert "Set" in result.output


class TestTelemetryCommand:
    def test_telemetry_status(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["telemetry", "status"], env=env)
        assert result.exit_code == 0
        assert "disabled" in result.output.lower() or "enabled" in result.output.lower()

    def test_telemetry_show_data(self, runner, isolated_env):
        _, napoln_home, env = isolated_env
        napoln_home.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["telemetry", "show-data"], env=env)
        assert result.exit_code == 0
        assert "command" in result.output


class TestListCommand:
    def test_list_local(self, runner, isolated_env, local_skill):
        _, _, env = isolated_env
        result = runner.invoke(app, ["list", str(local_skill.parent)], env=env)
        assert result.exit_code == 0
