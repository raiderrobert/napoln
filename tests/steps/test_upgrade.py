"""Step definitions for upgrade.feature."""

from __future__ import annotations

import tomllib

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/upgrade.feature", "Fast-forward when no local changes")
def test_fast_forward():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given(parsers.parse('a skill "{name}" is installed'))
def skill_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name, version="1.0.0")
    env.result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)


@given("the placement is unmodified")
def placement_unmodified(env: NapolnTestEnv):
    pass  # Default state after install


@given("a new version of the skill exists locally")
def new_version_exists(env: NapolnTestEnv):
    # Create updated skill and modify source in manifest to point to it
    new_skill = env.create_updated_skill("test-skill", "2.0.0")

    # Update manifest source to point to new version
    mf_path = env.napoln_home / "manifest.toml"
    data = tomllib.loads(mf_path.read_text())
    data["skills"]["test-skill"]["source"] = str(new_skill)

    import tomli_w
    mf_path.write_text(tomli_w.dumps(data))


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse("I run napoln upgrade {name}"), target_fixture="result_env")
def run_upgrade(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["upgrade", name], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the placement is updated with the new version")
def placement_updated(result_env: NapolnTestEnv):
    skill_md = result_env.home / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert skill_md.exists()
    content = skill_md.read_text()
    assert "V2" in content or "2.0.0" in content


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code
