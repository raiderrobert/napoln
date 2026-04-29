"""Step definitions for remove.feature."""

from __future__ import annotations

import tomllib

import tomli_w
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/remove.feature", "Remove an installed skill")
def test_remove_installed():
    pass


@scenario("../features/remove.feature", "Remove a skill that is not installed")
def test_remove_not_installed():
    pass


@scenario("../features/remove.feature", "Remove with dry run")
def test_remove_dry_run():
    pass


@scenario("../features/remove.feature", "Remove multiple skills at once")
def test_remove_multiple():
    pass


@scenario("../features/remove.feature", "Remove by source with --from-source")
def test_remove_from_source():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────
# "Claude Code is installed" and 'a skill "{name}" is installed' are in conftest.


@given("no skills are installed")
def no_skills(env: NapolnTestEnv):
    env.napoln_home.mkdir(parents=True, exist_ok=True)
    (env.napoln_home / "manifest.toml").write_text(
        tomli_w.dumps({"napoln": {"schema": 1}, "skills": {}})
    )


@given(parsers.parse('a skill "{name}" is installed from "{source}"'))
def skill_installed_from_source(env: NapolnTestEnv, name: str, source: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    assert result.exit_code == 0, result.output

    mf_path = env.napoln_home / "manifest.toml"
    data = tomllib.loads(mf_path.read_text())
    data["skills"][name]["source"] = source
    mf_path.write_text(tomli_w.dumps(data))


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse("I run napoln remove {args}"), target_fixture="result_env")
def run_remove(env: NapolnTestEnv, args: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["remove", *args.split()], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────
# "the exit code is" and "the output contains" are in conftest.


@then("the skill is no longer placed for Claude Code")
def skill_not_placed(result_env: NapolnTestEnv):
    skill_dir = result_env.home / ".claude" / "skills" / "test-skill"
    assert not skill_dir.exists()


@then("the skill is still placed for Claude Code")
def skill_still_placed(result_env: NapolnTestEnv):
    skill_dir = result_env.home / ".claude" / "skills" / "test-skill"
    assert skill_dir.exists()
    assert (skill_dir / "SKILL.md").exists()


@then(parsers.parse('"{name}" is no longer placed for Claude Code'))
def named_skill_not_placed(result_env: NapolnTestEnv, name: str):
    skill_dir = result_env.home / ".claude" / "skills" / name
    assert not skill_dir.exists()
