# Codebase Audit: test/bdd-consolidation-and-unit-tests branch

**Date:** 2026-04-29
**Scope:** Branch diff against main — 22 files changed, ~2,850 lines added, ~470 removed. Focus on test reorganization and the `_parse_config_value` extraction.

## Summary

5 findings (0 HIGH, 3 MEDIUM, 2 LOW). The refactor is structurally sound — the layering decision (BDD = behavioral spec, integration = CLI surface, unit = pure logic) is clean and consistently applied. The main issues are: step definition duplication that will compound as features grow, an inconsistency in agent detection monkeypatching across step files, and a dynamically-typed attribute stash on `NapolnTestEnv`.

## Findings

### tests/steps/ (all 9 step files)

**Criterion:** Duplicated logic
**Severity:** MEDIUM
**Description:** Three step definitions are copy-pasted verbatim into every step file:

```python
# Repeated in 7 files:
@given("Claude Code is installed", target_fixture="env")
def claude_installed(napoln_env: NapolnTestEnv):
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)
    return napoln_env

# Repeated in all 9 files:
@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(result_env: NapolnTestEnv, code: int): ...

@then(parsers.parse('the output contains "{text}"'))
def output_contains(result_env: NapolnTestEnv, text: str): ...
```

Similarly, `a skill "{name}" is installed` is repeated in 5 files with identical bodies.

This is a pre-existing pattern, but the branch doubled the number of step files (from 5 to 9), which doubled the duplication. Each new feature file adds another copy.

**Recommendation:** Move shared steps into `tests/steps/conftest.py` (or a dedicated `tests/steps/shared_steps.py`). pytest-bdd supports step definitions in `conftest.py` and they're available to all feature files without re-declaration. This would eliminate ~100 lines of duplication and make adding new features cheaper.

---

### tests/steps/ — inconsistent `_check_on_path` monkeypatching

**Criterion:** Inconsistent patterns
**Severity:** MEDIUM
**Description:** Some step files monkeypatch `napoln.core.agents._check_on_path` to prevent the developer's locally-installed agents (pi, codex, hermes) from leaking into BDD test results. Others don't.

| File | Monkeypatches `_check_on_path`? |
|---|---|
| `test_upgrade.py` | Yes |
| `test_setup.py` | Yes |
| `test_sync.py` | Yes |
| `test_first_run.py` | Yes (in one scenario) |
| `test_install.py` | No |
| `test_remove.py` | No |
| `test_config.py` | No |
| `test_list.py` | No |
| `test_init.py` | No |

The files that don't monkeypatch will detect real agents on the developer's machine and install skills to those agent directories too. This works by accident — the tests assert on Claude Code's directory and don't check that *only* Claude Code got the skill. But it means test behavior varies by machine. On a developer's Mac with pi and codex installed, `test_install.py` silently creates placements in `~/.agents/skills/` inside the temp dir, while `test_upgrade.py` doesn't.

This is a latent correctness issue: if any test later asserts "only placed for Claude Code" (like `test_setup.py` does), it would fail without the monkeypatch on machines with pi/codex.

**Recommendation:** Move the monkeypatch into the shared `claude_installed` Given step so it's applied uniformly. Every test that says "Claude Code is installed" should mean "only Claude Code is installed."

---

### tests/steps/test_sync.py:100

**Criterion:** Hidden dependencies / data clumps
**Severity:** MEDIUM
**Description:** The "Install restores skills from project manifest" scenario stashes state on the `NapolnTestEnv` via a dynamically-set attribute:

```python
# In the Given step:
env._project_skill_placement = skill_placement

# In the Then step:
placement = getattr(result_env, "_project_skill_placement", None)
```

This is untyped, invisible to the class definition, and uses `getattr` with a fallback — a pattern that silently passes if the Given step is removed or renamed. The `NapolnTestEnv` class has no `_project_skill_placement` attribute, so type checkers and IDE navigation can't track this coupling.

**Recommendation:** Add `_project_skill_placement: Path | None = None` to `NapolnTestEnv.__init__` in `conftest.py`. This makes the attribute visible, typed, and documents that it's expected to be set by some scenarios.

---

### tests/features/add.feature — "Add with project scope" scenario is thin

**Criterion:** Speculative / incomplete coverage
**Severity:** LOW
**Description:** The "Add with project scope" scenario only asserts exit code 0:

```gherkin
Scenario: Add with project scope
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with --project --agents claude-code
    Then the exit code is 0
```

This is weaker than the other scenarios which assert on store contents, placements, and manifest state. It confirms the command doesn't crash but doesn't verify the skill was placed in the project directory or that the project manifest was written.

**Recommendation:** Add Then steps:
```gherkin
Then the project manifest contains the skill
And the skill is placed in the project's Claude Code skills directory
And the exit code is 0
```

---

### tests/features/ — `enable` command has no BDD coverage

**Criterion:** Documentation alignment (unenforced convention)
**Severity:** LOW
**Description:** The `enable` command is registered in `cli.py` and has a unit test file (`test_enable.py`), but no BDD feature file and no integration test. The old `test_cli.py` didn't test it either. The AGENTS.md lists "7 CLI commands" and doesn't include `enable` or `setup`, but both are registered as `@app.command()` and visible in help output.

`setup` has full BDD coverage (`setup.feature`, 4 scenarios). `enable` has nothing at the BDD layer.

**Recommendation:** Not necessarily a finding from this branch (the gap is pre-existing), but the consolidation work claimed BDD is now the canonical spec for "every command." Either add `enable.feature` or document in AGENTS.md that `enable` is intentionally uncovered at the BDD layer.

---

## Themes

**Step definition duplication is the systemic risk.** The branch went from 5 to 9 step files, each re-declaring the same 3-4 common steps. This is the main thing that will slow down future feature additions. Extracting shared steps into conftest would make the BDD layer genuinely cheap to extend.

**Monkeypatch inconsistency is a test reliability issue.** Tests pass everywhere today because assertions are loose enough to tolerate extra agent placements. If any future assertion tightens (e.g., "exactly one placement was created"), tests will break on machines with pi/codex installed but not on CI.

## What's Working Well

- **Clean layer separation.** BDD owns behavior, integration owns CLI surface, unit tests own pure functions. The line is drawn consistently — 38 BDD scenarios, 7 integration tests, 124 unit tests. No overlap.

- **Feature files read as specs.** `upgrade.feature` and `setup.feature` (pre-existing) are the strongest examples — they document the three-way merge cases and multi-agent routing logic in plain language. The new `remove.feature` and `sync.feature` follow the same pattern well, particularly the "from-source" and "restore from manifest" scenarios.

- **The `_parse_config_value` extraction is textbook.** Inline parsing logic pulled into a named function with a clear signature, existing behavior preserved (verified by the BDD config tests still passing), and thorough unit tests added covering booleans, integers, lists, strings, and edge cases (negative numbers, mixed alphanumeric). No behavioral change, pure improvement.

- **Unit test factories (`_entry`, `_entry_with_agents`) are well-designed.** They reduce SkillEntry construction boilerplate from 7 keyword arguments to 1, making test intent clear.

- **Integration tests are correctly minimal.** 7 tests for help/version/flags is the right scope for what's left — pure CLI surface with no filesystem side effects.
