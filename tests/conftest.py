"""Shared fixtures for napoln tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    """Create a temporary home directory."""
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def napoln_home(tmp_home: Path) -> Path:
    """Create a temporary napoln home directory."""
    nh = tmp_home / ".napoln"
    nh.mkdir()
    (nh / "store").mkdir()
    (nh / "cache").mkdir()
    return nh


@pytest.fixture
def env_vars(tmp_home: Path, napoln_home: Path) -> dict[str, str]:
    """Environment variables for isolated test runs."""
    return {
        "HOME": str(tmp_home),
        "NAPOLN_HOME": str(napoln_home),
        "NAPOLN_TELEMETRY": "off",
    }


@pytest.fixture
def skill_builder(tmp_path: Path):
    """Factory for creating test skill directories."""

    def build(
        name: str = "test-skill",
        description: str = "A test skill.",
        version: str = "1.0.0",
        body: str = "# Test Skill\n\nTest body.\n",
        extra_files: dict[str, str] | None = None,
    ) -> Path:
        skill_dir = tmp_path / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        frontmatter = (
            f"---\nname: {name}\ndescription: {description}\n"
            f'metadata:\n  version: "{version}"\n---\n\n{body}'
        )
        (skill_dir / "SKILL.md").write_text(frontmatter)

        if extra_files:
            for path, content in extra_files.items():
                f = skill_dir / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content)

        return skill_dir

    return build


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"
