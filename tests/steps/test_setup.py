"""Step definitions for setup.feature."""

from __future__ import annotations

import tomllib

import tomli_w
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/setup.feature", "Setup persists default agents to config")
def test_setup_persists_defaults():
    pass


@scenario("../features/setup.feature", "Add respects configured default agents")
def test_add_respects_defaults():
    pass


@scenario(
    "../features/setup.feature",
    "Add hints at setup when defaults are unset and multiple agents detected",
)
def test_add_hints_at_setup():
    pass


@scenario("../features/setup.feature", "Setup with no agents detected fails with guidance")
def test_setup_no_agents():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code and Cursor are installed", target_fixture="env")
def claude_and_cursor(napoln_env: NapolnTestEnv, monkeypatch):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    (napoln_env.home / ".cursor").mkdir(parents=True, exist_ok=True)
    # Don't let pi/codex on the real PATH leak into detection.
    monkeypatch.setattr("napoln.core.agents._check_on_path", lambda cmd: False)
    return napoln_env


@given("no agents are installed", target_fixture="env")
def no_agents(napoln_env: NapolnTestEnv, monkeypatch):
    monkeypatch.setattr("napoln.core.agents._check_on_path", lambda cmd: False)
    return napoln_env


@given(parsers.parse('default_agents is configured to "{ids}"'))
def configure_defaults(env: NapolnTestEnv, ids: str):
    env.napoln_home.mkdir(parents=True, exist_ok=True)
    config_path = env.napoln_home / "config.toml"
    data = {"napoln": {"default_agents": [a.strip() for a in ids.split(",")]}}
    config_path.write_text(tomli_w.dumps(data))


@given("default_agents is not configured")
def no_defaults(env: NapolnTestEnv):
    config_path = env.napoln_home / "config.toml"
    assert not config_path.exists()


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse('I run napoln setup with selection "{ids}"'), target_fixture="result_env")
def run_setup_with_selection(env: NapolnTestEnv, ids: str, cli_runner: CliRunner, monkeypatch):
    from napoln.core import agents as agents_mod

    selected_ids = [a.strip() for a in ids.split(",")]
    selected = [agents_mod.AGENTS[aid] for aid in selected_ids]
    # Bypass the questionary prompt: return the chosen agents directly.
    monkeypatch.setattr(
        "napoln.commands.setup.pick_agents", lambda available, preselected_ids=None: selected
    )
    env.result = cli_runner.invoke(app, ["setup"], env=env.env_vars)
    return env


@when("I run napoln setup non-interactively", target_fixture="result_env")
def run_setup_noninteractive(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["setup"], env=env.env_vars)
    return env


@when("I run napoln add with a valid local skill", target_fixture="result_env")
def run_add(env: NapolnTestEnv, cli_runner: CliRunner):
    skill_path = env.create_local_skill()
    env.result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then(parsers.parse('the config contains default_agents "{ids}"'))
def config_has_defaults(result_env: NapolnTestEnv, ids: str):
    config_path = result_env.napoln_home / "config.toml"
    assert config_path.exists(), "config.toml was not written"
    data = tomllib.loads(config_path.read_text())
    expected = [a.strip() for a in ids.split(",")]
    assert data["napoln"]["default_agents"] == expected


@then("the skill is placed only for Claude Code")
def placed_only_for_claude(result_env: NapolnTestEnv):
    claude_skill = result_env.home / ".claude" / "skills" / "test-skill"
    cursor_skill = result_env.home / ".cursor" / "skills" / "test-skill"
    assert claude_skill.exists(), f"Expected Claude placement at {claude_skill}"
    assert not cursor_skill.exists(), f"Did not expect Cursor placement at {cursor_skill}"


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    combined = result_env.result.output + (result_env.result.stderr or "")
    assert text in combined, f"Expected '{text}' in:\n{combined}"


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code, (
        f"exit={result_env.result.exit_code} output={result_env.result.output!r}"
    )
