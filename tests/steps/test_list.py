"""Step definitions for list.feature."""

from __future__ import annotations

import json

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/list.feature", "List with no skills installed")
def test_list_empty():
    pass


@scenario("../features/list.feature", "List shows installed skills")
def test_list_shows_skills():
    pass


@scenario("../features/list.feature", "List with --json produces valid JSON")
def test_list_json():
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


@when("I run napoln list", target_fixture="result_env")
def run_list(env: NapolnTestEnv, cli_runner: CliRunner):
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(env.home)
        env.result = cli_runner.invoke(app, ["list"], env=env.env_vars)
    finally:
        os.chdir(old_cwd)
    return env


@when("I run napoln list --json", target_fixture="result_env")
def run_list_json(env: NapolnTestEnv, cli_runner: CliRunner):
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(env.home)
        env.result = cli_runner.invoke(app, ["list", "--json"], env=env.env_vars)
    finally:
        os.chdir(old_cwd)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code


@then(parsers.parse('the output is valid JSON with "{skill}" in global'))
def output_valid_json_with_skill(result_env: NapolnTestEnv, skill: str):
    data = json.loads(result_env.result.output)
    assert "global" in data
    assert skill in data["global"]
