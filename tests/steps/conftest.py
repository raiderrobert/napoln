"""BDD-specific fixtures and shared step definitions for napoln feature tests."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import tomli_w
from pytest_bdd import given, parsers, then
from typer.testing import CliRunner

from napoln.cli import app


class NapolnTestEnv:
    """Isolated napoln environment for BDD tests."""

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.result = None
        self.napoln_home = self.home / ".napoln"
        self.env_vars = {
            "HOME": str(self.home),
            "NAPOLN_HOME": str(self.napoln_home),
            "NAPOLN_TELEMETRY": "off",
        }
        self.skill_dir: Path | None = None
        self._version_counter = 0
        self._project_skill_placement: Path | None = None

    def create_local_skill(
        self,
        name: str = "test-skill",
        version: str = "1.0.0",
        body: str = "# Test Skill\n\nTest body.\n",
        extra_files: dict[str, str] | None = None,
    ) -> Path:
        """Create a skill in a unique tmp directory."""
        self._version_counter += 1
        skill_dir = self.tmp_path / f"skills-{self._version_counter}" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A test skill.\n"
            f'metadata:\n  version: "{version}"\n---\n\n{body}'
        )
        if extra_files:
            for rel, content in extra_files.items():
                f = skill_dir / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content)
        self.skill_dir = skill_dir
        return skill_dir

    def create_updated_skill(
        self,
        name: str = "test-skill",
        version: str = "2.0.0",
        body: str = "# Test Skill V2\n\nUpdated.\n",
        extra_files: dict[str, str] | None = None,
    ) -> Path:
        """Create a new version and point the manifest source at it."""
        skill_dir = self.create_local_skill(name, version, body, extra_files)
        self.update_manifest_source(name, str(skill_dir))
        return skill_dir

    def update_manifest_source(self, skill_name: str, new_source: str) -> None:
        """Point the manifest's source for a skill to a new local path."""
        mf_path = self.napoln_home / "manifest.toml"
        data = tomllib.loads(mf_path.read_text())
        data["skills"][skill_name]["source"] = new_source
        mf_path.write_text(tomli_w.dumps(data))

    def claude_skill_path(self, name: str) -> Path:
        return self.home / ".claude" / "skills" / name


@pytest.fixture
def napoln_env(tmp_path) -> NapolnTestEnv:
    return NapolnTestEnv(tmp_path)


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


# ─── Shared Given steps ──────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv, monkeypatch):
    """Set up Claude Code as the only detected agent.

    Monkeypatches _check_on_path so agents on the developer's real PATH
    (pi, codex, hermes) don't leak into the test.
    """
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("napoln.core.agents._check_on_path", lambda cmd: False)
    return napoln_env


@given(parsers.parse('a skill "{name}" is installed'))
def skill_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    assert result.exit_code == 0, result.output


# ─── Shared Then steps ───────────────────────────────────────────────────────


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code, (
        f"Expected exit {code}, got {result_env.result.exit_code}\n"
        f"Output:\n{result_env.result.output}"
    )


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output, f"Expected '{text}' in:\n{result_env.result.output}"
