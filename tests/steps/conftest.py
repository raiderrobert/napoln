"""BDD-specific fixtures for napoln feature tests."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import tomli_w
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
        self._version_counter = 0

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
