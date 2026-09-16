"""Step definitions for add.feature."""

from __future__ import annotations

import subprocess
import tomllib

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


@scenario("../features/add.feature", "Add all skills from a subdirectory of a multi-bundle repo")
def test_add_subdir_all():
    pass


@scenario("../features/add.feature", "Add a named skill from a subdirectory of a multi-bundle repo")
def test_add_subdir_named():
    pass


@scenario("../features/add.feature", "Add from a subdirectory that has no skills")
def test_add_subdir_missing():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────
# "Claude Code is installed" is in conftest.


@given("a local skill exists at a test path")
def local_skill_exists(env: NapolnTestEnv):
    env.create_local_skill()


@given(parsers.parse('a skill "{name}" is already installed'))
def skill_already_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    assert result.exit_code == 0, result.output


@given(parsers.parse('a cached git repo "{source}" with bundles "{bundle_a}" and "{bundle_b}"'))
def cached_bundle_repo(env: NapolnTestEnv, source: str, bundle_a: str, bundle_b: str):
    owner, repo = source.split("/")
    cache_dir = env.napoln_home / "cache"
    clone_dir = cache_dir / f"{owner}-{repo}"
    for bundle in (bundle_a, bundle_b):
        bundle_name, names = bundle.split(":")
        for name in names.split(","):
            skill_dir = clone_dir / bundle_name / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: A test skill.\n"
                f'metadata:\n  version: "1.0.0"\n---\n\n# {name}\n'
            )
    git_env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        "HOME": str(env.home),
    }
    for cmd in (["git", "init", "-q"], ["git", "add", "."], ["git", "commit", "-qm", "init"]):
        subprocess.run(cmd, cwd=clone_dir, check=True, env=git_env, capture_output=True)
    (cache_dir / f".{owner}-{repo}.last-fetch").touch()


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse('I run napoln add "{source}" with --all'), target_fixture="result_env")
def run_add_source_all(env: NapolnTestEnv, source: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", source, "--all"], env=env.env_vars)
    return env


@when(
    parsers.parse('I run napoln add "{source}" with --skill "{name}"'),
    target_fixture="result_env",
)
def run_add_source_skill(env: NapolnTestEnv, source: str, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", source, "--skill", name], env=env.env_vars)
    return env


@when("I run napoln add with the local skill", target_fixture="result_env")
def run_add(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    return env


@when("I run napoln add with dry run", target_fixture="result_env")
def run_add_dry(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir), "--dry-run"], env=env.env_vars)
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
def run_add_project(env: NapolnTestEnv, cli_runner: CliRunner, monkeypatch):
    # Sandbox cwd so --project doesn't write into the real repo.
    project = env.tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    env.result = cli_runner.invoke(
        app,
        ["add", str(env.skill_dir), "--project", "--agents", "claude-code"],
        env=env.env_vars,
    )
    return env


# ─── Then ────────────────────────────────────────────────────────────────────
# "the exit code is" and "the output contains" are in conftest.


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
    mf_path = result_env.napoln_home / "manifest.toml"
    assert mf_path.exists()
    data = tomllib.loads(mf_path.read_text())
    assert "test-skill" in data.get("skills", {})


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


@then("the project manifest contains the skill")
def project_manifest_has_skill(result_env: NapolnTestEnv):
    project = result_env.tmp_path / "project"
    mf_path = project / ".napoln" / "manifest.toml"
    assert mf_path.exists(), f"Expected project manifest at {mf_path}"
    data = tomllib.loads(mf_path.read_text())
    assert "test-skill" in data.get("skills", {})


def _manifest_skills(env: NapolnTestEnv) -> dict:
    mf_path = env.napoln_home / "manifest.toml"
    assert mf_path.exists()
    return tomllib.loads(mf_path.read_text()).get("skills", {})


@then(parsers.parse('the manifest contains skills "{names}"'))
def manifest_has_skills(result_env: NapolnTestEnv, names: str):
    skills = _manifest_skills(result_env)
    for name in names.split(","):
        assert name in skills, f"{name} missing from {sorted(skills)}"


@then(parsers.parse('the manifest does not contain skills "{names}"'))
def manifest_lacks_skills(result_env: NapolnTestEnv, names: str):
    skills = _manifest_skills(result_env)
    for name in names.split(","):
        assert name not in skills, f"{name} unexpectedly in {sorted(skills)}"


@then(parsers.parse('the manifest source for "{name}" is "{source}"'))
def manifest_source_is(result_env: NapolnTestEnv, name: str, source: str):
    assert _manifest_skills(result_env)[name]["source"] == source
