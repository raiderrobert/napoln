# User Stories & Command Examples

## Part 1: BDD Stories

---

### Story 1: First-Time User Installs a Skill

```gherkin
Feature: First run experience
  As a developer using Claude Code and Gemini CLI
  I want to install my first skill with minimal friction
  So that I can extend my agents' capabilities

  Background:
    Given I have Claude Code installed at ~/.claude/
    And I have Gemini CLI installed at ~/.gemini/
    And I have never run napoln before
    And ~/.napoln/ does not exist

  Scenario: First run bootstraps napoln and installs a skill
    When I run "napoln add owner/code-review"
    Then napoln creates ~/.napoln/ with config.toml and manifest.toml
    And napoln prompts me about telemetry opt-in
    And napoln detects Claude Code and Gemini CLI as installed agents
    And napoln clones the git repo "github.com/owner/code-review"
    And napoln validates the SKILL.md in the repo
    And napoln stores the pristine upstream in ~/.napoln/store/code-review/1.0.0-a3b2c1d/
    And napoln places a working copy at ~/.claude/skills/code-review/ via reflink
    And napoln places a working copy at ~/.agents/skills/code-review/ via reflink
    And napoln installs the napoln-manage bootstrap skill to both agents
    And napoln writes ~/.napoln/manifest.toml with both skills
    And the exit code is 0

  Scenario: First run on a system without reflink support
    Given the filesystem does not support reflink
    When I run "napoln add owner/code-review"
    Then napoln falls back to copy for all placements
    And the .napoln provenance file records link_mode = "copy"
    And the manifest records link_mode = "copy" for each agent
    And a note is printed: "Using copy mode (reflink not supported on this filesystem)"
    And the exit code is 0

  Scenario: First run with no agents detected
    Given ~/.claude/ does not exist
    And ~/.gemini/ does not exist
    And ~/.pi/ does not exist
    When I run "napoln add owner/code-review"
    Then napoln prints "No agents detected. Use --agents to specify targets."
    And napoln prints "  Supported: claude-code, gemini-cli, pi"
    And the exit code is 1
```

---

### Story 2: Browsing Before Installing

```gherkin
Feature: Listing skills in a repository
  As a developer evaluating a skill repo
  I want to see what skills are available before installing
  So that I can choose which ones I need

  Scenario: List skills in a multi-skill repo
    Given the repo "owner/agent-skills" contains:
      | Skill            | Version | Description                          |
      | code-review      | 1.0.0   | Structured code review workflow      |
      | test-generator   | 2.1.0   | Generate tests from implementation   |
      | deploy-checklist | 1.3.0   | Pre-deployment safety checklist      |
    When I run "napoln list owner/agent-skills"
    Then napoln clones the repo to cache
    And napoln prints a table of available skills with names, versions, and descriptions
    And the exit code is 0

  Scenario: List skills in a single-skill repo
    Given the repo "owner/code-review" is a root-level skill
    When I run "napoln list owner/code-review"
    Then napoln prints the single skill's name, version, and description
    And the exit code is 0
```

---

### Story 3: Installing a Specific Skill from a Multi-Skill Repo

```gherkin
Feature: Selective installation from multi-skill repos
  As a developer who only needs certain skills
  I want to install specific skills from a multi-skill repo
  So that I don't clutter my agents with skills I don't need

  Scenario: Install one skill by name
    Given the repo "owner/agent-skills" contains skills: code-review, test-generator, deploy-checklist
    When I run "napoln add owner/agent-skills --skill code-review"
    Then only code-review is installed
    And test-generator and deploy-checklist are not installed
    And the manifest contains only code-review

  Scenario: Install all skills
    When I run "napoln add owner/agent-skills --skill '*'"
    Then all three skills are installed
    And each has its own entry in the manifest

  Scenario: Install to a specific agent only
    When I run "napoln add owner/agent-skills --skill code-review --agents claude-code"
    Then code-review is placed only in ~/.claude/skills/code-review/
    And ~/.agents/skills/code-review/ is NOT created
    And the manifest records only a claude-code agent entry
```

---

### Story 4: Viewing Installed Skills and Modifications

```gherkin
Feature: Status and diff
  As a developer who has customized some skills
  I want to see which skills I've modified
  So that I know what will need merging on upgrade

  Background:
    Given I have installed "code-review" v1.0.0 for claude-code and gemini-cli
    And I have edited ~/.claude/skills/code-review/SKILL.md to add security review steps
    And I have NOT edited ~/.agents/skills/code-review/SKILL.md

  Scenario: Status shows modification state per agent
    When I run "napoln status"
    Then I see code-review listed with:
      | Agent       | Path                              | State    |
      | claude-code | ~/.claude/skills/code-review      | modified |
      | gemini-cli  | ~/.agents/skills/code-review      | clean    |

  Scenario: Diff shows what changed
    When I run "napoln diff code-review --agent claude-code"
    Then I see a unified diff of my changes against the upstream version
    And the diff header shows "store (upstream v1.0.0)" vs "working copy"

  Scenario: Diff for unmodified placement
    When I run "napoln diff code-review --agent gemini-cli"
    Then I see "No local modifications."
```

---

### Story 5: Upgrading a Customized Skill

```gherkin
Feature: Upgrade with three-way merge
  As a developer who has customized a skill
  I want to upgrade to a new version without losing my changes
  So that I get upstream improvements while keeping my customizations

  Background:
    Given I have installed "code-review" v1.0.0 for claude-code and gemini-cli
    And I have customized the claude-code placement (added security review steps)
    And the gemini-cli placement is unmodified
    And upstream has released v1.1.0 with a new "performance review" section

  Scenario: Dry run shows what would happen
    When I run "napoln upgrade code-review --dry-run"
    Then I see the new version (1.1.0) and a summary of changes
    And I see that the gemini-cli placement will be fast-forwarded (no local changes)
    And I see that the claude-code placement will be merged (local + upstream changes)
    And no files are modified on disk
    And the manifest is not updated

  Scenario: Upgrade with clean merge
    Given my customizations do not conflict with the upstream changes
    When I run "napoln upgrade code-review"
    Then the gemini-cli placement is replaced with a reflink of the new version (fast-forward)
    And the claude-code placement is three-way merged (my changes + upstream changes)
    And the store now contains v1.1.0
    And the manifest is updated to version 1.1.0
    And the exit code is 0

  Scenario: Upgrade with merge conflict
    Given my customizations conflict with the upstream changes on the same lines
    When I run "napoln upgrade code-review"
    Then the gemini-cli placement is fast-forwarded
    And the claude-code placement has conflict markers in SKILL.md
    And napoln prints "Conflicts in code-review for claude-code. Resolve and run: napoln resolve code-review"
    And the manifest is updated to version 1.1.0 with a "conflicted" flag
    And the exit code is 2

  Scenario: Resolving conflicts
    Given code-review has unresolved conflicts in the claude-code placement
    And I have edited the file to remove all conflict markers
    When I run "napoln resolve code-review"
    Then napoln verifies no conflict markers remain
    And the conflicted flag is removed from the manifest
    And the exit code is 0

  Scenario: Force upgrade discards local changes
    When I run "napoln upgrade code-review --force"
    Then all placements are replaced with reflinks of the new version
    And all local customizations are lost
    And the exit code is 0
```

---

### Story 6: Team Workflow with Project-Level Skills

```gherkin
Feature: Project-level skills shared via git
  As a team lead
  I want to define shared skills for my project
  So that all team members have the same agent capabilities

  Scenario: Adding a project-level skill
    Given I am in a git repository at ~/projects/my-app/
    When I run "napoln add owner/deploy-checklist --project"
    Then napoln creates .napoln/manifest.toml in the project root
    And napoln places the skill in .claude/skills/deploy-checklist/
    And napoln places the skill in .agents/skills/deploy-checklist/

  Scenario: Teammate clones and installs
    Given my teammate has cloned ~/projects/my-app/
    And .napoln/manifest.toml is committed in the repo
    And .claude/skills/ and .agents/skills/ are in .gitignore
    When my teammate runs "napoln install" in the project root
    Then napoln reads .napoln/manifest.toml
    And napoln fetches deploy-checklist from the recorded git source
    And napoln stores it and places working copies for detected agents
    And the teammate has the same skills I do

  Scenario: Teammate has different agents installed
    Given my teammate only has pi installed (no Claude Code or Gemini CLI)
    When my teammate runs "napoln install" in the project root
    Then napoln places the skill only in .agents/skills/deploy-checklist/
    And napoln does NOT create .claude/skills/ (agent not detected)
```

---

### Story 7: Health Check and Repair

```gherkin
Feature: Diagnostics and self-healing
  As a developer whose setup might have gotten into a weird state
  I want to verify and repair my napoln installation
  So that everything works correctly

  Scenario: Doctor finds no issues
    When I run "napoln doctor"
    Then all checks pass
    And the exit code is 0

  Scenario: Doctor finds a missing placement
    Given I accidentally deleted ~/.claude/skills/code-review/
    When I run "napoln doctor"
    Then napoln reports "Missing placement: code-review → ~/.claude/skills/code-review"
    And suggests "Run 'napoln sync' to repair"
    And the exit code is 2

  Scenario: Sync repairs missing placements
    Given ~/.claude/skills/code-review/ was accidentally deleted
    When I run "napoln sync"
    Then napoln re-creates the placement from the store via reflink
    And prints "Restored: code-review → ~/.claude/skills/code-review"

  Scenario: Doctor finds store corruption
    Given someone manually edited a file in ~/.napoln/store/
    When I run "napoln doctor"
    Then napoln reports "Store integrity failure: code-review/1.0.0-a3b2c1d (hash mismatch)"
    And suggests "Run 'napoln upgrade code-review --force' to re-fetch"

  Scenario: Doctor finds untracked skills
    Given I manually created ~/.claude/skills/my-custom-thing/SKILL.md
    When I run "napoln doctor"
    Then napoln reports "Untracked skill: my-custom-thing in ~/.claude/skills/"
    And does NOT try to modify or remove it
```

---

### Story 8: Garbage Collection

```gherkin
Feature: Cleaning up old store versions
  As a developer who has upgraded skills several times
  I want to reclaim disk space from old versions
  So that my store doesn't grow unbounded

  Scenario: GC with dry run
    Given the store contains code-review v1.0.0, v1.1.0, and v1.2.0
    And the manifest references only v1.2.0
    When I run "napoln gc --dry-run"
    Then napoln lists v1.0.0 and v1.1.0 as removable
    And no files are deleted

  Scenario: GC removes unreferenced versions
    When I run "napoln gc"
    Then v1.0.0 and v1.1.0 are removed from the store
    And v1.2.0 is retained
```

---

## Part 2: Command Output Examples

### Example 1: `napoln --help`

```
$ napoln --help

 Usage: napoln [OPTIONS] COMMAND [ARGS]...

 A quality-first skill manager for AI coding agents.

╭─ Commands ──────────────────────────────────────────────────────────────────╮
│                                                                            │
│  add        Install a skill from a git repo or local path                  │
│  remove     Remove an installed skill                                      │
│  upgrade    Upgrade one or all installed skills                            │
│  status     Show installed skills and their state                          │
│  diff       Show local modifications vs. upstream                         │
│  resolve    Mark a skill's merge conflicts as resolved                    │
│  list       List available skills in a source                              │
│  install    Install all skills from a project manifest                    │
│  sync       Re-create missing placements from manifest + store            │
│  doctor     Verify store integrity and placement health                   │
│  gc         Remove unreferenced store entries                              │
│  config     View or edit napoln configuration                              │
│  telemetry  Manage telemetry settings                                      │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────╮
│                                                                            │
│  --verbose, -v    Verbose output                                           │
│  --quiet, -q      Suppress non-error output                                │
│  --json           Machine-readable JSON output                             │
│  --no-color       Disable colored output                                   │
│  --version        Show version and exit                                    │
│  --help, -h       Show this message and exit                               │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯

 Quick start:
   napoln add owner/repo              Install a skill from GitHub
   napoln status                      See what's installed
   napoln upgrade                     Upgrade all skills
```

```
$ napoln add --help

 Usage: napoln add [OPTIONS] SOURCE

 Install a skill from a git repo or local path.

 SOURCE can be:
   owner/repo                         GitHub shorthand
   owner/repo/path/to/skill           Specific skill in a repo
   owner/repo@v1.2.0                  Pinned to a version tag
   github.com/owner/repo              Full hostname
   https://gitlab.com/owner/repo      Any git host
   ./path/to/local/skill              Local directory

╭─ Options ──────────────────────────────────────────────────────────────────╮
│                                                                            │
│  --agents, -a  TEXT    Target agents: claude-code, gemini-cli, pi          │
│                        Comma-separated. Default: auto-detect               │
│  --version     TEXT    Version constraint (tag, branch, or semver range)   │
│  --skill       TEXT    Select specific skill from a multi-skill repo       │
│                        Use '*' for all skills                              │
│  --global              Install globally [default]                          │
│  --project             Install to current project                          │
│  --dry-run             Show what would be installed without doing it       │
│  --help, -h            Show this message and exit                          │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯

 Examples:
   napoln add anthropics/skills --skill code-review
   napoln add owner/repo@v2.0 --agents claude-code
   napoln add ./my-local-skill --project
```

---

### Example 2: `napoln add` (First Run)

```
$ napoln add anthropics/skills --skill code-review

  Initializing napoln...
  Created ~/.napoln/

  Telemetry
  napoln can collect anonymous usage data (commands used, OS, success/failure).
  Never collected: skill names, file paths, repo URLs, or personal info.
  Run 'napoln telemetry show-data' at any time to see exactly what's sent.

  Enable telemetry? [y/N]: N

  Telemetry disabled. You can change this later with 'napoln telemetry enable'.

  Detecting agents...
  ✓ Claude Code   ~/.claude/
  ✓ Gemini CLI    ~/.gemini/
  ✗ pi            not found

  Fetching anthropics/skills...
  ✓ Cloned github.com/anthropics/skills (main @ e4a7b23)

  Validating code-review...
  ✓ SKILL.md valid (name: code-review, v1.0.0)

  Storing...
  ✓ Stored code-review/1.0.0-a3b2c1d

  Placing working copies...
  ✓ ~/.claude/skills/code-review/    clone (copy-on-write)
  ✓ ~/.agents/skills/code-review/    clone (copy-on-write)

  Installing bootstrap skill...
  ✓ ~/.claude/skills/napoln-manage/  clone (copy-on-write)
  ✓ ~/.agents/skills/napoln-manage/  clone (copy-on-write)

  Installed code-review v1.0.0 for claude-code, gemini-cli
```

---

### Example 3: `napoln add --dry-run`

```
$ napoln add anthropics/skills --skill code-review --dry-run

  Fetching anthropics/skills...
  ✓ Cloned github.com/anthropics/skills (main @ e4a7b23)

  Validating code-review...
  ✓ SKILL.md valid (name: code-review, v1.0.0)

  Dry run — no changes will be made:

  Store:
    Would store: code-review/1.0.0-a3b2c1d (3 files, 4.2 KB)

  Placements:
    Would place: ~/.claude/skills/code-review/   (clone)
    Would place: ~/.agents/skills/code-review/   (clone)

  Manifest:
    Would add entry: code-review v1.0.0
      source:  github.com/anthropics/skills/skills/code-review
      agents:  claude-code (global), gemini-cli (global)

  Run without --dry-run to apply.
```

---

### Example 4: `napoln upgrade --dry-run` and `napoln upgrade`

```
$ napoln upgrade --dry-run

  Checking for updates...

  code-review
    Installed: v1.0.0 (a3b2c1d)
    Available: v1.1.0

    claude-code  ~/.claude/skills/code-review     modified
      → Will merge: local changes (3 lines added) + upstream changes (new section)
      → SKILL.md: 3-way merge required

    gemini-cli   ~/.agents/skills/code-review     clean
      → Will fast-forward: replace with v1.1.0 (no local changes)

  napoln-manage
    Installed: v0.1.0 (bundled)
    Available: v0.1.0
    → Up to date.

  Summary: 1 skill to upgrade, 1 merge required, 0 conflicts expected.
  Run 'napoln upgrade' to apply.
```

```
$ napoln upgrade

  Upgrading code-review v1.0.0 → v1.1.0...

  Fetching anthropics/skills@v1.1.0...
  ✓ Fetched (tag v1.1.0 @ f8c9d12)

  Storing...
  ✓ Stored code-review/1.1.0-b7e3f2a

  Upgrading placements...

  gemini-cli   ~/.agents/skills/code-review
    No local changes — fast-forwarding.
    ✓ Replaced with v1.1.0 (clone)

  claude-code  ~/.claude/skills/code-review
    Local changes detected — merging...
    ✓ Merged cleanly. Your changes preserved:
      SKILL.md: kept 3 added lines (security review steps)
      SKILL.md: added upstream section "Performance Review"

  Upgraded code-review v1.0.0 → v1.1.0

  1 skill upgraded, 0 conflicts.
```

**With a conflict:**

```
$ napoln upgrade

  Upgrading code-review v1.0.0 → v1.1.0...

  Fetching anthropics/skills@v1.1.0...
  ✓ Fetched (tag v1.1.0 @ f8c9d12)

  Storing...
  ✓ Stored code-review/1.1.0-b7e3f2a

  Upgrading placements...

  gemini-cli   ~/.agents/skills/code-review
    No local changes — fast-forwarding.
    ✓ Replaced with v1.1.0 (clone)

  claude-code  ~/.claude/skills/code-review
    Local changes detected — merging...
    ✗ Conflict in SKILL.md (lines 14-22)
      Both you and upstream modified the "Review Steps" section.

  Upgraded code-review v1.0.0 → v1.1.0 (1 conflict)

  To resolve:
    1. Edit ~/.claude/skills/code-review/SKILL.md
       (look for <<<<<<< / ======= / >>>>>>> markers)
    2. Run: napoln resolve code-review
```

---

### Example 5: `napoln status` and `napoln doctor`

```
$ napoln status

  Installed skills (global):

  code-review v1.1.0  github.com/anthropics/skills
  │ claude-code  ~/.claude/skills/code-review     modified
  │ gemini-cli   ~/.agents/skills/code-review     clean
  │
  napoln-manage v0.1.0  (bundled)
  │ claude-code  ~/.claude/skills/napoln-manage    clean
  │ gemini-cli   ~/.agents/skills/napoln-manage    clean

  Installed skills (project ~/projects/my-app):

  deploy-checklist v1.3.0  github.com/owner/repo
  │ claude-code  .claude/skills/deploy-checklist   clean
  │ gemini-cli   .agents/skills/deploy-checklist   clean

  3 skills installed (1 modified).
```

```
$ napoln status --json
{
  "skills": [
    {
      "name": "code-review",
      "version": "1.1.0",
      "source": "github.com/anthropics/skills/skills/code-review",
      "store_hash": "b7e3f2a",
      "scope": "global",
      "agents": {
        "claude-code": {
          "path": "~/.claude/skills/code-review",
          "state": "modified",
          "link_mode": "clone"
        },
        "gemini-cli": {
          "path": "~/.agents/skills/code-review",
          "state": "clean",
          "link_mode": "clone"
        }
      }
    }
  ]
}
```

```
$ napoln doctor

  Store integrity
  ✓ code-review/1.0.0-a3b2c1d    hash valid
  ✓ code-review/1.1.0-b7e3f2a    hash valid
  ✓ napoln-manage/0.1.0-c4d5e6f  hash valid

  Manifest consistency
  ✓ All manifest entries have valid store versions

  Placements
  ✓ code-review → ~/.claude/skills/code-review         exists, modified
  ✓ code-review → ~/.agents/skills/code-review          exists, clean
  ✓ napoln-manage → ~/.claude/skills/napoln-manage      exists, clean
  ✓ napoln-manage → ~/.agents/skills/napoln-manage      exists, clean
  ✓ deploy-checklist → .claude/skills/deploy-checklist   exists, clean
  ✓ deploy-checklist → .agents/skills/deploy-checklist   exists, clean

  Agents
  ✓ Claude Code detected
  ✓ Gemini CLI detected
  ✗ pi not detected

  Untracked skills
  ⚠ ~/.claude/skills/my-custom-thing/  (not managed by napoln)

  Garbage collection
  ⚠ 1 unreferenced store entry (code-review/1.0.0-a3b2c1d)
    Run 'napoln gc' to remove (4.2 KB)

  Environment
  ✓ git available (2.44.0)
  ✓ Filesystem supports reflink (APFS)
  ✓ napoln v0.1.0

  All checks passed (2 warnings).
```

```
$ napoln doctor --json
{
  "store": {
    "status": "ok",
    "entries": 3,
    "unreferenced": 1
  },
  "manifest": {
    "status": "ok"
  },
  "placements": {
    "status": "ok",
    "total": 6,
    "missing": 0,
    "modified": 1
  },
  "agents": {
    "claude-code": true,
    "gemini-cli": true,
    "pi": false
  },
  "untracked": ["~/.claude/skills/my-custom-thing"],
  "environment": {
    "git": "2.44.0",
    "reflink": true,
    "filesystem": "apfs",
    "napoln": "0.1.0"
  }
}
```

---

### `--dry-run` Design Principles

The `--dry-run` flag follows these rules across all commands:

1. **Read everything, write nothing.** Network fetches and git clones still happen (needed to determine what would change). Only local mutations (store writes, placements, manifest updates) are suppressed.

2. **Show exactly what would happen.** Each action is printed with a "Would ..." prefix. The output structure mirrors the real command output so users can scan it the same way.

3. **Same exit code as the real run would produce.** If the real run would succeed, dry-run exits 0. If it would produce conflicts, dry-run exits 2. This lets scripts use dry-run to check before applying.

4. **Available on mutating commands only:**

| Command | `--dry-run` | Rationale |
|---------|-------------|-----------|
| `add` | ✅ | Shows what would be stored and placed |
| `remove` | ✅ | Shows what would be deleted |
| `upgrade` | ✅ | Shows merge plan per agent |
| `sync` | ✅ | Shows what would be repaired |
| `gc` | ✅ | Shows what store entries would be removed |
| `resolve` | ❌ | Resolve is a confirmation, not a mutation |
| `status` | ❌ | Already read-only |
| `diff` | ❌ | Already read-only |
| `doctor` | ❌ | Already read-only |
| `list` | ❌ | Already read-only |
| `config` | ❌ | Too simple to need dry-run |
| `telemetry` | ❌ | Too simple to need dry-run |

5. **Clearly labeled.** Dry-run output always begins or ends with a reminder:

```
  Dry run — no changes will be made.
  Run without --dry-run to apply.
```
