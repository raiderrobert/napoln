"""Step definitions for upgrade.feature — three-way merge cases."""

from __future__ import annotations

import tomllib

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv

# ─── Base content used across all merge scenarios ─────────────────────────────
# 10 distinct lines so merge regions are unambiguous for git merge-file.

BASE_BODY = """\
# Test Skill

## Overview

This is the overview section.

## Steps

1. First step
2. Second step
3. Third step
"""

# ─── Scenarios ────────────────────────────────────────────────────────────────


@scenario("../features/upgrade.feature", "Fast-forward when no local changes")
def test_fast_forward():
    pass


@scenario("../features/upgrade.feature",
          "Clean merge when local and upstream changes do not overlap")
def test_clean_merge():
    pass


@scenario("../features/upgrade.feature",
          "Conflict when local and upstream change the same lines")
def test_conflict():
    pass


@scenario("../features/upgrade.feature", "Supporting files replaced if unchanged")
def test_script_replaced():
    pass


@scenario("../features/upgrade.feature",
          "Supporting files kept when locally modified")
def test_script_kept():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given(parsers.parse('a skill "{name}" is installed at version "{version}"'))
def skill_installed(env: NapolnTestEnv, name: str, version: str, cli_runner: CliRunner):
    env.create_local_skill(name, version, BASE_BODY)
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    assert env.result.exit_code == 0, env.result.output


@given(parsers.parse(
    'a skill "{name}" with a script is installed at version "{version}"'
))
def skill_with_script_installed(
    env: NapolnTestEnv, name: str, version: str, cli_runner: CliRunner,
):
    env.create_local_skill(
        name, version, BASE_BODY,
        extra_files={"scripts/run.sh": "#!/bin/bash\necho v1\n"},
    )
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    assert env.result.exit_code == 0, env.result.output


# ── placement state ──────────────────────────────────────────────────────────


@given("the Claude Code placement is unmodified")
def placement_unmodified(env: NapolnTestEnv):
    pass


@given("the Claude Code placement has local changes at the end")
def placement_local_end(env: NapolnTestEnv):
    skill_md = env.claude_skill_path("test-skill") / "SKILL.md"
    skill_md.write_text(skill_md.read_text() + "\n## Custom Section\n\nAdded by the user.\n")


@given("the Claude Code placement has local changes on line 5")
def placement_local_line5(env: NapolnTestEnv):
    skill_md = env.claude_skill_path("test-skill") / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text().replace(
            "This is the overview section.",
            "This is the LOCAL overview.",
        )
    )


@given("the script in the Claude Code placement is unmodified")
def script_unmodified(env: NapolnTestEnv):
    pass


@given("the script in the Claude Code placement has local changes")
def script_modified(env: NapolnTestEnv):
    script = env.claude_skill_path("test-skill") / "scripts" / "run.sh"
    script.write_text("#!/bin/bash\necho local-customized\n")


# ── upstream versions ────────────────────────────────────────────────────────


@given('upstream has released version "2.0.0" with a new section')
def upstream_new_section(env: NapolnTestEnv):
    env.create_updated_skill(
        "test-skill", "2.0.0",
        body=BASE_BODY + "\n## Performance\n\nNew upstream section.\n",
    )


@given('upstream has released version "2.0.0" with changes at the beginning')
def upstream_changes_beginning(env: NapolnTestEnv):
    env.create_updated_skill(
        "test-skill", "2.0.0",
        body=BASE_BODY.replace("# Test Skill", "# Test Skill (Improved)"),
    )


@given('upstream has released version "2.0.0" with different changes on line 5')
def upstream_changes_line5(env: NapolnTestEnv):
    env.create_updated_skill(
        "test-skill", "2.0.0",
        body=BASE_BODY.replace(
            "This is the overview section.",
            "This is the UPSTREAM overview.",
        ),
    )


@given('upstream has released version "2.0.0" with an updated script')
def upstream_updated_script(env: NapolnTestEnv):
    env.create_updated_skill(
        "test-skill", "2.0.0",
        body=BASE_BODY,
        extra_files={"scripts/run.sh": "#!/bin/bash\necho v2-upstream\n"},
    )


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse("I run napoln upgrade {name}"), target_fixture="result_env")
def run_upgrade(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["upgrade", name], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the Claude Code placement contains the new upstream content")
def placement_has_upstream(result_env: NapolnTestEnv):
    content = (result_env.claude_skill_path("test-skill") / "SKILL.md").read_text()
    assert "Performance" in content or "2.0.0" in content


@then("the Claude Code placement does not contain conflict markers")
def no_conflict_markers(result_env: NapolnTestEnv):
    content = (result_env.claude_skill_path("test-skill") / "SKILL.md").read_text()
    assert "<<<<<<<" not in content


@then(parsers.parse('the manifest version is "{version}"'))
def manifest_version(result_env: NapolnTestEnv, version: str):
    data = tomllib.loads((result_env.napoln_home / "manifest.toml").read_text())
    assert data["skills"]["test-skill"]["version"] == version


@then("the Claude Code placement contains both local and upstream changes")
def has_both_changes(result_env: NapolnTestEnv):
    content = (result_env.claude_skill_path("test-skill") / "SKILL.md").read_text()
    assert "Custom Section" in content, f"Missing local changes:\n{content}"
    assert "(Improved)" in content, f"Missing upstream changes:\n{content}"


@then("the Claude Code placement contains conflict markers")
def has_conflict_markers(result_env: NapolnTestEnv):
    content = (result_env.claude_skill_path("test-skill") / "SKILL.md").read_text()
    assert "<<<<<<<" in content and "=======" in content and ">>>>>>>" in content, (
        f"Expected conflict markers:\n{content}"
    )


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output, (
        f"Expected '{text}' in:\n{result_env.result.output}"
    )


@then("the script in the Claude Code placement matches the new upstream")
def script_matches_upstream(result_env: NapolnTestEnv):
    script = result_env.claude_skill_path("test-skill") / "scripts" / "run.sh"
    assert "v2-upstream" in script.read_text()


@then("the script in the Claude Code placement retains local changes")
def script_retains_local(result_env: NapolnTestEnv):
    script = result_env.claude_skill_path("test-skill") / "scripts" / "run.sh"
    assert "local-customized" in script.read_text()


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code, (
        f"Expected exit {code}, got {result_env.result.exit_code}\n"
        f"Output:\n{result_env.result.output}"
    )
