"""Step definitions for first_run.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/first_run.feature", "First run bootstraps napoln and installs a skill")
def test_first_run_bootstrap():
    pass


@scenario("../features/first_run.feature", "First run with no agents detected")
def test_first_run_no_agents():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="napoln_env_with_claude")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given("no agents are installed", target_fixture="napoln_env_no_agents")
def no_agents(napoln_env: NapolnTestEnv):
    return napoln_env


@given("napoln has never been run")
def fresh_napoln(napoln_env: NapolnTestEnv):
    assert not napoln_env.napoln_home.exists()


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln add with a valid local skill", target_fixture="run_result")
def run_add_local(napoln_env_with_claude: NapolnTestEnv, cli_runner: CliRunner):
    env = napoln_env_with_claude
    skill_path = env.create_local_skill()
    env.result = cli_runner.invoke(
        app, ["add", str(skill_path)], env=env.env_vars
    )
    return env


@when("I run napoln add with a valid local skill and no agents", target_fixture="run_result")
def run_add_no_agents(napoln_env_no_agents: NapolnTestEnv, cli_runner: CliRunner):
    env = napoln_env_no_agents
    skill_path = env.create_local_skill()
    env.result = cli_runner.invoke(
        app, ["add", str(skill_path)], env=env.env_vars
    )
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the napoln home directory is created")
def napoln_home_exists(run_result: NapolnTestEnv):
    assert run_result.napoln_home.is_dir()


@then("the skill is stored in the content-addressed store")
def skill_in_store(run_result: NapolnTestEnv):
    store = run_result.napoln_home / "store"
    # Should have at least one skill directory
    skill_dirs = [d for d in store.iterdir() if d.is_dir()] if store.exists() else []
    assert len(skill_dirs) >= 1


@then("the skill is placed in the Claude Code skills directory")
def skill_in_claude(run_result: NapolnTestEnv):
    skills_dir = run_result.home / ".claude" / "skills"
    assert skills_dir.exists()
    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert any(d.name == "test-skill" for d in skill_dirs)


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(run_result: NapolnTestEnv, code: int):
    assert run_result.result.exit_code == code


@then(parsers.parse('the output contains "{text}"'))
def output_contains(run_result: NapolnTestEnv, text: str):
    assert text in run_result.result.output
