"""Step definitions for first_run.feature."""

from __future__ import annotations

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


@scenario("../features/first_run.feature", "Registry identifiers are not yet available")
def test_registry_not_available():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("no agents are installed", target_fixture="env")
def no_agents(napoln_env: NapolnTestEnv):
    return napoln_env


@given("napoln has never been run")
def fresh_napoln(napoln_env: NapolnTestEnv):
    assert not napoln_env.napoln_home.exists()


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln add with a valid local skill", target_fixture="result_env")
def run_add_local(env: NapolnTestEnv, cli_runner: CliRunner):
    skill_path = env.create_local_skill()
    env.result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    return env


@when("I run napoln add with a valid local skill and no agents", target_fixture="result_env")
def run_add_no_agents(env: NapolnTestEnv, cli_runner: CliRunner, monkeypatch):
    skill_path = env.create_local_skill()
    monkeypatch.setattr("napoln.core.agents._check_on_path", lambda cmd: False)
    env.result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    return env


@when(
    parsers.parse('I run napoln add with a bare name "{name}"'),
    target_fixture="result_env",
)
def run_add_bare_name(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", name], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the napoln home directory is created")
def napoln_home_exists(result_env: NapolnTestEnv):
    assert result_env.napoln_home.is_dir()


@then("the skill is stored in the content-addressed store")
def skill_in_store(result_env: NapolnTestEnv):
    store = result_env.napoln_home / "store"
    skill_dirs = [d for d in store.iterdir() if d.is_dir()] if store.exists() else []
    assert len(skill_dirs) >= 1


@then("the skill is placed in the Claude Code skills directory")
def skill_in_claude(result_env: NapolnTestEnv):
    skills_dir = result_env.home / ".claude" / "skills"
    assert skills_dir.exists()
    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert any(d.name == "test-skill" for d in skill_dirs)
