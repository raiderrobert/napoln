"""BDD-specific fixtures for napoln feature tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


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

    def create_local_skill(
        self, name: str = "test-skill", version: str = "1.0.0",
        body: str = "# Test Skill\n\nTest body.\n",
    ) -> Path:
        skill_dir = self.tmp_path / "local-skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A test skill.\n"
            f'metadata:\n  version: "{version}"\n---\n\n{body}'
        )
        self.skill_dir = skill_dir
        return skill_dir

    def create_updated_skill(
        self, name: str = "test-skill", version: str = "2.0.0",
    ) -> Path:
        """Create a new version of an existing skill."""
        skill_dir = self.tmp_path / "local-skills-v2" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A test skill.\n"
            f'metadata:\n  version: "{version}"\n---\n\n# Test Skill V2\n\nUpdated.\n'
        )
        return skill_dir


@pytest.fixture
def napoln_env(tmp_path) -> NapolnTestEnv:
    return NapolnTestEnv(tmp_path)


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
