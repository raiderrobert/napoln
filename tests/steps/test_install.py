"""Step definitions for install.feature."""

from __future__ import annotations

import shutil

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/install.feature", "Install from local path")
def test_install_local():
    pass


@scenario("../features/install.feature", "Install with dry run")
def test_install_dry_run():
    pass


@scenario("../features/install.feature", "Install re-fetches skills when store is empty")
def test_install_refetch_empty_store():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given("a local skill exists at a test path")
def local_skill_exists(env: NapolnTestEnv):
    env.create_local_skill()


@given("the skill was previously added")
def skill_previously_added(env: NapolnTestEnv, cli_runner: CliRunner):
    result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    assert result.exit_code == 0


@given("the store is empty")
def store_is_empty(env: NapolnTestEnv):
    store_dir = env.napoln_home / "store"
    if store_dir.exists():
        shutil.rmtree(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)


@given("skill placements are removed")
def placements_removed(env: NapolnTestEnv):
    skills_dir = env.home / ".claude" / "skills"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln add with the local skill", target_fixture="result_env")
def run_add(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    return env


@when("I run napoln add with dry run", target_fixture="result_env")
def run_add_dry(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir), "--dry-run"], env=env.env_vars)
    return env


@when("I run napoln install", target_fixture="result_env")
def run_install(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["install"], env=env.env_vars)
    return env


@when("I run napoln install --global", target_fixture="result_env")
def run_install_global(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["install", "--global"], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the skill is stored in the content-addressed store")
def skill_stored(result_env: NapolnTestEnv):
    store = result_env.napoln_home / "store"
    assert store.exists()
    assert any(d.is_dir() for d in store.iterdir())


@then("the skill is placed in the Claude Code skills directory")
def skill_placed(result_env: NapolnTestEnv):
    skills = result_env.home / ".claude" / "skills"
    assert any(d.name == "test-skill" for d in skills.iterdir() if d.is_dir())


@then("the manifest contains the skill")
def manifest_has_skill(result_env: NapolnTestEnv):
    import tomllib

    mf_path = result_env.napoln_home / "manifest.toml"
    assert mf_path.exists()
    data = tomllib.loads(mf_path.read_text())
    assert "test-skill" in data.get("skills", {})


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code


@then("no skills are stored")
def no_skills_stored(result_env: NapolnTestEnv):
    store = result_env.napoln_home / "store"
    if store.exists():
        # May have bootstrap skill
        skill_dirs = [d for d in store.iterdir() if d.is_dir()]
        assert all(d.name == "napoln-manage" for d in skill_dirs) or len(skill_dirs) == 0
    # Or store doesn't exist at all, which is fine


@then("no placements are created")
def no_placements(result_env: NapolnTestEnv):
    skills = result_env.home / ".claude" / "skills"
    if skills.exists():
        # May have bootstrap skill
        placed = [d for d in skills.iterdir() if d.is_dir() and d.name != "napoln-manage"]
        assert len(placed) == 0


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output
