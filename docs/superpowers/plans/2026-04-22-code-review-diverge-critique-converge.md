# Code Review: Diverge-Critique-Converge

> **For agentic workers:** This plan uses the diverge-critique-converge workflow. Dispatch 3 independent code reviewer agents, then 2 critics, then synthesize findings.

**Goal:** Produce a comprehensive, high-confidence code review of the napoln codebase covering architecture adherence, code smells, and quality issues.

**Architecture:** Three code reviewer agents independently review the full codebase (~4100 lines, 22 source files) against a shared checklist of 13 review criteria. Two critic agents then review all three reports for false positives, missed items, and severity disagreements. Finally, synthesize into a single consolidated report with only high-confidence findings.

**Workflow:** Diverge (3 reviewers) -> Critique (2 critics) -> Converge (1 synthesis)

---

## Review Checklist (All 13 Criteria)

Every reviewer evaluates ALL criteria. Independent coverage creates natural cross-validation.

| # | Category | What to look for |
|---|----------|-----------------|
| 1 | Cross-domain imports | Imports placed inside functions to avoid circular deps or scope issues. Modules importing from the wrong layer. |
| 2 | Bare exceptions | `except Exception`, `except BaseException`, or bare `except:` that swallow errors without useful messages or re-raising. |
| 3 | Code duplication | Repeated logic across files that should be extracted. Near-identical patterns with minor variations. |
| 4 | Dependency direction | `core/` importing from `commands/`, `cli.py`, `output.py`, or `prompts.py`. Architecture mandates one-way: commands -> core. |
| 5 | Undocumented modules | Files that exist in the source tree but aren't mentioned in ARCHITECTURE.md or CONTRIBUTING.md (e.g., `commands/setup.py`). |
| 6 | Command convention | Do all command modules export a `run_<command>()` function as documented? Any commands that break the pattern? |
| 7 | Error type consistency | `errors.py` defines custom error types. Are they used throughout, or do modules raise ad-hoc `ValueError`/`RuntimeError` instead? |
| 8 | Error handling layer | Are errors caught at the right layer? Core swallowing errors the CLI should present? Commands catching things they shouldn't? |
| 9 | Missing type hints | Functions or methods missing parameter or return type annotations. CLAUDE.md requires hints on all signatures. |
| 10 | Dead code | Unused functions, imports, unreachable branches, commented-out code. |
| 11 | Magic strings/numbers | Hardcoded paths, version strings, numeric constants that should be named. |
| 12 | Inconsistent patterns | Similar operations done differently in different places (e.g., path construction, error formatting, output patterns). |
| 13 | `__init__.py` exports | Are package `__init__.py` files intentionally curated or empty? Do they expose the right API surface? |

## Source Files to Review

All reviewers must read all of these files:

**Core layer** (`src/napoln/core/`):
- `agents.py` (224 lines) — Agent detection, path configuration
- `hasher.py` (64 lines) — Content hashing
- `linker.py` (138 lines) — Reflink/copy placement
- `manifest.py` (230 lines) — Manifest TOML read/write
- `merger.py` (231 lines) — Three-way merge
- `resolver.py` (629 lines) — Source resolution (largest file)
- `store.py` (148 lines) — Content-addressed store
- `validator.py` (168 lines) — SKILL.md validation
- `__init__.py` (0 lines) — Empty

**Commands layer** (`src/napoln/commands/`):
- `add.py` (402 lines) — Add command
- `config.py` (310 lines) — Config/doctor/gc subcommands
- `init.py` (54 lines) — Init command
- `install.py` (130 lines) — Install command
- `list_cmd.py` (246 lines) — List command
- `remove.py` (152 lines) — Remove command
- `setup.py` (104 lines) — Undocumented in architecture
- `upgrade.py` (218 lines) — Upgrade command
- `__init__.py` (0 lines) — Empty

**Top-level modules** (`src/napoln/`):
- `cli.py` (325 lines) — Typer CLI entry point
- `errors.py` (64 lines) — Error types
- `output.py` (89 lines) — Terminal output formatting
- `prompts.py` (169 lines) — Interactive skill picker

**Reference docs** (read for context, don't review):
- `ARCHITECTURE.md` — Design decisions and store layout
- `CONTRIBUTING.md` — Project conventions

---

## Phase 1: Diverge — Three Independent Reviews

Dispatch 3 code reviewer agents in parallel. Each reviews the full codebase independently against all 13 criteria.

### Reviewer Instructions (shared across all 3)

```
You are reviewing the napoln codebase — a Python package manager for agent skills.

Read these reference docs first for context (do NOT review them, just understand the architecture):
- ARCHITECTURE.md
- CONTRIBUTING.md

Then read ALL 22 source files listed above and evaluate against ALL 13 review criteria.

For each finding, report:
- **Criterion number** (1-13)
- **File and line number(s)**
- **Severity**: HIGH (architectural violation, bug, or data loss risk), MEDIUM (code smell that hurts maintainability), LOW (style/convention nit)
- **Description**: What's wrong, with a code snippet showing the issue
- **Suggestion**: How to fix it (brief)

Organize findings by file, not by criterion. This makes it easier to act on them.

Do NOT report:
- Style preferences that aren't backed by the project's own documented conventions
- Things that are technically true but don't matter in practice
- Suggestions for new features or capabilities
```

Each reviewer produces an independent report. No reviewer sees another's work.

### Differentiation

To maximize coverage diversity, each reviewer gets a secondary focus area in addition to the full checklist:

- **Reviewer A** — Secondary focus: architecture and dependency boundaries. Pay extra attention to criteria 1, 4, 5, 6, 13.
- **Reviewer B** — Secondary focus: error handling and robustness. Pay extra attention to criteria 2, 7, 8.
- **Reviewer C** — Secondary focus: code quality and duplication. Pay extra attention to criteria 3, 9, 10, 11, 12.

---

## Phase 2: Critique — Two Independent Critics

After all 3 reviewer reports are complete, dispatch 2 critic agents in parallel. Each critic receives ALL THREE reviewer reports.

### Critic Instructions (shared across both)

```
You are a critic reviewing 3 independent code review reports for the napoln codebase.

You have access to the source code. For each finding across all 3 reports:

1. **Verify**: Read the actual code at the cited file:line. Is the finding accurate?
2. **Classify**:
   - CONFIRMED: Finding is real and accurately described
   - FALSE POSITIVE: Finding is inaccurate or misunderstands the code
   - DISPUTED SEVERITY: Finding is real but severity is wrong (state correct severity)
   - DUPLICATE: Same finding reported by multiple reviewers (note which)
3. **Gaps**: After reviewing all findings, identify any issues the reviewers MISSED that you notice in the code.

Report format:
- For each finding: [Reviewer A/B/C] [File:line] [CONFIRMED/FALSE POSITIVE/DISPUTED/DUPLICATE] — brief justification
- At the end: any new findings the reviewers missed, using the same format as reviewer findings
```

- **Critic 1** — Focus on technical accuracy. Are the findings real? Do the code snippets match reality?
- **Critic 2** — Focus on severity calibration and completeness. Are severities appropriate? What did everyone miss?

---

## Phase 3: Converge — Synthesis

After both critics complete, synthesize into a final consolidated report.

### Synthesis Rules

1. **Include** findings that are:
   - CONFIRMED by at least 1 critic AND not FALSE POSITIVE'd by the other
   - Found by 2+ reviewers independently (strong signal)
   - New findings from critics that are substantiated with code references

2. **Exclude** findings that are:
   - FALSE POSITIVE'd by both critics
   - FALSE POSITIVE'd by 1 critic with no reviewer or critic corroboration

3. **Severity** — Use the critic-adjusted severity when disputed. When critics disagree on severity, use the higher one.

4. **Deduplicate** — Merge findings about the same issue from multiple reviewers into a single entry, noting it was independently found by N reviewers.

### Final Report Format

Save to `docs/superpowers/reviews/2026-04-22-code-review.md`:

```markdown
# Code Review: napoln

**Date:** 2026-04-22
**Scope:** Full codebase (src/napoln/, 22 files, ~4100 lines)
**Method:** 3 independent reviewers, 2 critics, synthesized

## Summary

[2-3 sentence overview: how many findings, severity breakdown, biggest themes]

## Critical Findings (HIGH)

### [Finding title]
**Files:** `path/to/file.py:NN`
**Found by:** N/3 reviewers, confirmed by N/2 critics
**Issue:** [description with code snippet]
**Recommendation:** [how to fix]

## Notable Findings (MEDIUM)

[same format]

## Minor Findings (LOW)

[same format, briefer descriptions]

## Themes

[Recurring patterns across findings — what systemic issues do they point to?]
```

---

## Execution Steps

- [ ] **Step 1: Dispatch 3 reviewer agents in parallel**
  Each reviewer reads all source files and reference docs, then produces an independent report against all 13 criteria.

- [ ] **Step 2: Collect all 3 reviewer reports**
  Wait for all to complete. Do not let any reviewer see another's work.

- [ ] **Step 3: Dispatch 2 critic agents in parallel**
  Each critic receives all 3 reports and verifies findings against the actual code.

- [ ] **Step 4: Collect both critic reports**

- [ ] **Step 5: Synthesize final report**
  Apply synthesis rules. Save to `docs/superpowers/reviews/2026-04-22-code-review.md`.

- [ ] **Step 6: Present summary to user**
  Share the key findings and themes. Link to the full report.
