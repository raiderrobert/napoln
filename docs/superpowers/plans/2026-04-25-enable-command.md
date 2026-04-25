# napoln enable Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `napoln enable <agent>` command that extends already-installed skills to additional agents without re-downloading.

**Architecture:** New `enable.py` command module that reads from existing manifests, filters skills not yet placed for the target agent, and uses interactive pickers. Reuses existing `linker.place_skill` and `manifest` infrastructure.

**Tech Stack:** typer CLI, existing `prompts.py` pickers, existing `manifest.py`, existing `linker.py`

---

## File Structure

- **Create:** `src/napoln/commands/enable.py`
- **Modify:** `src/napoln/cli.py` (add enable command)
- **Create:** `tests/unit/test_enable.py`
- **Create:** `tests/integration/test_enable.py` (optional)

---

## Task 1: Create enable.py Command Module

**Files:**
- Create: `src/napoln/commands/enable.py`

- [ ] **Step 1: Write the command module**

```python
"""napoln enable — Extend installed skills to additional agents."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from napoln import output
from napoln.core import agents as agents_mod
from napoln.core import linker, manifest, store
from napoln.core.home import get_napoln_home
from napoln.prompts import SkillChoice, pick_agents, pick_skills


def _get_skills_to_enable(
    mf: manifest.Manifest,
    agent_id: str,
) -> list[manifest.SkillEntry]:
    """Return skills not yet placed for the given agent."""
    skills = []
    for name, entry in mf.skills.items():
        if agent_id not in entry.agents:
            skills.append(entry)
    return skills


def _place_skill_for_agent(
    skill_entry: manifest.SkillEntry,
    agent_config: agents_mod.AgentConfig,
    napoln_home: Path,
    home: Path,
    scope: str,
    project_root: Path | None,
) -> bool:
    """Place a single skill for an agent. Returns True on success."""
    # Get store path
    store_path = napoln_home / "store" / skill_entry.source.replace("/", "_")
    # Find the actual versioned directory
    version_prefix = skill_entry.version + "-"
    for child in store_path.iterdir():
        if child.is_dir() and child.name.startswith(version_prefix):
            store_path = child
            break
    else:
        output.warning(f"Store entry not found for '{skill_entry.source}'")
        return False

    # Get target path
    target_path = agent_config.skill_path(home, skill_entry.source.split("/")[-1], scope, project_root)

    # Place
    try:
        link_mode = linker.place_skill(store_path, target_path)
        linker.write_provenance(
            target_path,
            skill_entry.source,
            skill_entry.version,
            skill_entry.store_hash,
            link_mode,
        )
        return True
    except Exception as e:
        output.error(f"Failed to place skill: {e}")
        return False


def run_enable(
    agent_ids: list[str] | None,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the enable command.

    Args:
        agent_ids: Specific agent IDs to enable, or None to pick interactively.
        scope: "global" or "project".
        project_root: Project root for project scope.

    Returns:
        Exit code (0=success, 1=error).
    """
    import os

    napoln_home = get_napoln_home()
    home = Path(os.environ.get("HOME", Path.home()))

    # Determine which agents to enable
    if agent_ids:
        # Validate agent IDs
        for aid in agent_ids:
            if aid not in agents_mod.AGENTS:
                output.error(f"Unknown agent: {aid}. Available: {', '.join(agents_mod.AGENTS.keys())}")
                return 1
        target_agents = [agents_mod.AGENTS[aid] for aid in agent_ids]
    else:
        # Interactive agent picker
        available = agents_mod.detect_agents(home, project_root, scope)
        if not available:
            output.error("No agents detected. Install an agent first.")
            return 1

        selected = pick_agents(available)
        if selected is None:
            return 1  # User cancelled
        if not selected:
            output.info("No agents selected.")
            return 0
        target_agents = cast(list[agents_mod.AgentConfig], selected)

    # Load manifest
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if not mf.skills:
        output.info("No skills installed.")
        return 0

    # Process each agent
    for agent in target_agents:
        skills_to_enable = _get_skills_to_enable(mf, agent.id)

        if not skills_to_enable:
            output.success(f"All skills already enabled for {agent.display_name}")
            continue

        output.info(f"Found {len(skills_to_enable)} skills. Select skills to enable for {agent.display_name}:")

        # Build picker choices
        choices = [
            SkillChoice(
                name=name,
                description=entry.source,
                path=Path(entry.source),
            )
            for name, entry in mf.skills.items()
            if agent.id not in entry.agents
        ]

        selected = pick_skills(choices)
        if not selected:
            output.info(f"No skills selected for {agent.display_name}")
            continue

        # Place selected skills
        for choice in selected:
            skill_entry = mf.skills[choice.name]
            success = _place_skill_for_agent(
                skill_entry, agent, napoln_home, home, scope, project_root
            )
            if success:
                output.success(f"Enabled '{choice.name}' for {agent.display_name}")
                # Update manifest
                from napoln.core.manifest import AgentPlacement
                skill_entry.agents[agent.id] = AgentPlacement(
                    path=str(agent.skill_path(home, choice.name, scope, project_root)),
                    link_mode="clone",  # Will be updated by place_skill
                    scope=scope,
                )

        # Write manifest
        manifest.write_manifest(mf, manifest_path)

    return 0
```

- [ ] **Step 2: Commit**

```bash
git add src/napoln/commands/enable.py
git commit -m "feat: add napoln enable command"
```

---

## Task 2: Add enable Command to CLI

**Files:**
- Modify: `src/napoln/cli.py`

- [ ] **Step 1: Add enable command to cli.py**

Add after the `setup` command definition (around line 200):

```python
# ─── enable ──────────────────────────────────────────────────────────────────


@app.command()
def enable(
    agent: Annotated[
        Optional[str],
        typer.Argument(help="Agent to enable skills for (e.g., hermes, claude-code)."),
    ] = None,
    project: Annotated[
        bool, typer.Option("--project", "-p", help="Enable skills in project scope.")
    ] = False,
) -> None:
    """Extend installed skills to additional agents."""
    from napoln.commands.enable import run_enable

    agent_ids = [agent] if agent else None
    scope = "project" if project else "global"
    project_root = Path.cwd() if project else None

    exit_code = run_enable(
        agent_ids=agent_ids,
        scope=scope,
        project_root=project_root,
    )
    raise typer.Exit(code=exit_code)
```

- [ ] **Step 2: Commit**

```bash
git add src/napoln/cli.py
git commit -m "feat: add enable command to CLI"
```

---

## Task 3: Write Unit Tests

**Files:**
- Create: `tests/unit/test_enable.py`

- [ ] **Step 1: Write unit tests**

```python
"""Tests for napoln.commands.enable."""

import pytest
from pathlib import Path

from napoln.commands.enable import _get_skills_to_enable, run_enable
from napoln.core import manifest as manifest_mod


class TestGetSkillsToEnable:
    """Filter skills not yet placed for an agent."""

    def test_no_skills(self):
        """Empty manifest returns empty list."""
        mf = manifest_mod.Manifest()
        result = _get_skills_to_enable(mf, "hermes")
        assert result == []

    def test_all_enabled(self):
        """Skill already placed for agent is filtered out."""
        mf = manifest_mod.Manifest()
        mf.skills["test-skill"] = manifest_mod.SkillEntry(
            source="owner/repo",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={"hermes": manifest_mod.AgentPlacement(
                path="/home/.hermes/skills/test-skill",
                link_mode="clone",
                scope="global",
            )},
        )
        result = _get_skills_to_enable(mf, "hermes")
        assert result == []

    def test_some_enabled(self):
        """Skills not placed for agent are returned."""
        mf = manifest_mod.Manifest()
        mf.skills["skill-a"] = manifest_mod.SkillEntry(
            source="owner/repo",
            version="1.0.0",
            store_hash="abc123",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={"claude-code": manifest_mod.AgentPlacement(
                path="/home/.claude/skills/skill-a",
                link_mode="clone",
                scope="global",
            )},
        )
        mf.skills["skill-b"] = manifest_mod.SkillEntry(
            source="other/repo",
            version="2.0.0",
            store_hash="def456",
            installed="2024-01-01T00:00:00Z",
            updated="2024-01-01T00:00:00Z",
            agents={},  # Not placed for anyone
        )
        result = _get_skills_to_enable(mf, "hermes")
        assert len(result) == 2
        names = {e.source for e in result}
        assert "owner/repo" in names
        assert "other/repo" in names


class TestRunEnable:
    """Integration tests for run_enable."""

    def test_unknown_agent(self, tmp_path, monkeypatch):
        """Unknown agent ID returns error."""
        # Mock environment
        monkeypatch.setenv("HOME", str(tmp_path))
        # Mock napoln home
        nap_home = tmp_path / ".napoln"
        nap_home.mkdir()
        monkeypatch.setattr(
            "napoln.commands.enable.get_napoln_home",
            lambda: nap_home,
        )

        exit_code = run_enable(agent_ids=["nonexistent-agent"])
        assert exit_code == 1

    def test_no_skills_installed(self, tmp_path, monkeypatch):
        """Empty manifest returns success."""
        monkeypatch.setenv("HOME", str(tmp_path))
        nap_home = tmp_path / ".napoln"
        nap_home.mkdir()
        monkeypatch.setattr(
            "napoln.commands.enable.get_napoln_home",
            lambda: nap_home,
        )

        exit_code = run_enable(agent_ids=["hermes"])
        assert exit_code == 0
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/test_enable.py -v`
Expected: Tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_enable.py
git commit -m "test: add unit tests for enable command"
```

---

## Task 4: Run Full Test Suite

- [ ] **Step 1: Run full check**

Run: `just check`
Expected: All checks pass, all tests pass

- [ ] **Step 2: Final commit if needed**

```bash
git push
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Create `enable.py` command module |
| 2 | Add enable command to CLI |
| 3 | Write unit tests |
| 4 | Run full test suite |

---

## Spec Coverage Check

- [x] `napoln enable <agent>` - implemented in Task 1-2
- [x] `napoln enable` (no agent) - pick_agents integration in run_enable
- [x] `--project` flag - scope parameter implemented
- [x] Skip already-placed skills - `_get_skills_to_enable` filters them
- [x] Interactive picker - uses `pick_skills`
- [x] Update manifest - manifest updated after placement

## Type Consistency Check

- `run_enable(agent_ids, scope, project_root)` matches CLI call signature
- `AgentConfig.id` used for manifest agent tracking
- `manifest.AgentPlacement` used for manifest updates
