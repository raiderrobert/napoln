"""Tests for resolve_and_store in add.py."""

from __future__ import annotations

import pytest


@pytest.fixture
def _stored_skill(skill_builder, napoln_home):
    """Use resolve_and_store to store a local skill and return the result."""
    from napoln.core.resolver import resolve_and_store

    skill_dir = skill_builder(name="my-skill", version="1.0.0")
    return resolve_and_store(
        source=str(skill_dir),
        skill_name="my-skill",
        napoln_home=napoln_home,
    )


def test_resolve_and_store_returns_store_path(_stored_skill, napoln_home):
    store_path, content_hash = _stored_skill
    assert store_path.exists()
    assert store_path.is_dir()
    assert (store_path / "SKILL.md").exists()
    assert napoln_home / "store" in store_path.parents


def test_resolve_and_store_returns_content_hash(_stored_skill):
    _, content_hash = _stored_skill
    assert isinstance(content_hash, str)
    assert len(content_hash) > 0


def test_resolve_and_store_bundled_source(napoln_home):
    from napoln.core.resolver import resolve_and_store

    store_path, content_hash = resolve_and_store(
        source="bundled",
        skill_name="napoln-manage",
        napoln_home=napoln_home,
    )
    assert store_path.exists()
    assert (store_path / "SKILL.md").exists()


def test_resolve_and_store_bad_source(napoln_home):
    from napoln.core.resolver import resolve_and_store

    with pytest.raises(Exception):
        resolve_and_store(
            source="/nonexistent/path/to/nowhere",
            skill_name="ghost",
            napoln_home=napoln_home,
        )
