"""Step definitions for add.feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/add.feature", "Add from local path")
def test_add_local():
    pass


@scenario("../features/add.feature", "Add with dry run")
def test_add_dry_run():
    pass


@scenario("../features/add.feature", "Add the same skill twice is idempotent")
def test_add_idempotent():
    pass


@scenario("../features/add.feature", "Add with explicit agent flag")
def test_add_explicit_agent():
    pass


@scenario("../features/add.feature", "Add a registry identifier before registry is available")
def test_add_registry_not_available():
    pass


@scenario("../features/add.feature", "Add with project scope")
def test_add_project():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv, monkeypatch):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    # Sandbox the working directory so --project doesn't write into the real repo.
    project = napoln_env.tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    return napoln_env


@given("a local skill exists at a test path")
def local_skill_exists(env: NapolnTestEnv):
    env.create_local_skill()


@given(parsers.parse('a skill "{name}" is already installed'))
def skill_already_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    assert result.exit_code == 0, result.output


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln add with the local skill", target_fixture="result_env")
def run_add(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    return env


@when("I run napoln add with dry run", target_fixture="result_env")
def run_add_dry(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(
        app, ["add", str(env.skill_dir), "--dry-run"], env=env.env_vars
    )
    return env


@when("I run napoln add with the same skill again", target_fixture="result_env")
def run_add_again(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    return env


@when("I run napoln add with --agents claude-code", target_fixture="result_env")
def run_add_explicit_agent(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(
        app, ["add", str(env.skill_dir), "--agents", "claude-code"], env=env.env_vars
    )
    return env


@when(parsers.parse('I run napoln add with a bare name "{name}"'), target_fixture="result_env")
def run_add_bare_name(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", name], env=env.env_vars)
    return env


@when(
    "I run napoln add with --project --agents claude-code",
    target_fixture="result_env",
)
def run_add_project(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(
        app,
        ["add", str(env.skill_dir), "--project", "--agents", "claude-code"],
        env=env.env_vars,
    )
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
    assert result_env.result.exit_code == code, (
        f"Expected exit {code}, got {result_env.result.exit_code}\n"
        f"Output:\n{result_env.result.output}"
    )


@then("no skills are stored")
def no_skills_stored(result_env: NapolnTestEnv):
    store = result_env.napoln_home / "store"
    if store.exists():
        skill_dirs = [d for d in store.iterdir() if d.is_dir()]
        assert all(d.name == "napoln-manage" for d in skill_dirs) or len(skill_dirs) == 0


@then("no placements are created")
def no_placements(result_env: NapolnTestEnv):
    skills = result_env.home / ".claude" / "skills"
    if skills.exists():
        placed = [d for d in skills.iterdir() if d.is_dir() and d.name != "napoln-manage"]
        assert len(placed) == 0


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output, (
        f"Expected '{text}' in:\n{result_env.result.output}"
    )
