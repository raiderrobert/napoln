"""Step definitions for garbage_collection.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/garbage_collection.feature", "GC with nothing to collect")
def test_gc_nothing():
    pass


@scenario("../features/garbage_collection.feature", "GC dry run")
def test_gc_dry_run():
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


@when("I run napoln gc", target_fixture="result_env")
def run_gc(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["gc"], env=env.env_vars)
    return env


@when("I run napoln gc with dry run", target_fixture="result_env")
def run_gc_dry(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["gc", "--dry-run"], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code
