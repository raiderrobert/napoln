"""Step definitions for health_check.feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/health_check.feature", "Doctor reports healthy state")
def test_doctor_healthy():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given(parsers.parse('a skill "{name}" is installed'))
def skill_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name)
    cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln doctor", target_fixture="result_env")
def run_doctor(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["doctor"], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the output contains checks passed")
def output_has_checks(result_env: NapolnTestEnv):
    # Doctor shows ✓ for passed checks
    assert "✓" in result_env.result.output or "integrity" in result_env.result.output.lower()


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code
