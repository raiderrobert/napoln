# Contributing to napoln

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Optionally install [just](https://github.com/casey/just) for task running.

```bash
git clone git@github.com:raiderrobert/napoln.git
cd napoln
uv sync --extra dev
```

Verify everything works:

```bash
just check       # or: uv run ruff check src/ tests/ && uv run pytest
```

## Project Layout

```
src/napoln/
├── cli.py              # Typer CLI entry point
├── errors.py           # Error types
├── output.py           # Terminal output formatting
├── telemetry.py        # Telemetry (opt-in only)
├── commands/           # One module per CLI command
│   ├── add.py
│   ├── remove.py
│   ├── upgrade.py
│   └── ...
├── core/               # Core logic (no CLI dependency)
│   ├── agents.py       # Agent detection, path configuration
│   ├── hasher.py       # Content hashing (SHA-256)
│   ├── linker.py       # Reflink/copy placement
│   ├── manifest.py     # Manifest TOML read/write
│   ├── merger.py       # Three-way merge (git merge-file + fallback)
│   ├── resolver.py     # Source resolution (git, local, registry)
│   ├── store.py        # Content-addressed store
│   └── validator.py    # SKILL.md validation
└── skills/             # Bundled bootstrap skill
    └── napoln-manage/
        └── SKILL.md
```

The `core/` package has no dependency on `commands/` or `cli.py`. Commands import from core, never the reverse.

## Running Tests

```bash
just test                     # full suite
just unit                     # unit tests only
just bdd                      # BDD scenario tests only
just integration              # CLI integration tests only
just coverage                 # with coverage report
just test -k "test_merge"     # run tests matching a pattern
just test -x -v               # stop on first failure, verbose
```

Or without just:

```bash
uv run pytest
uv run pytest tests/unit/ -x -v
uv run pytest --cov=napoln --cov-report=term-missing
```

### Test Organization

| Directory | What | How |
|-----------|------|-----|
| `tests/unit/` | One file per `core/` module. Parametrized with `pytest.mark.parametrize`. | Fast, no I/O beyond `tmp_path`. |
| `tests/integration/` | CLI commands via `typer.testing.CliRunner`. | Full command round-trips against an isolated `$HOME`. |
| `tests/steps/` | BDD scenarios (`pytest-bdd`). Feature files in `tests/features/`. | End-to-end workflows: install → customize → upgrade → verify merge. |
| `tests/fixtures/` | Static skill directories for tests. | Committed test data. |

Shared fixtures live in `tests/conftest.py`. The `skill_builder` factory is available to all unit tests.

### Writing a New Test

Unit test for a core module:

```python
# tests/unit/test_hasher.py
class TestHashSkill:
    def test_deterministic(self, simple_skill):
        assert hash_skill(simple_skill) == hash_skill(simple_skill)
```

BDD scenario:

```gherkin
# tests/features/upgrade.feature
Scenario: Fast-forward when no local changes
  Given Claude Code is installed
  And a skill "test-skill" is installed at version "1.0.0"
  And the Claude Code placement is unmodified
  And upstream has released version "2.0.0" with a new section
  When I run napoln upgrade test-skill
  Then the Claude Code placement contains the new upstream content
  And the exit code is 0
```

Step definitions go in `tests/steps/test_<feature>.py`.

## Linting

```bash
just lint        # check only
just fix         # auto-fix
```

napoln uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Config is in `pyproject.toml`:

- Target: Python 3.11
- Line length: 100

## Making Changes

1. **Create a branch** off `main`.
2. **Write tests first** when adding behavior. Unit tests for core logic, BDD for user-facing workflows.
3. **Run `just check`** before pushing. This runs lint + the full test suite.
4. **Keep `core/` independent.** Commands import from core, not the reverse. If you need shared logic, it goes in `core/`.
5. **One command per file** in `commands/`. Each module exports a `run_<command>()` function called by `cli.py`.

### Adding a New CLI Command

1. Create `src/napoln/commands/mycommand.py` with a `run_mycommand()` function.
2. Register it in `src/napoln/cli.py`.
3. Add integration tests in `tests/integration/test_cli.py`.
4. Add a BDD scenario in `tests/features/` if the command has user-facing workflow implications.

### Adding a New Agent

1. Add an `AgentConfig` entry to `AGENTS` in `src/napoln/core/agents.py`.
2. Add detection logic in `detect_agents()`.
3. Add parametrized test cases in `tests/unit/test_agents.py`.
4. Update the "Supported Agents" table in `README.md`.

## Architecture

Read [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions, store layout, merge strategy, and prior art analysis. Key points:

- **Reflink-first placement.** Copy-on-write where the filesystem supports it, full copy fallback elsewhere. No hardlinks (skills are mutable).
- **Content-addressed store** at `~/.napoln/store/{name}/{version}-{hash}/`. Immutable after write.
- **Three-way merge on upgrade** using `git merge-file`. Conflicts leave markers in the working copy and keep the manifest at the old version so the user can re-run upgrade after resolving.
- **Agent path deduplication.** Gemini CLI, pi, and Codex share `~/.agents/skills/` — one placement serves all three.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add napoln search command
fix: don't update manifest when upgrade has conflicts
test: BDD coverage for three-way merge cases
refactor: parametrize duplicated test patterns
docs: update ARCHITECTURE.md
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
