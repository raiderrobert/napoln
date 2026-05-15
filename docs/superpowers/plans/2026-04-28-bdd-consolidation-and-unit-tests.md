# BDD Consolidation and Unit Test Backfill

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BDD the canonical behavioral spec for all CLI commands by eliminating duplication with integration tests, migrating unique integration behaviors into BDD, and backfilling unit tests for command orchestration logic.

**Architecture:** BDD features own all behavioral contracts — every user-facing workflow has a `.feature` file. Integration tests shrink to CLI surface tests only (help text, version, flag visibility). Unit tests cover pure functions extracted from command modules. The duplication between `tests/integration/test_cli.py` and `tests/steps/` is eliminated by deleting the integration side and adding missing scenarios to BDD.

**Tech Stack:** pytest, pytest-bdd, typer.testing.CliRunner, ruff

---

## File Structure

**Files to delete:**
- None. All existing BDD files stay.

**Files to modify:**
- `tests/features/first_run.feature` — add "registry not available" scenario
- `tests/steps/test_first_run.py` — add step definitions for new scenario
- `tests/features/install.feature` — rename concept to "add", add idempotent/explicit-agent/project scenarios
- `tests/steps/test_install.py` — add step definitions for new scenarios
- `tests/features/config.feature` — add `config set` and `doctor --json` scenarios
- `tests/steps/test_config.py` — add step definitions for new scenarios
- `tests/integration/test_cli.py` — delete everything except `TestVersionCommand` and `TestHelpCommand`
- `src/napoln/commands/config.py` — extract `_parse_config_value`
- `tests/unit/test_linker.py` — add `restore_placement` tests

**Files to create:**
- `tests/features/remove.feature` — 5 scenarios for the remove command
- `tests/steps/test_remove.py` — step definitions for remove
- `tests/features/sync.feature` — 4 scenarios for `napoln install` (the restore/sync command)
- `tests/steps/test_sync.py` — step definitions for sync
- `tests/unit/test_remove_logic.py` — unit tests for `_resolve_from_source`
- `tests/unit/test_list_logic.py` — unit tests for display helpers
- `tests/unit/test_config_logic.py` — unit tests for `_parse_config_value`
- `tests/unit/test_add_logic.py` — unit tests for `_ensure_initialized`

---

### Task 1: Create `remove.feature` and Step Definitions

The remove command has 7 integration tests and zero BDD coverage. These test important behaviors: basic remove, not-installed handling, dry run, multi-skill remove, and `--from-source` matching.

**Files:**
- Create: `tests/features/remove.feature`
- Create: `tests/steps/test_remove.py`

- [ ] **Step 1: Write the feature file**

Create `tests/features/remove.feature`:

```gherkin
Feature: Remove installed skills
  As a developer
  I want to remove skills I no longer need
  So that my agents only have relevant capabilities

  Scenario: Remove an installed skill
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln remove test-skill
    Then the output contains "Removed"
    And the skill is no longer placed for Claude Code
    And the exit code is 0

  Scenario: Remove a skill that is not installed
    Given Claude Code is installed
    And no skills are installed
    When I run napoln remove nonexistent
    Then the output contains "not installed"
    And the exit code is 0

  Scenario: Remove with dry run
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln remove test-skill --dry-run
    Then the output contains "Dry run"
    And the skill is still placed for Claude Code
    And the exit code is 0

  Scenario: Remove multiple skills at once
    Given Claude Code is installed
    And a skill "skill-one" is installed
    And a skill "skill-two" is installed
    When I run napoln remove skill-one skill-two
    Then "skill-one" is no longer placed for Claude Code
    And "skill-two" is no longer placed for Claude Code
    And the exit code is 0

  Scenario: Remove by source with --from-source
    Given Claude Code is installed
    And a skill "design-audit" is installed from "https://github.com/raiderrobert/flow"
    When I run napoln remove --from-source raiderrobert/flow
    Then "design-audit" is no longer placed for Claude Code
    And the exit code is 0
```

- [ ] **Step 2: Write the step definitions**

Create `tests/steps/test_remove.py`:

```python
"""Step definitions for remove.feature."""

from __future__ import annotations

import tomllib

import tomli_w
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/remove.feature", "Remove an installed skill")
def test_remove_installed():
    pass


@scenario("../features/remove.feature", "Remove a skill that is not installed")
def test_remove_not_installed():
    pass


@scenario("../features/remove.feature", "Remove with dry run")
def test_remove_dry_run():
    pass


@scenario("../features/remove.feature", "Remove multiple skills at once")
def test_remove_multiple():
    pass


@scenario("../features/remove.feature", "Remove by source with --from-source")
def test_remove_from_source():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env


@given(parsers.parse('a skill "{name}" is installed'))
def skill_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    skill_path = env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    assert result.exit_code == 0, result.output


@given("no skills are installed")
def no_skills(env: NapolnTestEnv):
    env.napoln_home.mkdir(parents=True, exist_ok=True)
    (env.napoln_home / "manifest.toml").write_text(
        tomli_w.dumps({"napoln": {"schema": 1}, "skills": {}})
    )


@given(parsers.parse('a skill "{name}" is installed from "{source}"'))
def skill_installed_from_source(
    env: NapolnTestEnv, name: str, source: str, cli_runner: CliRunner
):
    skill_path = env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(skill_path)], env=env.env_vars)
    assert result.exit_code == 0, result.output

    # Update manifest source to the specified URL
    mf_path = env.napoln_home / "manifest.toml"
    data = tomllib.loads(mf_path.read_text())
    data["skills"][name]["source"] = source
    mf_path.write_text(tomli_w.dumps(data))


# ─── When ────────────────────────────────────────────────────────────────────


@when(parsers.parse("I run napoln remove {args}"), target_fixture="result_env")
def run_remove(env: NapolnTestEnv, args: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["remove", *args.split()], env=env.env_vars)
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the skill is no longer placed for Claude Code")
def skill_not_placed(result_env: NapolnTestEnv):
    skill_dir = result_env.home / ".claude" / "skills" / "test-skill"
    assert not skill_dir.exists()


@then("the skill is still placed for Claude Code")
def skill_still_placed(result_env: NapolnTestEnv):
    skill_dir = result_env.home / ".claude" / "skills" / "test-skill"
    assert skill_dir.exists()
    assert (skill_dir / "SKILL.md").exists()


@then(parsers.parse('"{name}" is no longer placed for Claude Code'))
def named_skill_not_placed(result_env: NapolnTestEnv, name: str):
    skill_dir = result_env.home / ".claude" / "skills" / name
    assert not skill_dir.exists()


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
```

- [ ] **Step 3: Run the new BDD tests**

```bash
just test tests/steps/test_remove.py -v
```

Expected: All 5 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/features/remove.feature tests/steps/test_remove.py
git commit -m "test: add remove.feature BDD scenarios"
```

---

### Task 2: Create `sync.feature` for `napoln install`

The `napoln install` command (restore/sync from manifest) has 4 integration tests and no BDD coverage. The most important scenario is the lockfile use case: clone a repo with a manifest, run `napoln install --project`, and skills get restored from source.

Note: The existing `install.feature` confusingly tests `napoln add`, not `napoln install`. This task creates a new `sync.feature` for the actual install command. Task 3 will rename `install.feature` to `add.feature`.

**Files:**
- Create: `tests/features/sync.feature`
- Create: `tests/steps/test_sync.py`

- [ ] **Step 1: Write the feature file**

Create `tests/features/sync.feature`:

```gherkin
Feature: Sync skill placements from manifests
  As a developer joining a project
  I want to run napoln install to restore skills from the manifest
  So that I get the same skill setup as my teammates

  Scenario: Install when everything is in sync
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln install --global
    Then the output contains "up to date"
    And the exit code is 0

  Scenario: Install with no manifests
    Given Claude Code is installed
    And napoln home exists but has no manifest
    When I run napoln install --global
    Then the output contains "No manifests"
    And the exit code is 0

  Scenario: Install with dry run
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln install --global --dry-run
    Then the output contains "Dry run"
    And the exit code is 0

  Scenario: Install restores skills from project manifest
    Given Claude Code is installed
    And a project manifest references "test-skill" from a local source
    And the store is empty
    And no placements exist
    When I run napoln install --project
    Then the output contains "Restored"
    And the skill is placed in the Claude Code skills directory
    And the exit code is 0
```

- [ ] **Step 2: Write the step definitions**

Create `tests/steps/test_sync.py`:

```python
"""Step definitions for sync.feature (napoln install)."""

from __future__ import annotations

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
    target_fixture="project_env",
)
def project_manifest_with_skill(
    env: NapolnTestEnv, name: str, monkeypatch: "pytest.MonkeyPatch"
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
    env._project_skill_placement = skill_placement  # stash for assertions
    return env


@given("the store is empty")
def store_is_empty(env: NapolnTestEnv):
    store = env.napoln_home / "store"
    if store.exists():
        import shutil

        shutil.rmtree(store)


@given("no placements exist")
def no_placements(env: NapolnTestEnv):
    skills_dir = env.home / ".claude" / "skills"
    if skills_dir.exists():
        import shutil

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
```

- [ ] **Step 3: Run the new BDD tests**

```bash
just test tests/steps/test_sync.py -v
```

Expected: All 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/features/sync.feature tests/steps/test_sync.py
git commit -m "test: add sync.feature BDD scenarios for napoln install"
```

---

### Task 3: Enhance Existing BDD Features with Missing Scenarios

The existing BDD features are missing scenarios that only the integration tests cover. Add them.

**Files:**
- Modify: `tests/features/install.feature` (rename to `add.feature`)
- Modify: `tests/steps/test_install.py` (update path reference)
- Modify: `tests/features/first_run.feature`
- Modify: `tests/steps/test_first_run.py`
- Modify: `tests/features/config.feature`
- Modify: `tests/steps/test_config.py`

- [ ] **Step 1: Rename `install.feature` to `add.feature` and add scenarios**

The existing `install.feature` tests `napoln add`, not `napoln install`. Rename it and add the missing scenarios from integration tests.

```bash
mv tests/features/install.feature tests/features/add.feature
```

Replace `tests/features/add.feature` with:

```gherkin
Feature: Add a skill
  As a developer
  I want to install skills from local paths and git sources
  So that I can use them in my agents

  Scenario: Add from local path
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with the local skill
    Then the skill is stored in the content-addressed store
    And the skill is placed in the Claude Code skills directory
    And the manifest contains the skill
    And the exit code is 0

  Scenario: Add with dry run
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with dry run
    Then no skills are stored
    And no placements are created
    And the output contains "Dry run"
    And the exit code is 0

  Scenario: Add the same skill twice is idempotent
    Given Claude Code is installed
    And a skill "test-skill" is already installed
    When I run napoln add with the same skill again
    Then the output contains "already installed"
    And the exit code is 0

  Scenario: Add with explicit agent flag
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with --agents claude-code
    Then the skill is placed in the Claude Code skills directory
    And the exit code is 0

  Scenario: Add a registry identifier before registry is available
    Given Claude Code is installed
    When I run napoln add with a bare name "my-skill"
    Then the output contains "not yet available"
    And the exit code is 1

  Scenario: Add with project scope
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with --project --agents claude-code
    Then the exit code is 0
```

- [ ] **Step 2: Update `tests/steps/test_install.py` to match**

Replace the entire file with:

```python
"""Step definitions for add.feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from napoln.cli import app
from tests.steps.conftest import NapolnTestEnv


@scenario("../features/add.feature", "Add from local path")
def test_add_local():
    pass


@scenario("../features/add.feature", "Add with dry run")
def test_add_dry_run():
    pass


@scenario("../features/add.feature", "Add the same skill twice is idempotent")
def test_add_idempotent():
    pass


@scenario("../features/add.feature", "Add with explicit agent flag")
def test_add_explicit_agent():
    pass


@scenario("../features/add.feature", "Add a registry identifier before registry is available")
def test_add_registry_not_available():
    pass


@scenario("../features/add.feature", "Add with project scope")
def test_add_project():
    pass


# ─── Given ────────────────────────────────────────────────────────────────────


@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv, monkeypatch):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    # Sandbox the working directory so --project doesn't write into the real repo.
    project = napoln_env.tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    return napoln_env


@given("a local skill exists at a test path")
def local_skill_exists(env: NapolnTestEnv):
    env.create_local_skill()


@given(parsers.parse('a skill "{name}" is already installed'))
def skill_already_installed(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.create_local_skill(name)
    result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    assert result.exit_code == 0, result.output


# ─── When ────────────────────────────────────────────────────────────────────


@when("I run napoln add with the local skill", target_fixture="result_env")
def run_add(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    return env


@when("I run napoln add with dry run", target_fixture="result_env")
def run_add_dry(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(
        app, ["add", str(env.skill_dir), "--dry-run"], env=env.env_vars
    )
    return env


@when("I run napoln add with the same skill again", target_fixture="result_env")
def run_add_again(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", str(env.skill_dir)], env=env.env_vars)
    return env


@when("I run napoln add with --agents claude-code", target_fixture="result_env")
def run_add_explicit_agent(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(
        app, ["add", str(env.skill_dir), "--agents", "claude-code"], env=env.env_vars
    )
    return env


@when(parsers.parse('I run napoln add with a bare name "{name}"'), target_fixture="result_env")
def run_add_bare_name(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", name], env=env.env_vars)
    return env


@when(
    "I run napoln add with --project --agents claude-code",
    target_fixture="result_env",
)
def run_add_project(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(
        app,
        ["add", str(env.skill_dir), "--project", "--agents", "claude-code"],
        env=env.env_vars,
    )
    return env


# ─── Then ────────────────────────────────────────────────────────────────────


@then("the skill is stored in the content-addressed store")
def skill_stored(result_env: NapolnTestEnv):
    store = result_env.napoln_home / "store"
    assert store.exists()
    assert any(d.is_dir() for d in store.iterdir())


@then("the skill is placed in the Claude Code skills directory")
def skill_placed(result_env: NapolnTestEnv):
    skills = result_env.home / ".claude" / "skills"
    assert any(d.name == "test-skill" for d in skills.iterdir() if d.is_dir())


@then("the manifest contains the skill")
def manifest_has_skill(result_env: NapolnTestEnv):
    import tomllib

    mf_path = result_env.napoln_home / "manifest.toml"
    assert mf_path.exists()
    data = tomllib.loads(mf_path.read_text())
    assert "test-skill" in data.get("skills", {})


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int):
    assert result_env.result.exit_code == code, (
        f"Expected exit {code}, got {result_env.result.exit_code}\n"
        f"Output:\n{result_env.result.output}"
    )


@then("no skills are stored")
def no_skills_stored(result_env: NapolnTestEnv):
    store = result_env.napoln_home / "store"
    if store.exists():
        skill_dirs = [d for d in store.iterdir() if d.is_dir()]
        assert all(d.name == "napoln-manage" for d in skill_dirs) or len(skill_dirs) == 0


@then("no placements are created")
def no_placements(result_env: NapolnTestEnv):
    skills = result_env.home / ".claude" / "skills"
    if skills.exists():
        placed = [d for d in skills.iterdir() if d.is_dir() and d.name != "napoln-manage"]
        assert len(placed) == 0


@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str):
    assert text in result_env.result.output, (
        f"Expected '{text}' in:\n{result_env.result.output}"
    )
```

- [ ] **Step 3: Add `config set` and `doctor --json` scenarios to `config.feature`**

Append to `tests/features/config.feature`:

```gherkin

  Scenario: Set a config value
    Given Claude Code is installed
    And napoln is initialized
    When I run napoln config set napoln.default_scope project
    Then the output contains "Set"
    And the exit code is 0

  Scenario: Doctor with JSON output
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln config doctor --json
    Then the output contains "checks_passed"
    And the exit code is 0
```

- [ ] **Step 4: Add step definitions for the new config scenarios**

Add to `tests/steps/test_config.py` — new scenario declarations and when steps.

Add these scenario declarations after the existing ones:

```python
@scenario("../features/config.feature", "Set a config value")
def test_config_set():
    pass


@scenario("../features/config.feature", "Doctor with JSON output")
def test_config_doctor_json():
    pass
```

Add these when steps in the When section:

```python
@when(parsers.parse("I run napoln config set {key} {value}"), target_fixture="result_env")
def run_config_set(env: NapolnTestEnv, key: str, value: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["config", "set", key, value], env=env.env_vars)
    return env


@when("I run napoln config doctor --json", target_fixture="result_env")
def run_doctor_json(env: NapolnTestEnv, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["config", "doctor", "--json"], env=env.env_vars)
    return env
```

- [ ] **Step 5: Add "registry not available" scenario to first_run.feature**

Append to `tests/features/first_run.feature`:

```gherkin

  Scenario: Registry identifiers are not yet available
    Given Claude Code is installed
    When I run napoln add with a bare name "my-skill"
    Then the output contains "not yet available"
    And the exit code is 1
```

- [ ] **Step 6: Add step definitions for the new first_run scenario**

Add to `tests/steps/test_first_run.py` — the scenario declaration and required steps.

Add the scenario declaration:

```python
@scenario("../features/first_run.feature", "Registry identifiers are not yet available")
def test_registry_not_available():
    pass
```

Add a new given step (the existing `claude_installed` only produces `napoln_env_with_claude`, but the new scenario needs the fixture named `env` — add a second fixture with that name):

```python
@given("Claude Code is installed", target_fixture="env")
def claude_installed_env(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env
```

Add the when step:

```python
@when(parsers.parse('I run napoln add with a bare name "{name}"'), target_fixture="run_result")
def run_add_bare(env: NapolnTestEnv, name: str, cli_runner: CliRunner):
    env.result = cli_runner.invoke(app, ["add", name], env=env.env_vars)
    return env
```

Note: Check for conflicts with existing `target_fixture` names. The existing "no agents" scenario uses `napoln_env_no_agents` → `run_result`, while this new one uses `env` → `run_result`. If pytest-bdd complains about duplicate step registrations, merge the two given steps into one pattern or use different fixture names.

- [ ] **Step 7: Run all BDD tests**

```bash
just test tests/steps/ -v
```

Expected: All BDD tests pass including the new scenarios.

- [ ] **Step 8: Commit**

```bash
git add -A tests/features/ tests/steps/
git commit -m "test: expand BDD features with missing add, config, and first-run scenarios"
```

---

### Task 4: Gut Integration Tests Down to CLI Surface Only

Now that BDD owns all behavioral contracts, delete the integration tests that duplicate BDD. Keep only `TestVersionCommand` and `TestHelpCommand` — these test CLI surface (flag names, help text, completion visibility) which don't need Gherkin.

**Files:**
- Modify: `tests/integration/test_cli.py`

- [ ] **Step 1: Read the current file to confirm what to keep**

Keep:
- `TestVersionCommand` (1 test) — version output format
- `TestHelpCommand` (5 tests) — help text, 7 commands listed, cut commands hidden, add help, no completion flags

Delete:
- `TestAddCommand` (6 tests) — now covered by `add.feature`
- `TestRemoveCommand` (7 tests) — now covered by `remove.feature`
- `TestListCommand` (3 tests) — now covered by `list.feature`
- `TestInstallCommand` (4 tests) — now covered by `sync.feature`
- `TestInitCommand` (3 tests, keep `test_init_help`) — now covered by `init.feature`
- `TestConfigCommand` (6 tests) — now covered by `config.feature`

`TestInitCommand.test_init_help` tests help text, which is CLI surface. Move it into `TestHelpCommand`.

- [ ] **Step 2: Replace the file**

Replace `tests/integration/test_cli.py` with:

```python
"""Integration tests for napoln CLI surface — help text, version, flags.

Behavioral tests for each command live in tests/features/*.feature.
"""

from __future__ import annotations

import re

from typer.testing import CliRunner

from napoln.cli import app


def runner():
    return CliRunner()


class TestVersionCommand:
    def test_version(self):
        result = CliRunner().invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "napoln" in result.output
        assert re.search(r"\d+\.\d+\.\d+", result.output)


class TestHelpCommand:
    def test_help(self):
        result = CliRunner().invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "agent skills" in result.output.lower()

    def test_help_shows_seven_commands(self):
        result = CliRunner().invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("add", "remove", "upgrade", "list", "install", "init", "config"):
            assert cmd in result.output

    def test_help_hides_cut_commands(self):
        result = CliRunner().invoke(app, ["--help"])
        for cmd in ("status", "diff", "resolve", "sync", "doctor", "gc", "telemetry"):
            assert f"  {cmd} " not in result.output or cmd in ("doctor", "gc")

    def test_no_completion_in_help(self):
        result = CliRunner().invoke(app, ["--help"])
        assert "--install-completion" not in result.output
        assert "--show-completion" not in result.output

    def test_add_help(self):
        result = CliRunner().invoke(app, ["add", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--skill" in result.output
        assert "--project" in result.output

    def test_init_help(self):
        result = CliRunner().invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Scaffold" in result.output
```

- [ ] **Step 3: Remove unused imports and fixtures**

The `isolated_env`, `local_skill`, and `runner` fixtures are no longer needed. The new file has no fixtures — each test creates its own `CliRunner()` inline. Verify no other test file imports from `tests/integration/test_cli.py`.

```bash
grep -r "from tests.integration" tests/
```

Expected: No output.

- [ ] **Step 4: Run full check**

```bash
just check
```

Expected: All tests pass. No ruff errors.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_cli.py
git commit -m "test: reduce integration tests to CLI surface only

Behavioral contracts now live in tests/features/*.feature.
Integration tests retain only help text, version, and flag visibility."
```

---

### Task 5: Unit Tests for `remove.py::_resolve_from_source`

`_resolve_from_source` takes a source string and a manifest, and returns matching skill names. It delegates to `normalize_source_for_match` (already unit-tested) but the filtering/matching over the manifest is untested.

**Files:**
- Create: `tests/unit/test_remove_logic.py`

- [ ] **Step 1: Write the tests**

```python
"""Tests for napoln.commands.remove — source matching logic."""

from __future__ import annotations

import pytest

from napoln.commands.remove import _resolve_from_source
from napoln.core import manifest as manifest_mod


def _entry(source: str) -> manifest_mod.SkillEntry:
    """Build a minimal SkillEntry with the given source."""
    return manifest_mod.SkillEntry(
        source=source,
        version="1.0.0",
        store_hash="abc123",
        installed="2024-01-01T00:00:00Z",
        updated="2024-01-01T00:00:00Z",
        agents={},
    )


class TestResolveFromSource:
    """Match --from-source against manifest entries."""

    def test_no_skills(self):
        mf = manifest_mod.Manifest()
        assert _resolve_from_source("owner/repo", mf) == []

    def test_no_match(self):
        mf = manifest_mod.Manifest()
        mf.skills["my-skill"] = _entry("github.com/alice/tools")
        assert _resolve_from_source("bob/other", mf) == []

    def test_shorthand_matches_full_source(self):
        mf = manifest_mod.Manifest()
        mf.skills["audit"] = _entry("https://github.com/raiderrobert/flow")
        assert _resolve_from_source("raiderrobert/flow", mf) == ["audit"]

    def test_multiple_skills_from_same_source(self):
        mf = manifest_mod.Manifest()
        for name in ("skill-a", "skill-b"):
            mf.skills[name] = _entry("https://github.com/owner/mono")
        assert sorted(_resolve_from_source("owner/mono", mf)) == ["skill-a", "skill-b"]

    @pytest.mark.parametrize(
        "source_in_manifest, query",
        [
            ("https://github.com/owner/repo.git", "owner/repo"),
            ("github.com/owner/repo", "owner/repo"),
            ("git@github.com:owner/repo.git", "owner/repo"),
        ],
        ids=["https-dotgit", "bare-host", "ssh"],
    )
    def test_normalization_variants(self, source_in_manifest, query):
        mf = manifest_mod.Manifest()
        mf.skills["the-skill"] = _entry(source_in_manifest)
        assert _resolve_from_source(query, mf) == ["the-skill"]
```

- [ ] **Step 2: Run tests**

```bash
just test tests/unit/test_remove_logic.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_remove_logic.py
git commit -m "test: unit tests for remove _resolve_from_source"
```

---

### Task 6: Unit Tests for `list_cmd.py` Pure Functions

`list_cmd.py` has four pure functions that transform manifest data for display: `_abbreviate_path`, `_get_agent_dirs`, `_common_agent_dirs`, `_get_placement_dirs`. None have tests.

**Files:**
- Create: `tests/unit/test_list_logic.py`

- [ ] **Step 1: Write the tests**

```python
"""Tests for napoln.commands.list_cmd — display helper functions."""

from __future__ import annotations

import pytest

from napoln.commands.list_cmd import (
    _abbreviate_path,
    _common_agent_dirs,
    _get_agent_dirs,
    _get_placement_dirs,
)
from napoln.core import manifest as manifest_mod


def _entry_with_agents(agents: dict[str, str], home: str = "/home/user") -> manifest_mod.SkillEntry:
    """Build a SkillEntry with agent placements at the given paths."""
    agent_placements = {}
    for agent_id, path in agents.items():
        agent_placements[agent_id] = manifest_mod.AgentPlacement(
            path=path, link_mode="copy", scope="global"
        )
    return manifest_mod.SkillEntry(
        source="owner/repo",
        version="1.0.0",
        store_hash="abc",
        installed="2024-01-01T00:00:00Z",
        updated="2024-01-01T00:00:00Z",
        agents=agent_placements,
    )


class TestAbbreviatePath:
    @pytest.mark.parametrize(
        "path, home, expected",
        [
            ("/home/user/.claude/skills/foo", "/home/user", "~/.claude/skills/foo"),
            ("/other/path/skills/foo", "/home/user", "/other/path/skills/foo"),
            ("/home/user", "/home/user", "~"),
        ],
        ids=["under-home", "outside-home", "exact-home"],
    )
    def test_abbreviation(self, path, home, expected):
        assert _abbreviate_path(path, home) == expected


class TestGetAgentDirs:
    def test_single_agent(self):
        entry = _entry_with_agents({"claude-code": "/home/user/.claude/skills/my-skill"})
        assert _get_agent_dirs(entry, "/home/user") == [".claude"]

    def test_shared_placement_deduplicates(self):
        entry = _entry_with_agents({
            "pi": "/home/user/.agents/skills/my-skill",
            "codex": "/home/user/.agents/skills/my-skill",
        })
        assert _get_agent_dirs(entry, "/home/user") == [".agents"]

    def test_no_agents(self):
        entry = _entry_with_agents({})
        assert _get_agent_dirs(entry, "/home/user") == []


class TestCommonAgentDirs:
    def test_all_same(self):
        mf = manifest_mod.Manifest()
        for name in ("skill-a", "skill-b"):
            mf.skills[name] = _entry_with_agents(
                {"claude-code": f"/home/user/.claude/skills/{name}"}
            )
        assert _common_agent_dirs(mf, "/home/user") == [".claude"]

    def test_mixed_returns_none(self):
        mf = manifest_mod.Manifest()
        mf.skills["a"] = _entry_with_agents({"claude-code": "/home/user/.claude/skills/a"})
        mf.skills["b"] = _entry_with_agents({"cursor": "/home/user/.cursor/skills/b"})
        assert _common_agent_dirs(mf, "/home/user") is None

    def test_empty_manifest(self):
        mf = manifest_mod.Manifest()
        assert _common_agent_dirs(mf, "/home/user") is None


class TestGetPlacementDirs:
    def test_deduplicates_shared_path(self):
        entry = _entry_with_agents({
            "pi": "/home/user/.agents/skills/my-skill",
            "codex": "/home/user/.agents/skills/my-skill",
        })
        assert _get_placement_dirs(entry, "/home/user") == ["~/.agents/skills"]

    def test_multiple_distinct_paths(self):
        entry = _entry_with_agents({
            "claude-code": "/home/user/.claude/skills/my-skill",
            "cursor": "/home/user/.cursor/skills/my-skill",
        })
        dirs = _get_placement_dirs(entry, "/home/user")
        assert "~/.claude/skills" in dirs
        assert "~/.cursor/skills" in dirs
```

- [ ] **Step 2: Run tests**

```bash
just test tests/unit/test_list_logic.py -v
```

Expected: All 9 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_list_logic.py
git commit -m "test: unit tests for list_cmd display helpers"
```

---

### Task 7: Extract and Unit Test `config.py::_parse_config_value`

`run_config_set` has an inline value parser that converts strings to typed Python values (bool, int, list, string). Extract it into a named function and unit test it.

**Files:**
- Modify: `src/napoln/commands/config.py`
- Create: `tests/unit/test_config_logic.py`

- [ ] **Step 1: Extract the parser**

In `src/napoln/commands/config.py`, add this function above `run_config_set`:

```python
def _parse_config_value(value: str) -> str | bool | int | list[str]:
    """Parse a config value string into a typed Python value."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    if value.isdigit():
        return int(value)
    if "," in value:
        return [v.strip() for v in value.split(",")]
    return value
```

Then replace the inline parsing block in `run_config_set` (the `parsed_value: str | bool | int | list` declaration and the if/elif chain) with:

```python
    parsed_value = _parse_config_value(value)
```

- [ ] **Step 2: Verify the refactor is safe**

```bash
just check
```

Expected: All tests pass.

- [ ] **Step 3: Write the unit tests**

```python
"""Tests for napoln.commands.config — configuration logic."""

from __future__ import annotations

import pytest

from napoln.commands.config import _parse_config_value


class TestParseConfigValue:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("true", True),
            ("True", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("no", False),
        ],
        ids=["true-lower", "true-title", "yes-lower", "false-lower", "false-title", "no-lower"],
    )
    def test_booleans(self, raw, expected):
        assert _parse_config_value(raw) is expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("0", 0),
            ("42", 42),
        ],
        ids=["zero", "positive"],
    )
    def test_integers(self, raw, expected):
        result = _parse_config_value(raw)
        assert result == expected
        assert isinstance(result, int)

    def test_comma_separated_list(self):
        assert _parse_config_value("claude-code, pi, codex") == ["claude-code", "pi", "codex"]

    def test_comma_no_spaces(self):
        assert _parse_config_value("a,b,c") == ["a", "b", "c"]

    def test_plain_string(self):
        assert _parse_config_value("project") == "project"

    def test_mixed_alphanumeric_is_string(self):
        assert _parse_config_value("v1") == "v1"

    def test_negative_number_is_string(self):
        """isdigit() returns False for negatives."""
        assert _parse_config_value("-1") == "-1"
```

- [ ] **Step 4: Run tests**

```bash
just test tests/unit/test_config_logic.py -v
```

Expected: All 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/napoln/commands/config.py tests/unit/test_config_logic.py
git commit -m "refactor: extract _parse_config_value, add unit tests"
```

---

### Task 8: Unit Tests for `add.py::_ensure_initialized`

`_ensure_initialized` creates the napoln home structure (store/, cache/, config.toml with defaults). Called on every `add` but tested only as a side effect of CLI tests.

**Files:**
- Create: `tests/unit/test_add_logic.py`

- [ ] **Step 1: Write the tests**

```python
"""Tests for napoln.commands.add — initialization logic."""

from __future__ import annotations

import tomllib

from napoln.commands.add import _ensure_initialized


class TestEnsureInitialized:
    def test_creates_directory_structure(self, tmp_path):
        home = tmp_path / ".napoln"
        _ensure_initialized(home)

        assert home.is_dir()
        assert (home / "store").is_dir()
        assert (home / "cache").is_dir()

    def test_writes_default_config(self, tmp_path):
        home = tmp_path / ".napoln"
        _ensure_initialized(home)

        config_path = home / "config.toml"
        assert config_path.exists()
        data = tomllib.loads(config_path.read_text())
        assert data["napoln"]["default_agents"] == []
        assert data["napoln"]["default_scope"] == "global"
        assert data["telemetry"]["enabled"] is False

    def test_does_not_overwrite_existing_config(self, tmp_path):
        home = tmp_path / ".napoln"
        _ensure_initialized(home)

        config_path = home / "config.toml"
        config_path.write_text('[napoln]\ndefault_scope = "project"\n')

        _ensure_initialized(home)

        data = tomllib.loads(config_path.read_text())
        assert data["napoln"]["default_scope"] == "project"

    def test_creates_nested_parent_dirs(self, tmp_path):
        home = tmp_path / "deep" / "nested" / ".napoln"
        _ensure_initialized(home)

        assert home.is_dir()
        assert (home / "store").is_dir()
```

- [ ] **Step 2: Run tests**

```bash
just test tests/unit/test_add_logic.py -v
```

Expected: All 4 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_add_logic.py
git commit -m "test: unit tests for add _ensure_initialized"
```

---

### Task 9: Unit Tests for `linker.py::restore_placement`

`restore_placement` is used by `napoln install` to restore skills from the store. It has zero test coverage. It's a simple "place if missing" guard but that idempotency contract should be tested directly.

**Files:**
- Modify: `tests/unit/test_linker.py`

- [ ] **Step 1: Read the current imports in test_linker.py**

Check what's already imported so the new tests integrate cleanly.

```bash
head -15 tests/unit/test_linker.py
```

- [ ] **Step 2: Add `restore_placement` to the imports and append tests**

Add `restore_placement` to the import from `napoln.core.linker`.

Append to the end of `tests/unit/test_linker.py`:

```python
class TestRestorePlacement:
    """restore_placement — idempotent placement from store."""

    def test_places_when_missing(self, tmp_path, skill_builder):
        skill_path = skill_builder(name="restore-test")
        from napoln.core import store as store_mod

        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "store").mkdir()
        store_path, content_hash = store_mod.store_skill(
            skill_path, "restore-test", "1.0.0", napoln_home
        )

        placement = tmp_path / "agents" / "skills" / "restore-test"
        result = restore_placement(
            store_path, placement, "owner/repo", "1.0.0", content_hash
        )

        assert result is not None
        assert (placement / "SKILL.md").exists()
        assert (placement / ".napoln").exists()

    def test_skips_when_already_exists(self, tmp_path, skill_builder):
        skill_path = skill_builder(name="exists-test")
        from napoln.core import store as store_mod

        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "store").mkdir()
        store_path, content_hash = store_mod.store_skill(
            skill_path, "exists-test", "1.0.0", napoln_home
        )

        placement = tmp_path / "agents" / "skills" / "exists-test"
        placement.mkdir(parents=True)
        (placement / "SKILL.md").write_text("already here")

        result = restore_placement(
            store_path, placement, "owner/repo", "1.0.0", content_hash
        )

        assert result is None
        assert (placement / "SKILL.md").read_text() == "already here"
```

- [ ] **Step 3: Run tests**

```bash
just test tests/unit/test_linker.py -v
```

Expected: All tests pass including the 2 new ones.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_linker.py
git commit -m "test: unit tests for linker restore_placement"
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run full check**

```bash
just check
```

Expected: format, lint, and all tests pass.

- [ ] **Step 2: Verify the BDD layer is now comprehensive**

```bash
ls tests/features/
```

Expected:
```
add.feature
config.feature
first_run.feature
init.feature
list.feature
remove.feature
setup.feature
sync.feature
upgrade.feature
```

9 feature files covering all 7 CLI commands (add, remove, upgrade, list, install, init, config) plus first-run and setup workflows.

- [ ] **Step 3: Verify integration tests are minimal**

```bash
grep "def test_" tests/integration/test_cli.py | wc -l
```

Expected: 7 tests (1 version + 6 help/surface).

- [ ] **Step 4: Count total tests**

```bash
just test --co -q 2>&1 | tail -3
```

Verify the total is reasonable. Expect a net increase of ~20-25 tests (new BDD scenarios + unit tests - deleted integration duplicates).

- [ ] **Step 5: Commit if any final cleanup needed**

```bash
just fmt
git add -A
git commit -m "chore: final cleanup after BDD consolidation"
```
