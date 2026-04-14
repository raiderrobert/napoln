# CLI Redesign Spec

## Overview

Reduce napoln from 13 commands to 7. Every command has a clear, non-overlapping purpose. No dead code (telemetry). No rarely-used plumbing cluttering the top-level help (`gc`, `resolve`, `doctor`, `diff`).

### Before (13 commands)

```
add, remove, upgrade, status, diff, resolve, sync, install, doctor, gc, list, config, telemetry
```

### After (7 commands)

```
add, remove, upgrade, list, install, init, config
```

### What was cut and where it went

| Cut | Disposition |
|-----|------------|
| `status` | Replaced by `list` (shows installed skills with placements) |
| `diff` | Cut entirely. Users can diff files themselves. |
| `resolve` | Cut. Upgrade already writes conflict markers; user resolves manually, re-runs `upgrade`. |
| `sync` | Merged into `install`. |
| `doctor` | Folded into `config doctor`. |
| `gc` | Folded into `config gc`. |
| `telemetry` | Cut entirely. Dead code, no backend. Re-add when there's a real implementation. |

---

## Command: `add`

Install skills from a git source or local path.

### Usage

```
napoln add <source> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `source` | Yes | Git shorthand (`owner/repo`), full URL, or local path (`./my-skill`) |

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--all` | `-a` | Install all skills from a multi-skill repo (no picker) |
| `--skill <name>` | `-s` | Install a specific skill by name from a multi-skill repo |
| `--project` | `-p` | Install to the current project instead of globally |
| `--agents <list>` | | Override auto-detected agents (comma-separated) |
| `--version <ver>` | | Pin to a specific version/tag/branch |
| `--name <name>` | | Override the skill name |
| `--dry-run` | | Show what would happen without applying |

### Behavior

1. **Parse source.** Determine if it's local, git, or registry (registry → error, not yet available).
2. **Resolve.** Clone/fetch the git repo (or read local path). Determine what skills are available.
3. **Skill selection:**
   - Single-skill repo → install it.
   - Multi-skill repo + `--all` → install all.
   - Multi-skill repo + `--skill <name>` → install that one.
   - Multi-skill repo + no flag + TTY → interactive checkbox picker with descriptions.
   - Multi-skill repo + no flag + non-TTY → install all (CI fallback).
4. **Detect agents.** Auto-detect installed agents unless `--agents` overrides.
5. **Store.** Hash contents, store in `~/.napoln/store/{name}/{version}-{hash}/`.
6. **Place.** Reflink (or copy fallback) into each agent's skill directory.
7. **Update manifest.** Record skill, version, hash, source, placements.
8. **Summary.** For multi-skill installs, show summary before installing (skill list, agents, scope).

### Scope

- Default: **global** (`~/.napoln/manifest.toml`, skills placed in `~/.claude/skills/`, etc.)
- With `--project`: project-scoped (`.napoln/manifest.toml`, skills placed in `.claude/skills/` relative to project root)

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (resolution failed, validation failed, etc.) |
| 2 | Installed with warnings (validation warnings) |

### Examples

```bash
napoln add owner/repo                    # single-skill repo → install it
napoln add owner/repo                    # multi-skill repo → interactive picker
napoln add owner/repo --all              # multi-skill repo → install all
napoln add owner/repo --skill rust       # multi-skill repo → install just 'rust'
napoln add owner/repo --project          # install to current project
napoln add owner/repo@v1.2.0            # pin to a version
napoln add ./my-local-skill              # local path
napoln add owner/repo --dry-run          # preview only
```

---

## Command: `remove`

Remove an installed skill.

### Usage

```
napoln remove <name> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Skill name to remove |

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--project` | `-p` | Remove from project scope |
| `--agents <list>` | | Remove from specific agents only |
| `--dry-run` | | Show what would happen |

### Behavior

1. Look up skill in the manifest (global or project based on `--project`).
2. If not found, print error and exit 1.
3. Delete placement directories from each agent.
4. Remove skill entry from manifest.
5. Store entries are left in place (cleaned up by `config gc`).

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Skill not found |

### Examples

```bash
napoln remove code-review               # remove globally-installed skill
napoln remove rust --project             # remove project-scoped skill
napoln remove code-review --dry-run      # preview
```

---

## Command: `upgrade`

Upgrade one or all skills to their latest upstream version.

### Usage

```
napoln upgrade [<name>] [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | No | Skill to upgrade. If omitted, upgrade all. |

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--project` | `-p` | Upgrade project-scoped skills |
| `--version <ver>` | | Upgrade to a specific version |
| `--agents <list>` | | Upgrade for specific agents only |
| `--force` | | Replace working copies without three-way merge |
| `--dry-run` | | Show what would happen |

### Behavior

1. For each skill being upgraded:
   a. Re-resolve the source to get the latest version.
   b. If the content hash is unchanged, skip ("already up to date").
   c. Store the new version.
   d. For each agent placement, perform a three-way merge:
      - **OURS == BASE** (no local changes) → fast-forward (replace with reflink of new version).
      - **OURS != BASE, no conflicts** → apply merge, write result.
      - **OURS != BASE, conflicts** → write conflict markers, report, keep manifest at old version.
      - **Non-markdown files** → replace if unchanged, keep + warn if modified.
2. Only update manifest version/hash if there are no conflicts.
3. If conflicts occurred, exit 2 and tell user to resolve and re-run.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All upgrades clean |
| 1 | Resolution error |
| 2 | Upgraded with conflicts (conflict markers written) |

### Examples

```bash
napoln upgrade                           # upgrade all global skills
napoln upgrade code-review               # upgrade one skill
napoln upgrade --project                 # upgrade all project skills
napoln upgrade code-review --force       # replace without merging
napoln upgrade code-review --version v2  # pin to specific version
napoln upgrade --dry-run                 # preview
```

---

## Command: `list`

Show installed skills with their versions and placement paths.

### Usage

```
napoln list [options]
```

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--project` | `-p` | Show only project skills |
| `--global` | `-g` | Show only global skills |
| `--json` | | Machine-readable JSON output |

### Behavior

1. Read the global manifest (`~/.napoln/manifest.toml`).
2. If in a directory with a project manifest (`.napoln/manifest.toml`), read that too.
3. Display skills grouped by scope.
4. For each skill, show: name, version, source, and placement paths (abbreviated).
5. If no skills are installed, say so.

### Default behavior (no flags)

Show both global and project skills (if a project manifest exists).

### Output format

```
Global:
  cite-check          v0.1.11  raiderrobert/sauce   ~/.claude/  ~/.agents/  ~/.cursor/
  writing-skills      v0.1.11  raiderrobert/sauce   ~/.claude/  ~/.agents/  ~/.cursor/
  napoln-manage       v0.1.0   bundled              ~/.claude/  ~/.agents/  ~/.cursor/

Project (/Users/robert/repos/myapp):
  rust                v0.2.12  raiderrobert/flow    .claude/  .agents/
  design-frontend     v0.2.12  raiderrobert/flow    .claude/  .agents/
```

Placement paths are shortened: `~/.claude/skills/cite-check` → `~/.claude/` (the skill name is already on the line).

### JSON output

```json
{
  "global": {
    "cite-check": {
      "version": "0.1.11",
      "source": "github.com/raiderrobert/sauce/skills/cite-check",
      "agents": {
        "claude-code": {"path": "~/.claude/skills/cite-check", "link_mode": "clone"},
        "gemini-cli": {"path": "~/.agents/skills/cite-check", "link_mode": "clone"}
      }
    }
  },
  "project": {}
}
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Always (even if empty) |

### Examples

```bash
napoln list                              # show all (global + project)
napoln list --global                     # global only
napoln list --project                    # project only
napoln list --json                       # machine-readable
```

---

## Command: `install`

Restore skill placements from manifests. Reads all available manifests and ensures every skill has its placements in the correct agent directories.

### Usage

```
napoln install [options]
```

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--project` | `-p` | Sync only the project manifest |
| `--global` | `-g` | Sync only the global manifest |
| `--dry-run` | | Show what would happen |

### Behavior

1. Read the global manifest (`~/.napoln/manifest.toml`). For each skill:
   a. Look up the store entry by name, version, and hash.
   b. For each agent placement, check if the placement directory exists.
   c. If missing, re-place from the store (reflink/copy).
   d. If the store entry is also missing, warn (can't restore without re-adding).
2. If a project manifest exists (`.napoln/manifest.toml` in current directory or ancestors), do the same for project skills.
3. Report what was synced.

### Default behavior (no flags)

Sync **both** global and project manifests. If only one exists, sync that one.

### Output

```
$ napoln install
✓ Synced 8 global skills (all up to date)
✓ Synced 2 project skills (1 restored)
```

Or on a fresh machine after restoring dotfiles:

```
$ napoln install
✓ Synced 8 global skills (8 restored)
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All synced |
| 1 | Some skills could not be restored (missing store entries) |

### Examples

```bash
napoln install                           # sync everything
napoln install --project                 # project only
napoln install --global                  # global only
napoln install --dry-run                 # preview
```

---

## Command: `init`

Scaffold a new skill directory with a `SKILL.md` template.

### Usage

```
napoln init [<name>] [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | No | Skill name. If omitted, uses current directory name. |

### Behavior

1. If `name` is given:
   - Create `<name>/SKILL.md` in the current directory.
2. If `name` is omitted:
   - Create `SKILL.md` in the current directory.
   - Use the current directory's name as the skill name.
3. If `SKILL.md` already exists at the target location, error (don't overwrite).
4. Write a template with frontmatter and a body outline.

### Template

```markdown
---
name: <name>
description: <empty — fill this in>
---

# <Name>

Describe what this skill does and when to use it.

## Instructions

1. Step one
2. Step two
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Created |
| 1 | SKILL.md already exists |

### Examples

```bash
napoln init my-skill                     # creates my-skill/SKILL.md
napoln init                              # creates ./SKILL.md using dir name
```

---

## Command: `config`

View and edit napoln configuration. Also provides housekeeping subcommands.

### Usage

```
napoln config                            # show current config
napoln config set <key> <value>          # set a value
napoln config doctor                     # health check
napoln config gc                         # garbage collect
```

### Subcommands

#### `config` (no subcommand)

Show current configuration: napoln home, store path, detected agents, manifest locations.

```
$ napoln config
Home:      ~/.napoln
Store:     ~/.napoln/store (42 entries, 1.2 MB)
Agents:    Claude Code, Gemini CLI, pi, Cursor
Global:    ~/.napoln/manifest.toml (8 skills)
Project:   (none)
```

#### `config set <key> <value>`

Set a configuration value in `~/.napoln/config.toml`.

```bash
napoln config set default_scope project
napoln config set default_agents claude-code,pi
```

#### `config doctor`

Health check. Verify store integrity, check for missing placements, detect orphaned entries.

```
$ napoln config doctor
✓ Store integrity: 42 entries, all valid
✓ Placements: 24 placements, all present
⚠ 2 unreferenced store entries (run 'napoln config gc' to clean up)
```

Options:
- `--json` — machine-readable output

#### `config gc`

Remove unreferenced store entries (versions no longer in any manifest).

```
$ napoln config gc
Removed 2 unreferenced store entries (saved 45 KB)
```

Options:
- `--dry-run` — show what would be removed

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid key, etc.) |

---

## Top-level help

```
$ napoln --help
Usage: napoln [OPTIONS] COMMAND [ARGS]...

  A package manager for agent skills.

Commands:
  add       Install skills from a git repo or local path.
  remove    Remove an installed skill.
  upgrade   Upgrade one or all skills.
  list      Show installed skills and where they are placed.
  install   Restore skill placements from manifests.
  init      Scaffold a new SKILL.md.
  config    View configuration and run housekeeping.

Options:
  --version  Show napoln version.
  --help     Show this message and exit.
```

No `--install-completion` or `--show-completion` in the help (hide them or remove them — they add noise).

---

## BDD Scenarios

### Feature: Add a skill

```gherkin
Feature: Add skills
  As a developer
  I want to install agent skills from git repos and local paths
  So that my coding agents have the capabilities I need

  Scenario: Add a single-skill repo
    Given Claude Code is installed
    When I run napoln add with a local single-skill source
    Then the skill is stored in the content-addressed store
    And the skill is placed in the Claude Code skills directory
    And the manifest records the skill with version and hash
    And the exit code is 0

  Scenario: Add from a multi-skill repo with --all
    Given Claude Code is installed
    When I run napoln add with a local multi-skill source and --all
    Then all skills from the repo are installed
    And the manifest records each skill separately
    And the exit code is 0

  Scenario: Add from a multi-skill repo with --skill
    Given Claude Code is installed
    When I run napoln add with a local multi-skill source and --skill "skill-a"
    Then only "skill-a" is installed
    And the exit code is 0

  Scenario: Add from a multi-skill repo with interactive picker (non-TTY fallback)
    Given Claude Code is installed
    And stdin is not a TTY
    When I run napoln add with a local multi-skill source
    Then all skills from the repo are installed
    And the exit code is 0

  Scenario: Add with --project installs to project scope
    Given Claude Code is installed
    And the current directory is a project
    When I run napoln add with a local skill and --project
    Then the skill is placed in the project's agent skill directory
    And the project manifest records the skill
    And the global manifest does not contain the skill
    And the exit code is 0

  Scenario: Add an already-installed skill is idempotent
    Given Claude Code is installed
    And a skill "test-skill" is already installed at version "1.0.0"
    When I run napoln add with the same source
    Then the output says the skill is already installed
    And the exit code is 0

  Scenario: Add with --dry-run makes no changes
    Given Claude Code is installed
    When I run napoln add with a local skill and --dry-run
    Then no files are written to the store
    And no files are placed in agent directories
    And no manifest is created
    And the output describes what would happen
    And the exit code is 0
```

### Feature: Remove a skill

```gherkin
Feature: Remove skills
  As a developer
  I want to remove skills I no longer need
  So that my agents don't have stale or unwanted instructions

  Scenario: Remove an installed skill
    Given a skill "test-skill" is installed globally
    When I run napoln remove test-skill
    Then the placement directories are deleted from all agents
    And the skill is removed from the global manifest
    And the store entry is left in place
    And the exit code is 0

  Scenario: Remove a skill that is not installed
    Given no skills are installed
    When I run napoln remove nonexistent
    Then the output says the skill is not installed
    And the exit code is 1

  Scenario: Remove with --project removes from project scope
    Given a skill "test-skill" is installed in the project
    When I run napoln remove test-skill --project
    Then the skill is removed from the project manifest
    And the global manifest is not modified
    And the exit code is 0

  Scenario: Remove with --dry-run makes no changes
    Given a skill "test-skill" is installed globally
    When I run napoln remove test-skill --dry-run
    Then the placement directories still exist
    And the manifest still contains the skill
    And the exit code is 0
```

### Feature: Upgrade with three-way merge

```gherkin
Feature: Upgrade skills
  As a developer who has customized a skill
  I want to upgrade without losing my changes
  So that I get upstream improvements while keeping my customizations

  # Case (a): OURS == BASE → fast-forward
  Scenario: Fast-forward when no local changes
    Given Claude Code is installed
    And a skill "test-skill" is installed at version "1.0.0"
    And the Claude Code placement is unmodified
    And upstream has released version "2.0.0" with a new section
    When I run napoln upgrade test-skill
    Then the Claude Code placement contains the new upstream content
    And the Claude Code placement does not contain conflict markers
    And the manifest version is "2.0.0"
    And the exit code is 0

  # Case (b): OURS != BASE, no conflicts with THEIRS → clean merge
  Scenario: Clean merge when local and upstream changes do not overlap
    Given Claude Code is installed
    And a skill "test-skill" is installed at version "1.0.0"
    And the Claude Code placement has local changes at the end
    And upstream has released version "2.0.0" with changes at the beginning
    When I run napoln upgrade test-skill
    Then the Claude Code placement contains both local and upstream changes
    And the Claude Code placement does not contain conflict markers
    And the exit code is 0

  # Case (c): OURS != BASE, conflicts with THEIRS → conflict markers
  Scenario: Conflict when local and upstream change the same lines
    Given Claude Code is installed
    And a skill "test-skill" is installed at version "1.0.0"
    And the Claude Code placement has local changes on line 5
    And upstream has released version "2.0.0" with different changes on line 5
    When I run napoln upgrade test-skill
    Then the Claude Code placement contains conflict markers
    And the manifest version is "1.0.0"
    And the output contains "Conflicts"
    And the exit code is 2

  # Case (d): non-SKILL.md files → replace if unchanged, warn if modified
  Scenario: Supporting files replaced if unchanged
    Given Claude Code is installed
    And a skill "test-skill" with a script is installed at version "1.0.0"
    And the script in the Claude Code placement is unmodified
    And upstream has released version "2.0.0" with an updated script
    When I run napoln upgrade test-skill
    Then the script in the Claude Code placement matches the new upstream
    And the exit code is 0

  Scenario: Supporting files kept when locally modified
    Given Claude Code is installed
    And a skill "test-skill" with a script is installed at version "1.0.0"
    And the script in the Claude Code placement has local changes
    And upstream has released version "2.0.0" with an updated script
    When I run napoln upgrade test-skill
    Then the script in the Claude Code placement retains local changes
    And the manifest version is "1.0.0"
    And the exit code is 2

  Scenario: Upgrade all skills at once
    Given Claude Code is installed
    And skills "alpha" and "beta" are installed
    When I run napoln upgrade
    Then both skills are checked for updates
    And the exit code is 0
```

### Feature: List installed skills

```gherkin
Feature: List installed skills
  As a developer
  I want to see what skills are installed and where
  So that I can understand what my agents have access to

  Scenario: List with no skills installed
    When I run napoln list
    Then the output says no skills are installed
    And the exit code is 0

  Scenario: List global skills
    Given skills "alpha" and "beta" are installed globally
    When I run napoln list
    Then the output shows "alpha" with its version and placement paths
    And the output shows "beta" with its version and placement paths
    And the output groups them under "Global"
    And the exit code is 0

  Scenario: List shows both global and project skills
    Given a skill "global-skill" is installed globally
    And a skill "project-skill" is installed in the project
    When I run napoln list
    Then the output shows "global-skill" under "Global"
    And the output shows "project-skill" under "Project"
    And the exit code is 0

  Scenario: List with --global shows only global skills
    Given a skill "global-skill" is installed globally
    And a skill "project-skill" is installed in the project
    When I run napoln list --global
    Then the output shows "global-skill"
    And the output does not show "project-skill"
    And the exit code is 0

  Scenario: List with --json produces machine-readable output
    Given a skill "test-skill" is installed globally
    When I run napoln list --json
    Then the output is valid JSON
    And the JSON contains a "global" key with "test-skill"
    And the exit code is 0
```

### Feature: Install from manifests

```gherkin
Feature: Install from manifests
  As a developer joining a project or setting up a new machine
  I want to restore all skills from manifests
  So that my agents are configured correctly

  Scenario: Install restores global skills on a fresh machine
    Given a global manifest exists with skills "alpha" and "beta"
    And the store contains both skills
    And no placements exist
    When I run napoln install
    Then "alpha" is placed in all agent directories
    And "beta" is placed in all agent directories
    And the output reports 2 skills restored
    And the exit code is 0

  Scenario: Install restores project skills
    Given a project manifest exists with skill "rust"
    And the store contains "rust"
    And no project placements exist
    When I run napoln install
    Then "rust" is placed in project agent directories
    And the exit code is 0

  Scenario: Install syncs both global and project
    Given a global manifest with skill "alpha"
    And a project manifest with skill "beta"
    And the store contains both
    When I run napoln install
    Then "alpha" is placed globally
    And "beta" is placed in the project
    And the exit code is 0

  Scenario: Install when placements already exist
    Given a global manifest with skill "alpha"
    And "alpha" is already placed correctly
    When I run napoln install
    Then the output says all skills are up to date
    And the exit code is 0

  Scenario: Install with missing store entry
    Given a global manifest with skill "alpha"
    And the store does not contain "alpha"
    When I run napoln install
    Then the output warns that "alpha" cannot be restored
    And the exit code is 1
```

### Feature: Init a skill

```gherkin
Feature: Initialize a skill
  As a skill author
  I want to scaffold a new skill quickly
  So that I have the correct structure from the start

  Scenario: Init with a name creates a subdirectory
    When I run napoln init my-skill
    Then a directory "my-skill" is created
    And "my-skill/SKILL.md" exists
    And the SKILL.md contains "name: my-skill" in the frontmatter
    And the exit code is 0

  Scenario: Init without a name uses current directory
    Given the current directory is named "cool-skill"
    And no SKILL.md exists in the current directory
    When I run napoln init
    Then "SKILL.md" is created in the current directory
    And the SKILL.md contains "name: cool-skill" in the frontmatter
    And the exit code is 0

  Scenario: Init refuses to overwrite existing SKILL.md
    Given a SKILL.md already exists
    When I run napoln init
    Then the output says SKILL.md already exists
    And the existing SKILL.md is not modified
    And the exit code is 1
```

### Feature: Config and housekeeping

```gherkin
Feature: Configuration and housekeeping
  As a developer
  I want to view my napoln configuration and clean up storage
  So that I can understand and maintain my setup

  Scenario: Show config
    Given napoln is initialized
    When I run napoln config
    Then the output shows the napoln home path
    And the output shows detected agents
    And the exit code is 0

  Scenario: Set a config value
    Given napoln is initialized
    When I run napoln config set default_scope project
    Then the config file contains the new value
    And the exit code is 0

  Scenario: Doctor reports healthy state
    Given skills are installed and placements are valid
    When I run napoln config doctor
    Then the output reports all checks passed
    And the exit code is 0

  Scenario: GC removes unreferenced store entries
    Given a skill was installed then removed
    And the store still contains the old version
    When I run napoln config gc
    Then the unreferenced store entry is deleted
    And the output reports how many entries were removed
    And the exit code is 0

  Scenario: GC with --dry-run shows what would be removed
    Given a skill was installed then removed
    And the store still contains the old version
    When I run napoln config gc --dry-run
    Then the store entry is not deleted
    And the output shows what would be removed
    And the exit code is 0
```

---

## Migration

### Files to modify

| File | Change |
|------|--------|
| `src/napoln/cli.py` | Rewrite: 7 commands, hide completion flags |
| `src/napoln/commands/list_cmd.py` | Rewrite: show installed skills, not preview a repo |
| `src/napoln/commands/sync.py` | Rename to `install.py`, add dual-manifest sync |
| `src/napoln/commands/init.py` | New: scaffold SKILL.md |
| `src/napoln/commands/config.py` | Expand: add `doctor` and `gc` subcommands |

### Files to delete

| File | Reason |
|------|--------|
| `src/napoln/commands/diff.py` | Command cut |
| `src/napoln/commands/resolve.py` | Command cut |
| `src/napoln/commands/status.py` | Replaced by `list` |
| `src/napoln/commands/telemetry_cmd.py` | Dead code, cut |
| `src/napoln/telemetry.py` | Dead code, cut |

### Test updates

| Test file | Change |
|-----------|--------|
| `tests/features/upgrade.feature` | Keep as-is (already covers merge cases) |
| `tests/features/install.feature` | Rewrite for new install behavior |
| `tests/features/status_and_diff.feature` | Delete, replace with `list.feature` |
| `tests/features/first_run.feature` | Update for new command set |
| `tests/integration/test_cli.py` | Rewrite for 7 commands |
| New: `tests/features/list.feature` | BDD scenarios for list |
| New: `tests/features/init.feature` | BDD scenarios for init |
| New: `tests/features/config.feature` | BDD scenarios for config |
