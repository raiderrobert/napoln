# Skill Name Collision Namespacing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `napoln add` would install a skill whose name already exists in the target manifest under a different source, place it under a deterministic namespaced name (e.g. `obra.superpowers:writing-skills`) instead of silently overwriting.

**Architecture:** The namespacing helper lives in `core/` and operates on the typed `ResolvedSource` (which gains a `parsed: ParsedSource | None` field for git sources). `commands/add.py` only reads the helper's output. Local paths derive the namespace from the parent directory of the skill dir; git sources derive it from `parsed.owner` and `parsed.repo`. The SKILL.md `name:` frontmatter is left untouched — directory name is canonical for placement, frontmatter preserves upstream identity.

**Tech Stack:** Python 3.11+, ruff, pytest, pytest-bdd, typer, tomli_w. Run `just check` before every commit.

**Spec source:** Issue #61 + audit report dated 2026-04-29 (this branch).

**Decisions locked in (call out if you disagree before starting):**
- Separator: `<owner>.<repo>:<skill>` for git, `<parent-dir>:<skill>` for local. Matches the existing branch direction; verified TOML round-trips with quoted keys.
- Scope: `add` only. `upgrade` re-resolves from `entry.source` so it cannot introduce a different-source collision; `install` syncs one manifest at a time. Cross-scope collisions (project `add` vs. global manifest) are a known gap, tracked as follow-up issue.
- Validator interaction: validator runs against the source skill dir (cache or local), not the placement target, so namespaced placement names do not trip its `^[a-z0-9-]+$` regex.

---

## Current State (resume here)

**Done:** Tasks 1–5. `core/naming.py` exists, `ResolvedSource.parsed` is wired through, the inline namespacer in `add.py` has been replaced with `namespace_for`, and the original `test_add_collision_namespaced` integration test passes.

**In progress: Task 6.** The idempotency test `test_add_collision_namespaced_is_idempotent` has been added to `tests/integration/test_cli.py` and is **failing**. The previous executor attempted a fix in `_install_single_skill` that added an `elif resolved.parsed is not None or resolved.source_type == "local":` branch — that fix is **wrong and must be reverted** before applying the corrected logic in Task 6 below. The reason the `elif` is wrong: it only fires when `skill_name not in mf.skills`, but in the failing case the original name *is* in the manifest (from the first install of repo-A), so the elif never runs and we re-namespace the already-namespaced skill.

**Still to do:** Tasks 6 (with corrected logic), 7, 8.

---

## File Structure

**Create:**
- `src/napoln/core/naming.py` — `namespace_for(resolved, skill_name) -> str`. Pure function, no I/O.
- `tests/unit/test_naming.py` — parametrized tests for all source shapes.

**Modify:**
- `src/napoln/core/resolver.py` — add `parsed: ParsedSource | None = None` field to `ResolvedSource`; populate it in `resolve_git` and the multi-skill picker path.
- `src/napoln/commands/add.py` — delete `_namespace_skill_name`, import `namespace_for`, simplify `_install_single_skill` collision branch.
- `tests/integration/test_cli.py` — update `test_add_collision_namespaced` assertion to match correct local-path namespace (`repo-b:shared-name`).
- `tests/unit/test_manifest.py` (or create if absent) — add round-trip test for a manifest containing a key with `.` and `:`.

**Out of scope (file follow-up issue):**
- Cross-scope collision detection between global and project manifests.

---

## Task 1: Add `parsed` field to `ResolvedSource`

**Files:**
- Modify: `src/napoln/core/resolver.py:22-30` (the `ResolvedSource` dataclass)
- Modify: `src/napoln/core/resolver.py:222-310` (`resolve_git` — populate the new field)
- Modify: `src/napoln/commands/add.py:281-291` (the picker path that constructs `ResolvedSource` for multi-skill repos — populate the new field)

- [ ] **Step 1: Read the current `ResolvedSource` definition and `ParsedSource`**

Run: `grep -n "class ResolvedSource\|class ParsedSource" src/napoln/core/resolver.py`
Read the surrounding 30 lines for each. You need to know what fields exist before extending.

- [ ] **Step 2: Add the `parsed` field**

Edit `src/napoln/core/resolver.py`. In the `ResolvedSource` dataclass, add a new optional field after the existing fields:

```python
@dataclass
class ResolvedSource:
    source_type: str
    source_id: str
    skill_dir: Path
    version: str
    cleanup: bool = False
    skill_name: str | None = None
    parsed: ParsedSource | None = None  # NEW: typed source metadata for git sources
```

(Use the actual existing field order — only add `parsed`, do not reorder.)

- [ ] **Step 3: Populate `parsed` in `resolve_git`**

In `resolve_git`, find every `return ResolvedSource(...)` and every `ResolvedSource(...)` constructed inside it (including inside the multi-skill loop around line 305+). Pass `parsed=parsed` to each.

- [ ] **Step 4: Populate `parsed` in the multi-skill picker**

In `src/napoln/commands/add.py:281-291`, the picker constructs `ResolvedSource(source_type="git", ...)`. Pass `parsed=parsed` (the variable from the enclosing function signature).

- [ ] **Step 5: Run existing tests to verify nothing broke**

Run: `just test`
Expected: all green. The new field defaults to `None`, so existing `ResolvedSource(...)` calls in tests remain valid.

- [ ] **Step 6: Commit**

```bash
git add src/napoln/core/resolver.py src/napoln/commands/add.py
git commit -m "refactor: carry parsed source on ResolvedSource for git resolutions"
```

---

## Task 2: Write failing tests for `namespace_for`

**Files:**
- Create: `tests/unit/test_naming.py`

- [ ] **Step 1: Write the test file**

Create `tests/unit/test_naming.py` with the following exact contents:

```python
"""Tests for napoln.core.naming."""

from __future__ import annotations

from pathlib import Path

import pytest

from napoln.core.naming import namespace_for
from napoln.core.resolver import ParsedSource, ResolvedSource


def _git_resolved(host: str, owner: str, repo: str, path: str = "") -> ResolvedSource:
    parsed = ParsedSource(
        source_type="git", host=host, owner=owner, repo=repo, path=path, version=None
    )
    source_id = f"{host}/{owner}/{repo}" + (f"/{path}" if path else "")
    return ResolvedSource(
        source_type="git",
        source_id=source_id,
        skill_dir=Path("/tmp/unused"),
        version="1.0.0",
        parsed=parsed,
    )


def _local_resolved(path: str) -> ResolvedSource:
    return ResolvedSource(
        source_type="local",
        source_id=path,
        skill_dir=Path(path),
        version="1.0.0",
    )


@pytest.mark.parametrize(
    "resolved,skill_name,expected",
    [
        # git, single-skill repo
        (_git_resolved("github.com", "obra", "superpowers"), "writing-skills",
         "obra.superpowers:writing-skills"),
        # git, multi-skill repo — owner/repo namespace, NOT including subpath
        (_git_resolved("github.com", "obra", "superpowers", "skills/writing"),
         "writing-skills", "obra.superpowers:writing-skills"),
        # local path — namespace from parent directory of the skill dir
        (_local_resolved("/path/to/repo-b/shared-name"), "shared-name",
         "repo-b:shared-name"),
        # local path with single-segment parent
        (_local_resolved("/repo-b/shared-name"), "shared-name",
         "repo-b:shared-name"),
    ],
)
def test_namespace_for(resolved, skill_name, expected):
    assert namespace_for(resolved, skill_name) == expected


def test_namespace_for_local_root_skill_falls_back_to_dir_name():
    """A skill whose source_id has no parent (e.g. '/skill') uses the skill dir name itself."""
    resolved = _local_resolved("/shared-name")
    # No parent segment available; deterministic fallback uses the skill dir name.
    assert namespace_for(resolved, "shared-name") == "shared-name:shared-name"
```

- [ ] **Step 2: Run tests to verify they fail (module does not exist yet)**

Run: `just test tests/unit/test_naming.py -v`
Expected: ImportError / ModuleNotFoundError on `napoln.core.naming`.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/unit/test_naming.py
git commit -m "test: add failing tests for namespace_for helper"
```

---

## Task 3: Implement `namespace_for`

**Files:**
- Create: `src/napoln/core/naming.py`

- [ ] **Step 1: Write the implementation**

Create `src/napoln/core/naming.py`:

```python
"""Skill name namespacing for collision avoidance."""

from __future__ import annotations

from pathlib import Path

from napoln.core.resolver import ResolvedSource


def namespace_for(resolved: ResolvedSource, skill_name: str) -> str:
    """Compute a deterministic namespaced skill name.

    Used when a skill name already exists in the target manifest under a
    different source. The namespace is derived from the source identity, not
    the skill name, so the same source always produces the same namespace.

    Format:
        git    -> "<owner>.<repo>:<skill_name>"
        local  -> "<parent-dir-name>:<skill_name>"
    """
    if resolved.source_type == "git" and resolved.parsed is not None:
        return f"{resolved.parsed.owner}.{resolved.parsed.repo}:{skill_name}"

    if resolved.source_type == "local":
        parent = Path(resolved.source_id).parent.name
        if parent:
            return f"{parent}:{skill_name}"
        # No parent segment available — use the skill dir name itself as a
        # last-resort namespace. Better than producing "<empty>:<name>".
        return f"{Path(resolved.source_id).name}:{skill_name}"

    # Defensive fallback for any future source_type. Should be unreachable today.
    safe = resolved.source_id.replace("/", ".").replace(":", "")
    return f"{safe}:{skill_name}"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `just test tests/unit/test_naming.py -v`
Expected: all 6 parametrized cases pass.

- [ ] **Step 3: Run full check**

Run: `just check`
Expected: format, lint, and full test suite all pass.

- [ ] **Step 4: Commit**

```bash
git add src/napoln/core/naming.py
git commit -m "feat: add namespace_for helper for skill-name collision avoidance"
```

---

## Task 4: Add manifest TOML round-trip test for namespaced names

**Files:**
- Modify or create: `tests/unit/test_manifest.py`

- [ ] **Step 1: Locate or create the manifest unit test file**

Run: `ls tests/unit/test_manifest.py 2>/dev/null && head -20 tests/unit/test_manifest.py`
If the file does not exist, create it with the standard imports used in other unit tests.

- [ ] **Step 2: Add the round-trip test**

Append to `tests/unit/test_manifest.py`:

```python
def test_manifest_round_trips_namespaced_skill_name(tmp_path):
    """Skill names containing '.' and ':' must survive a write/read round-trip.

    TOML treats '.' as a key separator unless quoted; this test guards against
    a regression where tomli_w (or a future replacement) stops quoting.
    """
    from napoln.core import manifest

    namespaced = "obra.superpowers:writing-skills"
    mf = manifest.Manifest()
    mf = manifest.add_skill_to_manifest(
        mf,
        skill_name=namespaced,
        source="github.com/obra/superpowers",
        version="1.0.0",
        store_hash="abc123",
        agent_placements={},
    )

    path = tmp_path / "manifest.toml"
    manifest.write_manifest(mf, path)

    reloaded = manifest.read_manifest(path)
    assert namespaced in reloaded.skills
    assert reloaded.skills[namespaced].source == "github.com/obra/superpowers"
    assert reloaded.skills[namespaced].version == "1.0.0"
```

If `add_skill_to_manifest`'s real signature differs, adjust the keyword arguments to match (read `src/napoln/core/manifest.py:154` first to confirm).

- [ ] **Step 3: Run the test**

Run: `just test tests/unit/test_manifest.py::test_manifest_round_trips_namespaced_skill_name -v`
Expected: PASS. If it FAILS, the fix is in `manifest.py` (use `tomli_w`'s quoting or wrap the key) — do not work around it in the namespacing helper.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_manifest.py
git commit -m "test: round-trip manifest with namespaced skill keys"
```

---

## Task 5: Replace the inline namespacer in `add.py` with `namespace_for`

**Files:**
- Modify: `src/napoln/commands/add.py:25-49` (delete `_namespace_skill_name`)
- Modify: `src/napoln/commands/add.py:155-171` (collision branch in `_install_single_skill`)
- Modify: `src/napoln/commands/add.py:1-22` (imports)

- [ ] **Step 1: Update the imports**

In `src/napoln/commands/add.py`, add:

```python
from napoln.core.naming import namespace_for
```

(Place it alphabetically among the existing `from napoln.core import ...` lines.)

- [ ] **Step 2: Delete the old `_namespace_skill_name` function**

Remove lines 25-49 of `src/napoln/commands/add.py` (the entire `_namespace_skill_name` function and its blank line). Verify there are no remaining references with:

Run: `grep -n "_namespace_skill_name" src/napoln/commands/add.py`
Expected: no output.

- [ ] **Step 3: Update the collision branch**

Replace the collision block in `_install_single_skill`. Find the block starting at the comment `# Collision detection: namespace skill name if same name exists from different source` and replace through the closing `return 0` of the inner branch with:

```python
    # Collision detection: namespace skill name if same name exists from different source
    if skill_name in mf.skills:
        existing = mf.skills[skill_name]
        if existing.source != resolved.source_id:
            new_name = namespace_for(resolved, skill_name)
            output.info(
                f"Skill name collision detected. "
                f"Installing as '{new_name}' to avoid conflict with "
                f"skill from {existing.source}."
            )
            skill_name = new_name
        elif existing.version == version and existing.store_hash:
            output.info(f"'{skill_name}' v{version} is already installed.")
            return 0
```

(Removes the dead `collision_source` local; reads cleaner.)

- [ ] **Step 4: Run the full test suite**

Run: `just check`
Expected: format/lint/tests all pass, including the previously-failing `test_add_collision_namespaced`.

- [ ] **Step 5: Commit**

```bash
git add src/napoln/commands/add.py
git commit -m "refactor: use core/naming namespace_for in add collision branch"
```

---

## Task 6: Make collision detection idempotent (the failing test)

**State on entry:** `test_add_collision_namespaced_is_idempotent` is already in `tests/integration/test_cli.py` and is failing. The previous executor inserted a broken `elif` branch into `_install_single_skill` that must be reverted before applying the fix below.

**Files:**
- Modify: `src/napoln/commands/add.py` (the collision block in `_install_single_skill`)
- No further changes to `tests/integration/test_cli.py` — the test is already present and correct.

### Why the previous attempt failed

The current collision block (after Task 5) is shaped:

```python
if skill_name in mf.skills:
    existing = mf.skills[skill_name]
    if existing.source != resolved.source_id:
        # namespace and continue
        ...
    elif existing.version == version and existing.store_hash:
        # already installed
        return 0
```

On a **second** `napoln add` of repo-B's `shared-name`:
- `skill_name = "shared-name"` (from the source frontmatter — the resolver always reports the upstream name).
- `mf.skills["shared-name"]` exists from repo-A's install. Source A ≠ source B, so we enter the namespacing branch and reinstall B as `repo-b:shared-name` again. The previous already-namespaced entry is still in the manifest, so we waste work and the test's `"already installed"` assertion fails.

The fix is to **check for an existing namespaced entry of this exact source first**, before the original-name lookup. If we find one, treat it as the canonical entry for this source and short-circuit on version match.

### Corrected logic

- [ ] **Step 1: Revert the broken `elif` from the previous attempt**

Open `src/napoln/commands/add.py` and find the block the previous executor added — the lines beginning with `# Also check for the namespaced name in case we are re-installing` and the `elif resolved.parsed is not None or resolved.source_type == "local":` that follows. Delete that entire block (about 9 lines). The collision section should be back to the post-Task-5 shape (single `if skill_name in mf.skills:` with an inner `if/elif`).

Verify with:

Run: `grep -n "Also check for the namespaced" src/napoln/commands/add.py`
Expected: no output.

- [ ] **Step 2: Replace the collision block with the idempotent version**

Locate the collision block in `_install_single_skill` (the `if skill_name in mf.skills:` block, currently around lines 130-145 depending on prior edits). Replace it with:

```python
    # Collision detection.
    #
    # Two cases produce a "this source is already installed" short-circuit:
    #   1. A previous install of this exact source was namespaced — look it up
    #      under the namespaced key first, so re-adds are idempotent.
    #   2. The skill is recorded under its original name and the source matches.
    #
    # Otherwise, if the original name is taken by a *different* source, we
    # namespace this install to avoid overwriting.
    candidate_namespaced = namespace_for(resolved, skill_name)
    if (
        candidate_namespaced in mf.skills
        and mf.skills[candidate_namespaced].source == resolved.source_id
    ):
        # Case 1: this source was previously namespaced. Adopt that name.
        skill_name = candidate_namespaced
        existing = mf.skills[skill_name]
        if existing.version == version and existing.store_hash:
            output.info(f"'{skill_name}' v{version} is already installed.")
            return 0
    elif skill_name in mf.skills:
        existing = mf.skills[skill_name]
        if existing.source != resolved.source_id:
            # Different source under the same name — namespace this install.
            output.info(
                f"Skill name collision detected. "
                f"Installing as '{candidate_namespaced}' to avoid conflict with "
                f"skill from {existing.source}."
            )
            skill_name = candidate_namespaced
        elif existing.version == version and existing.store_hash:
            # Case 2: same source, same version — already installed.
            output.info(f"'{skill_name}' v{version} is already installed.")
            return 0
```

Note: `candidate_namespaced` is computed unconditionally now and reused in both branches. That keeps the message accurate and avoids calling `namespace_for` twice.

- [ ] **Step 3: Run the idempotency test**

Run: `just test tests/integration/test_cli.py::TestAddCommand::test_add_collision_namespaced_is_idempotent -v`
Expected: PASS. Output should contain `"already installed"` on the third invocation, and no `repo-b:repo-b:` substring anywhere.

- [ ] **Step 4: Run the original collision test to confirm no regression**

Run: `just test tests/integration/test_cli.py::TestAddCommand::test_add_collision_namespaced -v`
Expected: PASS.

- [ ] **Step 5: Run the full check**

Run: `just check`
Expected: format/lint/full test suite all green.

- [ ] **Step 6: Commit**

```bash
git add src/napoln/commands/add.py tests/integration/test_cli.py
git commit -m "fix: make collision namespacing idempotent on repeat installs"
```

---

## Task 7: Document the cross-scope follow-up

**Files:**
- Create: a GitHub issue (no code change)

- [ ] **Step 1: Open the follow-up issue**

Run:

```bash
gh issue create \
  --title "Cross-scope skill name collision not detected (project add vs. global manifest)" \
  --body "$(cat <<'EOF'
Follow-up to #61. The collision detection added in PR for fix/detect-skill-name-collisions only checks the *target* manifest (the one selected by `--project` or default global). If a user runs `napoln add --project foo` and `foo` already exists in the global manifest from a different source, the project install proceeds without namespacing. Both end up on the agent's skill path with the same name.

Scope:
- `commands/add.py:_install_single_skill` should also consult the *other* scope's manifest when checking for collisions, then use `core.naming.namespace_for` if the other-scope source differs.
- Add a BDD scenario covering this case under `tests/features/`.

Out of scope: `upgrade` re-resolves from `entry.source` so it does not introduce different-source overwrites; `install` syncs one manifest at a time. Neither is at risk.
EOF
)"
```

- [ ] **Step 2: Note the issue number in the PR description when you open it.**

---

## Task 8: Final verification and PR

- [ ] **Step 1: Run the full check one more time from a clean state**

Run: `just check`
Expected: all green.

- [ ] **Step 2: Verify the diff against `main`**

Run: `git diff main..HEAD --stat`
Expected: changes confined to `src/napoln/core/naming.py` (new), `src/napoln/core/resolver.py`, `src/napoln/commands/add.py`, `tests/unit/test_naming.py` (new), `tests/unit/test_manifest.py`, `tests/integration/test_cli.py`, plus `uv.lock` if it was already modified on the branch.

- [ ] **Step 3: Open the PR**

Title: `fix: namespace colliding skill names instead of overwriting`

Body (using `gh pr create` with HEREDOC):

```
## Summary
- Auto-namespace a skill name when `napoln add` would overwrite an existing
  installation from a different source. Format: `<owner>.<repo>:<name>` for git,
  `<parent>:<name>` for local paths.
- Helper lives in `core/naming.py` and dispatches on typed `ResolvedSource`
  fields rather than re-parsing `source_id` strings.

## Test plan
- [x] Unit tests cover git single-skill, git multi-skill, and local namespacing.
- [x] Manifest round-trip test confirms namespaced keys (with `.` and `:`) survive write/read.
- [x] Integration test confirms placement at the namespaced directory.
- [x] Integration test confirms re-installing the colliding source is idempotent.
- [x] `just check` passes.

Follow-up: cross-scope collision (project add vs. global manifest) tracked in #<NEW_ISSUE_NUMBER>.

Closes #61.
```

---

## Self-Review

**Spec coverage (audit findings → tasks):**
- HIGH "wrong layer": Tasks 1-3 move logic into `core/naming.py` with typed input.
- HIGH "incomplete coverage of mutating commands": investigated and dismissed during planning — `upgrade` re-resolves from existing source; `install` syncs one manifest. The real residual case (cross-scope) is filed as Task 7 follow-up.
- MEDIUM "namespace bug for local paths": Task 2 test cases + Task 3 implementation.
- MEDIUM "TOML manifest key risk": Task 4 round-trip test.
- MEDIUM "directory vs SKILL.md `name:` divergence": handled by decision documented in plan header (frontmatter is upstream identity, directory is canonical placement; validator runs on source dir, so no warning).
- LOW "dead local + misleading comment + unreachable fallback": Task 5 deletes the old function; Task 3's new function has a deliberate, minimal fallback.

**Placeholder scan:** No "TBD", no "fill in", no "similar to Task N", no abstract validation/error-handling steps. Each code step shows the code.

**Type consistency:** `namespace_for(resolved, skill_name)` signature is consistent across Tasks 2, 3, and 5. `ResolvedSource.parsed` is the only field added; populated in Task 1, consumed in Task 3, asserted in Task 2. `ParsedSource` field names (`owner`, `repo`, `host`, `path`) match `src/napoln/core/resolver.py:60-70` as read during planning.
