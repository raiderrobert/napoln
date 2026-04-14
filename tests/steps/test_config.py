"""Step definitions for config.feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/config.feature", "Show config")
def test_config_show():
    pass


@scenario("../features/config.feature", "Doctor reports healthy state")
def test_config_doctor():
    pass


@scenario("../features/config.feature", "GC with nothing to collect")
def test_config_gc():
    pass


@scenario("../features/config.feature", "GC dry run")
def test_config_gc_dry():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given("napoln is initialized")
def napoln_initialized(env: NapolnTestEnv, cli_runner: CliRunner):
    # Add a skill to trigger initialization
    skill_path = env.create_local_skill("init-skill")
    cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)


@given(parsers.parse('a skill "{name}" is installed'))
def skill_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name)
    cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln config", target_fixture="result_env")
def run_config(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["config"], env=env.env_vars)
    return env


@when("I run napoln config doctor", target_fixture="result_env")
def run_doctor(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["config", "doctor"], env=env.env_vars)
    return env


@when("I run napoln config gc", target_fixture="result_env")
def run_gc(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["config", "gc"], env=env.env_vars)
    return env


@when("I run napoln config gc --dry-run", target_fixture="result_env")
def run_gc_dry(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["config", "gc", "--dry-run"], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output


@then("the output contains checks passed")
def output_has_checks(result_env: NapolnTestEnv):
    assert "✓" in result_env.result.output or "integrity" in result_env.result.output.lower()


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code
