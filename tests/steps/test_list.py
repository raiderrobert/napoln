"""Step definitions for list.feature."""

from __future__ import annotations

import json
import os

from pytest_bdd import scenario, then, when
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
# "Claude Code is installed" and 'a skill "{name}" is installed' are in conftest.


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln list", target_fixture="result_env")
def run_list(env: NapolnTestEnv, cli_runner: CliRunner):
    old_cwd = os.getcwd()
    try:
        os.chdir(env.home)
        env.result = cli_runner.invoke(app, ["list"], env=env.env_vars)
    finally:
        os.chdir(old_cwd)
    return env


@when("I run napoln list --json", target_fixture="result_env")
def run_list_json(env: NapolnTestEnv, cli_runner: CliRunner):
    old_cwd = os.getcwd()
    try:
        os.chdir(env.home)
        env.result = cli_runner.invoke(app, ["list", "--json"], env=env.env_vars)
    finally:
        os.chdir(old_cwd)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────
# "the exit code is" and "the output contains" are in conftest.


@then('the output is valid JSON with "test-skill" in global')
def output_valid_json_with_skill(result_env: NapolnTestEnv):
    data = json.loads(result_env.result.output)
    assert "global" in data
    assert "test-skill" in data["global"]
