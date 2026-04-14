"""Step definitions for init.feature."""

from __future__ import annotations

import os

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/init.feature", "Init with a name creates a subdirectory")
def test_init_with_name():
    pass


@scenario("../features/init.feature", "Init refuses to overwrite existing SKILL.md")
def test_init_refuses_overwrite():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given(parsers.parse('a SKILL.md already exists at "{name}"'), target_fixture="init_env")
def skill_md_exists(napoln_env: NapolnTestEnv, name: str):
    target = napoln_env.tmp_path / "workdir" / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_text("# Existing\n")
    return napoln_env


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse('I run napoln init with name "{name}"'), target_fixture="result_env")
def run_init(napoln_env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    # Use a workdir so we control where the file is created
    workdir = napoln_env.tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    old_cwd = os.getcwd()
    try:
        os.chdir(workdir)
        napoln_env.result = cli_runner.invoke(app, ["init", name], env=napoln_env.env_vars)
    finally:
        os.chdir(old_cwd)
    return napoln_env


# ─── Then ────────────────────────────────────────────────────────────────────


@then(parsers.parse('"{path}" exists'))
def file_exists(result_env: NapolnTestEnv, path: str):
    full_path = result_env.tmp_path / "workdir" / path
    assert full_path.exists(), f"Expected {full_path} to exist"


@then(parsers.parse('the SKILL.md contains "{text}"'))
def skill_md_contains(result_env: NapolnTestEnv, text: str):
    # Find the SKILL.md that was created
    workdir = result_env.tmp_path / "workdir"
    skill_files = list(workdir.rglob("SKILL.md"))
    assert skill_files, "No SKILL.md found"
    content = skill_files[0].read_text()
    assert text in content, f"Expected '{text}' in:\n{content}"


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code
