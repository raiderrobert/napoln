"""Step definitions for sync.feature (napoln install)."""

from __future__ import annotations

import shutil
from pathlib import Path

import tomli_w
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/sync.feature", "Install when everything is in sync")
def test_install_in_sync():
    pass


@scenario("../features/sync.feature", "Install with no manifests")
def test_install_no_manifests():
    pass


@scenario("../features/sync.feature", "Install with dry run")
def test_install_dry_run():
    pass


@scenario("../features/sync.feature", "Install restores skills from project manifest")
def test_install_restore_from_manifest():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv, monkeypatch):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("napoln.core.agents._check_on_path", lambda cmd: False)
    return napoln_env


@given(parsers.parse('a skill "{name}" is installed'))
def skill_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    assert result.exit_code == 0, result.output


@given("napoln home exists but has no manifest")
def napoln_home_no_manifest(env: NapolnTestEnv):
    env.napoln_home.mkdir(parents=True, exist_ok=True)


@given(
    parsers.parse('a project manifest references "{name}" from a local source'),
)
def project_manifest_with_skill(
    env: NapolnTestEnv, name: str, monkeypatch,
):
    from napoln.core.hasher import hash_skill

    skill_path = env.create_local_skill(name)
    content_hash = hash_skill(skill_path)

    # Set up project directory and chdir into it
    project = env.tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    skill_placement = env.home / ".claude" / "skills" / name
    manifest_dir = project / ".napoln"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "napoln": {"schema": 1},
        "skills": {
            name: {
                "source": str(skill_path),
                "version": "1.0.0",
                "store_hash": content_hash,
                "installed": "2026-01-01T00:00:00Z",
                "updated": "2026-01-01T00:00:00Z",
                "agents": {
                    "claude-code": {
                        "path": str(skill_placement),
                        "link_mode": "copy",
                        "scope": "project",
                    }
                },
            }
        },
    }
    (manifest_dir / "manifest.toml").write_text(tomli_w.dumps(manifest_data))
    # Stash for assertions
    env._project_skill_placement = skill_placement


@given("the store is empty")
def store_is_empty(env: NapolnTestEnv):
    store = env.napoln_home / "store"
    if store.exists():
        shutil.rmtree(store)


@given("no placements exist")
def no_placements(env: NapolnTestEnv):
    skills_dir = env.home / ".claude" / "skills"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse("I run napoln install {args}"), target_fixture="result_env")
def run_install(env: NapolnTestEnv, args: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["install", *args.split()], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the skill is placed in the Claude Code skills directory")
def skill_placed(result_env: NapolnTestEnv):
    placement = getattr(result_env, "_project_skill_placement", None)
    if placement:
        assert placement.exists(), f"Expected placement at {placement}"
        assert (placement / "SKILL.md").exists()
    else:
        skills_dir = result_env.home / ".claude" / "skills"
        assert skills_dir.exists()
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        assert len(skill_dirs) >= 1


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output, (
        f"Expected '{text}' in:\n{result_env.result.output}"
    )


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code, (
        f"Expected exit {code}, got {result_env.result.exit_code}\n"
        f"Output:\n{result_env.result.output}"
    )
