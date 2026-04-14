# Development Rules

## First Message

If no concrete task is given, read README.md and ARCHITECTURE.md, then ask what to work on.

## Project Overview

napoln is a package manager for agent skills. Python 3.11+, built with uv and hatchling. CLI uses typer. Tests use pytest + pytest-bdd.

Key directories:
- `src/napoln/core/` — Core logic (no CLI dependency)
- `src/napoln/commands/` — One module per CLI command
- `src/napoln/cli.py` — Typer entry point (7 commands)
- `tests/unit/` — Parametrized unit tests per core module
- `tests/integration/` — CLI tests via typer.testing.CliRunner
- `tests/steps/` — BDD step definitions
- `tests/features/` — BDD .feature files

Read [CONTRIBUTING.md](CONTRIBUTING.md) for full project layout, test organization, and how to add commands or agents.

## Commands

- After code changes: `just check` (runs format check + lint + tests). Fix all errors before committing.
- `just check` is the single source of truth. CI runs the same command.
- `just fmt` to auto-fix formatting and lint issues.
- `just test` to run tests only. Supports args: `just test -k "test_merge" -x -v`
- `just coverage` for coverage report.
- Run the CLI locally: `uv run napoln <command>`
- NEVER run `uv run napoln add` or `uv run napoln remove` against the real `~/.napoln/` during development without explicit user instruction. Tests use isolated `$HOME` and `$NAPOLN_HOME`.

## Code Quality

- Keep `core/` independent. Commands import from core, never the reverse.
- One command per file in `commands/`. Each exports a `run_<command>()` function.
- Use `from __future__ import annotations` in every module.
- Line length: 100 (configured in pyproject.toml).
- Linter/formatter: ruff.
- Type hints on all function signatures.
- No unused imports or variables (ruff enforces this).

## Architecture

Read [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions. Key points:

- **7 CLI commands**: `add`, `remove`, `upgrade`, `list`, `install`, `init`, `config`
- **Reflink-first placement.** Copy-on-write where supported, full copy fallback. No hardlinks (skills are mutable).
- **Content-addressed store** at `~/.napoln/store/{name}/{version}-{hash}/`. Immutable after write.
- **Three-way merge on upgrade** using `git merge-file` with `difflib` fallback.
- **Agent path deduplication.** Gemini CLI, pi, and Codex share `~/.agents/skills/` — one placement serves all three.
- **Dual-scope manifests.** Global (`~/.napoln/manifest.toml`) and project (`.napoln/manifest.toml`). `napoln install` syncs both.
- **No registry in v0.x.** Git-only sources. Registry identifiers are parsed but return "not yet available".
- **No telemetry.** Cut until there's a real backend.

## Testing

- Write tests first when adding behavior.
- Unit tests for core logic, BDD for user-facing workflows.
- Tests run in isolated environments with `$HOME` and `$NAPOLN_HOME` set to tmp dirs.
- The `NapolnTestEnv` class in `tests/steps/conftest.py` manages isolated BDD environments.
- The `skill_builder` factory in `tests/conftest.py` creates test skills for unit tests.
- Use `--agents claude-code` in tests that use `--project` to avoid relying on agent detection.
- BDD tests that check `napoln list` must `chdir` to the isolated home to avoid picking up the real project manifest.
- Reflink may not be available (Linux ext4, CI). The linker falls back to copy. Tests pass on both.

## CLI Design

The CLI has 7 top-level commands. No completion flags in help output. Common short flags:

| Flag | Meaning | Available on |
|------|---------|-------------|
| `-p` | Project scope | add, remove, upgrade, list, install, config doctor |
| `-g` | Global only | list, install |
| `-a` | Install all skills | add |
| `-s` | Select specific skill | add |
| `-v` | Verbose (show paths) | list |

`config` has subcommands: `set`, `doctor`, `gc`.

All mutating commands support `--dry-run`.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add napoln init command
fix: catch ReflinkImpossibleError on Linux
test: BDD coverage for three-way merge cases
refactor: reduce CLI from 13 commands to 7
docs: update ARCHITECTURE.md for new command set
chore: trigger release-please
```

Breaking changes bump minor while pre-v1 (configured via release-please `bump-minor-pre-major`).

## Style

- Concise answers, no filler.
- Neutral technical voice in documentation (no "This is exactly what we want", no first-person plural editorializing).
- No emojis in commits, docs, or code. Terminal output uses unicode symbols (✓, ✗, ⚠, ℹ).

## File Reading

- Use the read tool to examine files, not cat or sed.
- Read files fully before editing.
- When editing, keep `oldText` as small as possible while being unique.
