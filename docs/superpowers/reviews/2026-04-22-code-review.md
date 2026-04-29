# Code Review: napoln

**Date:** 2026-04-22
**Scope:** Full codebase (`src/napoln/`, 22 files, ~4100 lines)
**Method:** 3 independent reviewers, 2 critics, synthesized

## Summary

16 confirmed findings across the codebase: 2 HIGH, 7 MEDIUM, 7 LOW. The architecture is fundamentally sound — dependency direction (commands -> core, never reverse) is enforced, type hints are complete, and the command convention (`run_<command>()`) is followed consistently. The two systemic issues are **overly broad exception handling** (`except Exception` in 7+ locations) and **code duplication** (the same helper copied across all 7 command files). No bugs or data loss risks were found.

---

## HIGH Findings

### 1. Circular dependency between store.py and resolver.py

**Files:** `core/store.py:127`, `core/resolver.py:14`
**Found by:** 1/3 reviewers, confirmed by 2/2 critics (one upgraded severity)
**Criterion:** 1 (cross-domain imports), 4 (dependency direction)

`resolver.py` imports `store_skill` from `store.py` at module level. `store.py` imports `resolve_and_store` from `resolver.py` inside `ensure_stored()` as a lazy import to break the cycle. This isn't just an import ordering issue — it's mutual function-level coupling: `resolve_and_store()` calls `store_skill()`, and `ensure_stored()` calls `resolve_and_store()`. Both modules are tightly coupled and harder to test independently.

```python
# store.py:127 — lazy import to break cycle
def ensure_stored(...) -> Path:
    from napoln.core.resolver import resolve_and_store

# resolver.py:14 — module-level import
from napoln.core.store import store_skill
```

**Recommendation:** Extract the bridging logic. `ensure_stored()` combines resolution + storage — move it to `resolver.py` (which already depends on `store.py`), or to a new orchestration module. The goal is one-way dependency: resolver -> store, not bidirectional.

---

### 2. Private functions used as public API

**Files:** `commands/add.py:14-15`, `commands/upgrade.py:212`
**Found by:** 1/3 reviewers, confirmed by 2/2 critics (one upgraded from MEDIUM to HIGH)
**Criterion:** 12 (inconsistent patterns)

Several underscore-prefixed functions in `core/` are imported and used by `commands/`:

- `add.py` imports `_extract_description`, `_resolve_version` from `core/resolver.py`
- `upgrade.py` imports `_now_iso` from `core/manifest.py`

These are marked private by Python convention but function as public API. If someone refactors `resolver.py` internals and renames `_extract_description`, `add.py` breaks silently.

**Recommendation:** Either remove the underscore prefix (making them explicitly public) or provide public wrappers. If they're truly internal, restructure so commands don't need to call them directly.

---

## MEDIUM Findings

### 3. `_get_napoln_home()` duplicated 7 times

**Files:** `commands/add.py:24`, `commands/remove.py:13`, `commands/upgrade.py:14`, `commands/list_cmd.py:11`, `commands/install.py:12`, `commands/config.py:16`, `commands/setup.py:16`
**Found by:** 3/3 reviewers, confirmed by 2/2 critics
**Criterion:** 3 (code duplication)

Identical 3-line function in every command module:

```python
def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))
```

Each copy also has `import os` inside the function body, adding a deferred-import smell on top of the duplication.

**Recommendation:** Extract to a shared location. Options:
- `core/paths.py` (if core needs it too)
- Top-level `paths.py` (if only commands use it)

---

### 4. Broad exception handlers throughout

**Files:** `core/resolver.py:484,508`, `core/manifest.py:73`, `core/merger.py:230`, `commands/add.py:155,178,215`, `commands/install.py:59`, `commands/config.py:215`
**Found by:** 3/3 reviewers, confirmed by 2/2 critics
**Criterion:** 2 (bare exceptions)

9 instances of `except Exception` (or `except Exception as e`) that catch all errors instead of specific types. Three patterns:

| Pattern | Locations | Risk |
|---------|-----------|------|
| `except Exception: pass` | resolver.py:484, 508 | Silently swallows YAML, I/O, encoding errors |
| `except Exception: return False` | merger.py:230 | Hides unreadable files as "no conflicts" |
| `except Exception as e: output.error(...)` | add.py:155,178; install.py:59 | Catches programming bugs (AttributeError, KeyError) alongside expected failures |

**Recommendation:** Replace each with specific exception types:
- TOML parsing: `(OSError, tomllib.TOMLDecodeError)`
- YAML parsing: `(OSError, yaml.YAMLError, UnicodeDecodeError)`
- Store/placement: `(StoreError, PlacementError, OSError)`
- Conflict detection: `(OSError, UnicodeDecodeError)`

---

### 5. Inconsistent exception handling patterns in core

**Files:** `core/resolver.py`, `core/manifest.py`, `core/merger.py`, `core/store.py`
**Found by:** 0/3 reviewers (critic-identified), confirmed by 1/2 critics
**Criterion:** 8 (error handling layer), 12 (inconsistent patterns)

The project defines custom error types (`StoreError`, `ManifestError`, `ResolverError`, etc.) in `errors.py`, but core modules use them inconsistently:

| Module | Pattern |
|--------|---------|
| `manifest.py` | Wraps in `ManifestError` with cause and fix message |
| `resolver.py` | `except Exception: pass` — silent fallback |
| `merger.py` | `except Exception: return False` — silent fallback |
| `store.py` | `except Exception: cleanup + bare raise` — no wrapping |

`manifest.py` is the gold standard: it catches specific errors and wraps them in a custom type with actionable fix suggestions. Other modules should follow this pattern.

**Recommendation:** Establish the `manifest.py` pattern as the convention. Each core module should wrap lower-level errors in its corresponding custom error type from `errors.py`.

---

### 6. Documentation says 7 commands, CLI has 8

**Files:** `ARCHITECTURE.md:362,388`, `CONTRIBUTING.md:23`, `CLAUDE.md:19`, `cli.py:247`
**Found by:** 3/3 reviewers, confirmed by 2/2 critics
**Criterion:** 5 (undocumented modules)

`commands/setup.py` is registered in `cli.py` but not documented in ARCHITECTURE.md, CONTRIBUTING.md, or CLAUDE.md. All three docs say "7 CLI commands" and list: add, remove, upgrade, list, install, init, config. The actual CLI has 8.

**Recommendation:** Update all three docs to list 8 commands and describe `setup` (interactive onboarding to choose default agents).

---

### 7. Frontmatter extraction duplication in resolver.py

**Files:** `core/resolver.py:461-487`, `core/resolver.py:490-511`
**Found by:** 1/3 reviewers, confirmed by 2/2 critics
**Criterion:** 3 (code duplication)

`_extract_version()` and `_extract_description()` both:
1. Read `SKILL.md`
2. Check for `---` frontmatter delimiters
3. Parse YAML frontmatter
4. Extract a field from the parsed dict

The frontmatter parsing (steps 1-3) is identical. Only the field extraction differs.

**Recommendation:** Extract a shared `_parse_skill_frontmatter(skill_dir: Path) -> dict | None` and have both functions call it.

---

### 8. `_ensure_initialized()` partial duplication

**Files:** `commands/add.py:30-50`, `commands/setup.py:20-23`
**Found by:** 1/3 reviewers, disputed by critics (one said false positive, one said keep)
**Criterion:** 3 (code duplication)

Both functions create `napoln_home`, `store/`, and `cache/` directories. `add.py`'s version additionally creates a default `config.toml`. The directory creation logic is identical; the config creation is add-only.

**Recommendation:** Extract the shared directory creation to a utility function. Have `add.py` call it + create config separately.

---

### 9. Inconsistent custom error type usage

**Files:** `errors.py`, `core/store.py`, `core/linker.py`, `commands/add.py`
**Found by:** 1/3 reviewers, confirmed by 2/2 critics
**Criterion:** 7 (error type consistency)

`errors.py` defines `StoreError` and `PlacementError`, but:
- `store.py` raises `StoreError` only for hash mismatches (line 51-55), not general storage failures
- `linker.py` never raises `PlacementError`
- `add.py` catches `Exception` instead of these specific types

**Recommendation:** Have `store.py` and `linker.py` wrap filesystem errors in their respective custom types, so commands can catch `StoreError`/`PlacementError` specifically.

---

## LOW Findings

### 10. Deferred import of `__version__` in linker.py

**File:** `core/linker.py:108`
**Criterion:** 1 (cross-domain imports)

`from napoln import __version__` inside `write_provenance()`. Likely avoids a potential circular import (core importing from top-level package). Functional but unusual.

### 11. Deferred command imports in cli.py (undocumented pattern)

**File:** `cli.py:74,118,158,...`
**Criterion:** 1 (cross-domain imports)

All command module imports are inside function bodies for CLI startup performance. This is intentional and correct, but should be documented in CONTRIBUTING.md so contributors don't "fix" it by moving imports to module level.

### 12. Questionary indicator override duplicated in prompts.py

**File:** `prompts.py:81-84`, `prompts.py:139-142`
**Criterion:** 3 (code duplication)

Identical 4-line `setattr` block overriding questionary's checkbox symbols appears in both `pick_skills()` and `pick_agents()`.

### 13. list_cmd.py bypasses output.py abstraction

**File:** `commands/list_cmd.py:103,148,235`
**Criterion:** 12 (inconsistent patterns)

Imports `typer` directly and calls `typer.echo()` / `typer.style()` instead of routing through `output.py` like other commands.

### 14. Magic strings in agents.py detection logic

**File:** `core/agents.py:107-120`
**Criterion:** 11 (magic strings)

`.claude`, `.gemini`, `.pi`, `.cursor` hardcoded in `detect_agents()`. These match the `AgentConfig` definitions but aren't derived from them, creating drift risk.

### 15. Magic version fallback "0.0.0"

**File:** `core/resolver.py:356,358,465,472,487`
**Criterion:** 11 (magic strings)

The fallback version string `"0.0.0"` appears 5+ times. Should be a named constant.

### 16. Magic string ".napoln" appears 29 times

**Files:** Throughout `core/` and `commands/`
**Criterion:** 11 (magic strings)

The provenance filename `.napoln` and home directory name `.napoln` are the same string used in different contexts. A constant would clarify intent and reduce repetition.

---

## Themes

**1. Exception handling is the biggest systemic issue.** The codebase has custom error types but doesn't use them consistently. Some modules wrap errors beautifully (manifest.py), others swallow them silently (resolver.py, merger.py). Establishing manifest.py's pattern as the convention and applying it everywhere would significantly improve debuggability.

**2. Code duplication is concentrated in command boilerplate.** The `_get_napoln_home()` helper, `_ensure_initialized()`, and manifest-reading loops are repeated across commands. A small shared utility module would eliminate most of it.

**3. Architecture is clean where it matters.** The core/commands boundary is properly enforced (no reverse imports). The one violation (store↔resolver circular dep) is localized and fixable by moving the bridging function to one side.

**4. The codebase is well-typed and lint-clean.** All function signatures have type hints. No dead code was found. The command convention is followed consistently. These are signs of good engineering discipline — the issues found are refinements, not structural problems.

---

## What's Working Well

- Dependency direction (commands -> core) is strictly enforced
- All function signatures have complete type hints
- Command convention (`run_<command>()`) followed consistently
- Custom error hierarchy in `errors.py` is well-designed
- No dead code detected
- `manifest.py` is an exemplar of good error handling
