# napoln Specification

**Version:** 0.1.0-draft
**Date:** 2026-04-14
**Status:** Draft

---

## 1. Overview

napoln is a package manager for agent skills — reusable instruction sets consumed by terminal-based AI coding agents. It manages the full lifecycle: discovery, installation, versioning, customization-preserving upgrades, and multi-agent placement.

### 1.0 Related Documents

| Document | Contents |
|----------|----------|
| [README.md](README.md) | Project overview and design principles |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture decisions, prior art analysis (uv, pnpm, Aulë, Vercel skills), reflink-first store design |
| [STORIES.md](STORIES.md) | BDD-style user stories (8 scenarios) and detailed command output examples (5 commands) including `--dry-run` design |
| [PROMPT.md](PROMPT.md) | Original brainstorm context and problem statement |

### 1.1 Goals

1. **Versioned skill management** with three-way merge on upgrade, preserving local customizations
2. **Minimal disk duplication** via reflink/copy-on-write, with copy fallback
3. **Decentralized distribution** — any git repo is a valid skill source; optional registry for discovery
4. **Content-addressed integrity** — every stored version has a deterministic hash
5. **Depth over breadth** — five agents done well: Claude Code, Gemini CLI, pi, Codex, Cursor
6. **Self-describing** — bootstrap skills teach agents how to use napoln

### 1.2 Non-Goals (v0.1)

- Registry web application (git-only sources at launch)
- Executable skill tools or lifecycle hooks (Aulë v0.2.0 scope — premature for us)
- Permission/policy enforcement (agents handle their own sandboxing)
- Windows support (best-effort; copy fallback works but not tested)

### 1.3 Terminology

| Term | Definition |
|------|-----------|
| **Skill** | A directory containing a `SKILL.md` and optional supporting files, conforming to the [Agent Skills standard](https://agentskills.io/specification) |
| **Store** | `~/.napoln/store/` — content-addressed, immutable upstream snapshots |
| **Working copy** | The editable copy of a skill placed in an agent's skill directory |
| **Placement** | A working copy in a specific agent directory (one skill can have multiple placements) |
| **Origin** | The pristine upstream version of a skill in the store (used as merge base) |
| **Manifest** | `manifest.toml` — tracks installed skills, versions, placements |
| **Source** | Where a skill comes from: a git repo, local path, or registry identifier |

---

## 2. Skill Format

napoln consumes and produces skills conforming to the [Agent Skills standard](https://agentskills.io/specification). It does not define its own skill format.

### 2.1 Required Structure

```
<skill-name>/
├── SKILL.md              # Required
├── scripts/              # Optional
├── references/           # Optional
└── assets/               # Optional
```

### 2.2 SKILL.md Format

```markdown
---
name: skill-name
description: What this skill does and when to use it.
license: MIT                          # Optional
compatibility: Requires Python 3.12+  # Optional
metadata:                             # Optional
  author: someone
  version: "1.0.0"
allowed-tools: Bash(git:*) Read       # Optional, experimental
---

Markdown body with instructions for the agent.
```

### 2.3 Frontmatter Rules

Per the Agent Skills spec:
- `name`: Required. 1–64 chars. Lowercase `[a-z0-9-]`. No leading/trailing/consecutive hyphens. Must match parent directory name.
- `description`: Required. 1–1024 chars.
- All other fields: Optional. Agents ignore fields they don't understand.

### 2.4 Agent-Specific Frontmatter

Some agents extend the standard with additional frontmatter fields (e.g., Claude Code's `allowed-tools`, pi's `disable-model-invocation`). Since agents ignore unknown fields, a single SKILL.md can include a superset:

```yaml
---
name: my-skill
description: Does something useful.
allowed-tools: Bash(git:*) Read       # Claude Code uses this; others ignore
disable-model-invocation: false       # pi uses this; others ignore
---
```

napoln does **not** implement an overlay or per-agent variant mechanism. One SKILL.md serves all agents. If agent formats diverge significantly in the future, an adapter layer can be added as a backward-compatible extension.

### 2.5 Skill Validation

On `napoln add`, validate:
1. `SKILL.md` exists
2. Frontmatter parses as valid YAML
3. `name` field is present and valid per naming rules
4. `description` field is present and non-empty
5. `name` matches parent directory name

Validation is **warnings, not errors** — matching how pi and Gemini CLI handle it. A skill with warnings is still installed.

---

## 3. Store

### 3.1 Location

```
~/.napoln/
├── config.toml
├── manifest.toml
├── store/
│   └── <skill-name>/
│       └── <version>-<hash-prefix>/
└── cache/
```

Configurable via `NAPOLN_HOME` environment variable. Default: `~/.napoln/`.

### 3.2 Content Addressing

Each skill version in the store is identified by `{version}-{hash-prefix}` where:

```
hash = SHA-256(
  for each file in skill directory (sorted by relative path, excluding .napoln):
    encode("{relative_path}\x00")
    encode(file_contents)
    encode("\x00")
)
hash-prefix = first 7 hex characters of hash
```

This is deterministic: the same skill content always produces the same hash regardless of where or when it was computed.

### 3.3 Immutability

Store contents are **never modified** after initial write. They serve as the merge base for three-way merge. If a store entry is modified (detected by re-hashing), `napoln doctor` reports corruption.

### 3.4 Garbage Collection

`napoln gc` removes store entries not referenced by any manifest (global or any project manifest found in `cwd` ancestors). Old versions are retained after upgrade until explicitly collected.

---

## 4. Placement

### 4.1 Agent Directories

| Agent | Global Placement | Project Placement |
|-------|-----------------|-------------------|
| Claude Code | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` |
| Gemini CLI | `~/.gemini/skills/<name>/` | `.gemini/skills/<name>/` |
| pi | `~/.agents/skills/<name>/` | `.agents/skills/<name>/` |
| Codex | `~/.agents/skills/<name>/` | `.agents/skills/<name>/` |
| Cursor | `~/.cursor/skills/<name>/` | `.agents/skills/<name>/` |

All five agents implement the Agent Skills standard with identical `SKILL.md` format. All paths above are hardcoded and non-configurable (except pi, which supports custom paths via settings.json).

**Note on `.agents/skills/` convergence:** Gemini CLI, pi, Codex, Cursor, and [many other agents](https://github.com/vercel-labs/skills#available-agents) all read from `.agents/skills/` at the project level. A single placement in `.agents/skills/` serves all of them. Only Claude Code requires its own `.claude/skills/` placement. At the global level, agents diverge (`~/.gemini/skills/`, `~/.cursor/skills/`, `~/.agents/skills/`, etc.) so napoln places into each agent's specific global path.

**Note on deduplication:** Gemini CLI reads from both `~/.gemini/skills/` and `~/.agents/skills/`. napoln places into `~/.agents/skills/` only for the global level, avoiding a double placement. If the user explicitly requests `--agents gemini-cli`, napoln uses `~/.gemini/skills/`.

#### Codex Sidecar Metadata

Codex supports an optional `agents/openai.yaml` sidecar file alongside `SKILL.md` for richer metadata:

```yaml
# agents/openai.yaml (Codex-specific, optional)
interface:
  display_name: "My Skill"
  short_description: "Brief tagline"
  icon_small: "assets/icon-sm.png"
  brand_color: "#4A90D9"
  default_prompt: "Do the thing"
dependencies:
  tools:
    - type: mcp
      value: "my-mcp-server"
      transport: stdio
      command: "npx my-server"
policy:
  allow_implicit_invocation: true
```

This file is Codex-specific — other agents ignore it. napoln treats it like any other supporting file: it is stored, placed, and merged alongside the rest of the skill directory. Skill authors who want Codex-specific behavior can include it; it costs nothing for other agents.

### 4.2 Link Strategy

**Primary:** Clone/reflink (copy-on-write)
- macOS: APFS `clonefile()`
- Linux: `ioctl_ficlone()` on btrfs, xfs, bcachefs

**Fallback:** Full copy (if reflink fails on first file)

**Not used:** Hardlinks (share writes — wrong for mutable content), symlinks (fragile, tight store coupling)

The fallback is detected per-placement on the first file and recorded in the manifest and `.napoln` provenance file.

### 4.3 Provenance File

Each placement includes a `.napoln` file (hidden dotfile):

```toml
source = "github.com/owner/repo/skills/my-skill"
version = "1.2.0"
store_hash = "ab3f7c4"
link_mode = "clone"
installed = "2026-04-14T09:00:00Z"
napoln_version = "0.1.0"
```

This file is:
- Written by napoln on install/upgrade
- Read by napoln for status/diff/upgrade
- Ignored by agents (they only read SKILL.md)
- Used to make placements self-describing (recoverable without global manifest)

### 4.4 Agent Auto-Detection

When `--agents` is not specified, napoln detects installed agents:

| Check | Agent |
|-------|-------|
| `~/.claude/` directory exists | Claude Code |
| `~/.gemini/` directory exists | Gemini CLI |
| `~/.pi/` directory exists OR `pi` on PATH | pi |
| `codex` on PATH | Codex |
| `~/.cursor/` directory exists | Cursor |

For project-level installs, check for `.claude/`, `.gemini/`, `.pi/`, `.agents/` in the project root.

If no agents are detected, prompt the user to specify with `--agents`.

### 4.5 Scope

| Scope | Flag | Manifest Location | Placement Paths |
|-------|------|-------------------|----------------|
| Global | `--global` (default) | `~/.napoln/manifest.toml` | `~/.<agent>/skills/<name>/` |
| Project | `--project` | `.napoln/manifest.toml` | `.<agent>/skills/<name>/` |

Global is the default because most skills are personal tools, not project-specific.

---

## 5. Sources

### 5.1 Git Sources

Any git repository containing a valid skill directory is a valid source. napoln does not require any napoln-specific configuration in the source repo.

#### 5.1.1 Source Identifiers

```
# Full forms
github.com/owner/repo                        # Root of repo is a skill
github.com/owner/repo/path/to/skill          # Subdirectory is a skill
github.com/owner/repo@v1.2.0                 # Pinned to tag
github.com/owner/repo@main                   # Track branch
github.com/owner/repo@abc1234                # Pinned to commit
github.com/owner/repo/path/to/skill@v1.2.0   # Subdirectory + tag

# Shorthand (assumes github.com)
owner/repo
owner/repo/path/to/skill
owner/repo@v1.2.0

# Full git URLs
https://github.com/owner/repo.git
git@github.com:owner/repo.git
https://gitlab.com/owner/repo.git
```

#### 5.1.2 Skill Discovery in Repos

When a source points to a directory (not a specific skill path):
1. If the directory contains `SKILL.md` → it is a single skill
2. If the directory contains subdirectories with `SKILL.md` → list them, let user choose (or use `--skill` flag)
3. If the directory contains a `skills/` subdirectory → recurse into it

#### 5.1.3 Version Resolution

| Source Form | Version Strategy |
|------------|-----------------|
| `owner/repo@v1.2.0` | Exact tag match |
| `owner/repo@^1.2.0` | Latest tag matching semver range |
| `owner/repo@main` | Latest commit on branch |
| `owner/repo@abc1234` | Exact commit |
| `owner/repo` (no version) | Latest semver tag, or `HEAD` of default branch if no tags |

Semver tags: napoln recognizes tags matching `v?MAJOR.MINOR.PATCH(-PRERELEASE)?`. Tags not matching this pattern are ignored for version resolution.

### 5.2 Local Sources

```bash
napoln add ./path/to/skill
napoln add /absolute/path/to/skill
```

Local sources are copied into the store (not reflinked, since the source may be on a different filesystem or may change). The source path is recorded in the manifest for `napoln upgrade` to re-read.

### 5.3 Registry Sources (Future)

```bash
napoln add my-skill                   # Short name → registry lookup
napoln add @owner/my-skill            # Namespaced
```

Not implemented in v0.1. The manifest format supports it. The CLI parses it and returns a clear "registry not yet available" message with the git alternative.

---

## 6. Manifest

### 6.1 Format

TOML. Human-readable, supports comments, well-supported in Python (tomllib in stdlib since 3.11, tomli for older).

### 6.2 Schema

```toml
[napoln]
schema = 1                                    # Manifest schema version

[skills.<name>]
source = "<source-identifier>"                # Where this skill came from
version = "<semver-or-ref>"                   # Installed version
store_hash = "<7-char-hex>"                   # Content hash of stored version
installed = "<ISO-8601>"                       # When first installed
updated = "<ISO-8601>"                        # When last upgraded

[skills.<name>.agents.<agent-id>]
path = "<absolute-or-relative-path>"          # Where the working copy lives
link_mode = "clone|copy"                      # How it was placed
scope = "global|project"                      # Installation scope
```

### 6.3 Example

```toml
[napoln]
schema = 1

[skills.code-review]
source = "github.com/owner/repo/skills/code-review"
version = "2.0.1"
store_hash = "d19e4a3"
installed = "2026-04-14T10:00:00Z"
updated = "2026-04-14T10:00:00Z"

[skills.code-review.agents.claude-code]
path = "~/.claude/skills/code-review"
link_mode = "clone"
scope = "global"

[skills.code-review.agents.gemini-cli]
path = "~/.agents/skills/code-review"
link_mode = "clone"
scope = "global"

[skills.code-review.agents.pi]
path = "~/.agents/skills/code-review"
link_mode = "clone"
scope = "global"
```

**Note:** When Gemini CLI and pi share the `.agents/skills/` path, the manifest records one placement that serves both agents. The agent key reflects the primary target; a `shared_with` field is not needed — both agents independently discover skills in `.agents/skills/`.

### 6.4 Lock File

**Decision: No lock file in v0.1.** The manifest pins exact versions and content hashes, which provides sufficient reproducibility. A lock file adds value when there are transitive dependencies — skills don't have dependencies on other skills. If skill dependencies are added in a future version, a lock file becomes necessary.

### 6.5 Project Manifest

`.napoln/manifest.toml` in the project root. Same schema as the global manifest. Records only project-scoped installations.

#### `.gitignore` Strategy

**Decision: Commit the manifest, gitignore the placements.**

```gitignore
# .gitignore
.claude/skills/
.gemini/skills/
.agents/skills/
.pi/skills/

# Commit .napoln/manifest.toml — it's the source of truth
!.napoln/
```

Team workflow:
1. Developer A runs `napoln add owner/repo/skills/my-skill --project`
2. `.napoln/manifest.toml` is committed
3. Developer B clones, runs `napoln install` (reads manifest, places skills)

This is the same pattern as `package.json` + `node_modules/` in .gitignore.

---

## 7. Three-Way Merge

### 7.1 Algorithm

Merge is performed per-file using `git merge-file`:

```bash
git merge-file -p \
  <working-copy>  \    # OURS — user's current version
  <store-base>     \   # BASE — pristine version from when skill was installed
  <store-new>           # THEIRS — pristine version of new upstream
```

If `git` is not available, fall back to Python's `merge3` library (or `difflib`-based implementation).

### 7.2 Merge Scope

| File Pattern | Strategy |
|-------------|----------|
| `SKILL.md` | Three-way merge |
| `scripts/**` | Replace if unchanged vs. base; keep local + warn if modified |
| `references/**` | Replace if unchanged vs. base; keep local + warn if modified |
| `assets/**` | Replace if unchanged vs. base; keep local + warn if modified |
| `.napoln` | Overwrite (napoln-managed metadata) |
| New files in upstream | Add |
| Files deleted in upstream | Remove if unchanged vs. base; keep + warn if modified |

### 7.3 Merge Cases

Given: `BASE` = store origin of installed version, `OURS` = working copy, `THEIRS` = new upstream

| BASE vs OURS | BASE vs THEIRS | Action |
|-------------|---------------|--------|
| Identical | Changed | Fast-forward: replace OURS with reflink of THEIRS |
| Changed | Identical | No-op: OURS already has everything (upstream didn't change this file) |
| Identical | Identical | No-op: nothing changed |
| Changed | Changed, no conflict | Merge: apply both sets of changes |
| Changed | Changed, conflict | Merge with conflict markers; report to user |

### 7.4 Conflict Format

Standard git conflict markers:

```markdown
<<<<<<< local (your changes)
2. Focus on security implications
3. Check error handling
=======
2. Use the OWASP checklist
>>>>>>> upstream (v1.3.0)
```

### 7.5 Conflict Resolution

```bash
# After manually (or agent-assisted) resolving conflicts:
napoln resolve code-review
napoln resolve code-review --agent claude-code   # resolve for one agent only
```

`napoln resolve` verifies no conflict markers remain in SKILL.md, then updates the manifest to reflect the new version.

---

## 8. CLI

### 8.1 Entry Point

```bash
uvx napoln <command>
# or, if installed:
napoln <command>
```

### 8.2 Commands

#### `napoln add <source>`

Install a skill from a git source or local path.

```
Arguments:
  source                Git source, local path, or registry name

Options:
  --agents <a,b,c>      Target agents (default: auto-detect)
  --version <constraint> Version constraint (default: latest)
  --global              Install globally (default)
  --project             Install to current project
  --skill <name>        Select specific skill from multi-skill repo
  --name <name>         Override skill name (for skills where directory name differs)
```

Behavior:
1. Resolve source → fetch to cache → validate
2. Hash → store
3. Detect agents → place working copies
4. Update manifest

Exit codes: 0 = success, 1 = error, 2 = validation warnings (skill installed with warnings)

#### `napoln remove <name>`

Remove an installed skill.

```
Options:
  --agents <a,b,c>      Remove from specific agents only
  --global              Remove from global scope
  --project             Remove from project scope
  --keep-store          Don't mark store entry for GC
```

#### `napoln upgrade [<name>]`

Upgrade one or all skills.

```
Options:
  --version <constraint> Upgrade to specific version
  --agents <a,b,c>      Upgrade for specific agents only
  --dry-run             Show what would change without applying
  --force               Replace working copies without merging (discard local changes)
```

#### `napoln status`

Show installed skills and their state.

```
Options:
  --json                Machine-readable output
  --global              Show global skills only
  --project             Show project skills only
```

Output:
```
my-skill v1.2.0 (github.com/owner/repo)
  claude-code  ~/.claude/skills/my-skill     modified
  gemini-cli   ~/.agents/skills/my-skill     clean
  pi           ~/.agents/skills/my-skill     clean (shared)

code-review v2.0.1 (github.com/other/repo)
  claude-code  .claude/skills/code-review    clean      [project]
```

#### `napoln diff <name>`

Show local modifications vs. upstream.

```
Options:
  --agent <agent>       Diff for specific agent only
```

#### `napoln resolve <name>`

Mark a skill's merge conflicts as resolved.

```
Options:
  --agent <agent>       Resolve for specific agent only
```

Validates that no conflict markers remain. Updates manifest.

#### `napoln sync`

Re-create missing placements from manifest + store.

```
Options:
  --dry-run             Show what would be synced
```

Use after cloning a project with a `.napoln/manifest.toml`, or after accidentally deleting a skill directory.

#### `napoln install`

Alias for `napoln sync`. Reads the manifest and ensures all placements exist. Intended for use after `git clone` in a project with a committed manifest.

#### `napoln doctor`

Health check.

```
Checks:
  ✓ Store integrity (hash verification)
  ✓ Manifest consistency (all referenced store entries exist)
  ✓ Placement validity (all manifested placements exist on disk)
  ✓ Provenance files (.napoln in each placement matches manifest)
  ✓ Untracked skills (skills in agent dirs not managed by napoln)
  ✗ git not found — merge will use fallback algorithm
```

#### `napoln gc`

Remove unreferenced store entries.

```
Options:
  --dry-run             Show what would be removed
  --all                 Also remove cache entries
```

#### `napoln list`

List available skills from a source without installing.

```
napoln list github.com/owner/repo
napoln list ./local/path
```

#### `napoln config`

View or edit configuration.

```
napoln config                         # Show current config
napoln config set telemetry.enabled false
napoln config set default_agents "claude-code,pi"
```

#### `napoln telemetry <subcommand>`

```
napoln telemetry status               # Show telemetry state
napoln telemetry enable               # Enable
napoln telemetry disable              # Disable
napoln telemetry show-data            # Show what would be sent
```

### 8.3 `--dry-run`

Available on all mutating commands: `add`, `remove`, `upgrade`, `sync`, `gc`.

Behavior:
- **Read everything, write nothing.** Network fetches and git clones still execute (needed to determine what would change). Local mutations (store writes, placements, manifest updates) are suppressed.
- **Show exactly what would happen.** Each suppressed action is printed with a "Would ..." prefix. Output structure mirrors the real command.
- **Same exit code as the real run would produce.** Scripts can use dry-run to check before applying.
- **Clearly labeled.** Output begins with "Dry run — no changes will be made" and ends with "Run without --dry-run to apply."

Not available on read-only commands (`status`, `diff`, `doctor`, `list`) or trivial commands (`resolve`, `config`, `telemetry`).

See [STORIES.md](STORIES.md#example-3-napoln-add---dry-run) for full output examples.

### 8.4 Global Options

```
--verbose, -v           Verbose output
--quiet, -q             Suppress non-error output
--json                  Machine-readable JSON output
--no-color              Disable colored output
--dry-run               Show what would change without applying (mutating commands)
--version               Show napoln version
--help, -h              Show help
```

### 8.5 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (network, filesystem, validation failure) |
| 2 | Success with warnings (validation warnings, unresolved conflicts) |
| 130 | Interrupted (SIGINT) |

---

## 9. Configuration

### 9.1 Location

`~/.napoln/config.toml`

### 9.2 Schema

```toml
[napoln]
default_agents = ["claude-code", "gemini-cli", "pi"]   # Default agents for `add`
default_scope = "global"                                 # "global" or "project"

[telemetry]
enabled = false                     # Explicit opt-in
anonymous_id = "uuid"               # Generated on first run

[cache]
dir = "~/.napoln/cache"            # Override cache location
max_size = "1GB"                    # Auto-prune cache above this size

# Future:
# [registry]
# url = "https://registry.napoln.dev"
# token = "..."
```

---

## 10. Bootstrap Skills

### 10.1 Bundled Skills

napoln ships with one built-in skill:

**`napoln-manage`** — teaches agents how to use napoln.

This skill is:
- Bundled in the napoln Python package at `src/napoln/skills/napoln-manage/SKILL.md`
- Installed automatically on first `napoln add` (or `napoln init`)
- Managed like any other skill (appears in manifest, can be upgraded)
- Dogfoods the Agent Skills format

### 10.2 First-Run Behavior

On first invocation of any `napoln` command:
1. Create `~/.napoln/` directory structure
2. Generate `config.toml` with defaults
3. Prompt for telemetry opt-in
4. Install `napoln-manage` bootstrap skill to detected agents
5. Proceed with the requested command

### 10.3 Bootstrap Skill Content

```markdown
---
name: napoln-manage
description: >
  Search for, install, upgrade, and manage agent skills using the napoln
  package manager. Use when the user wants to find new capabilities, install
  a skill from a git repository, check for skill updates, view local
  modifications to installed skills, or resolve merge conflicts after upgrade.
---

# napoln — Skill Manager

napoln manages reusable skills for AI coding agents. You can help the user
manage their skills using the `napoln` CLI.

## Install a Skill

```bash
# From a git repository
napoln add owner/repo                          # GitHub shorthand
napoln add github.com/owner/repo/skills/name   # Specific skill in repo
napoln add owner/repo@v1.2.0                   # Pinned version

# From a local path
napoln add ./path/to/skill
```

## Check What's Installed

```bash
napoln status          # List all installed skills with modification state
napoln diff <name>     # Show local changes vs. upstream
```

## Upgrade Skills

```bash
napoln upgrade              # Upgrade all skills
napoln upgrade <name>       # Upgrade specific skill
napoln upgrade --dry-run    # Preview changes without applying
```

If upgrade produces merge conflicts (the user customized a skill and the
upstream also changed the same lines):
1. Conflicts appear as `<<<<<<<` / `=======` / `>>>>>>>` markers in SKILL.md
2. Edit the file to resolve — keep the best of both versions
3. Run `napoln resolve <name>` to confirm resolution

## Remove a Skill

```bash
napoln remove <name>
```

## Health Check

```bash
napoln doctor          # Verify store integrity and placement validity
napoln sync            # Re-create any missing placements
```
```

---

## 11. Telemetry

### 11.1 Principles

- **Opt-in**: Prompted on first run, default is disabled
- **Anonymous**: UUID generated locally, not linked to any identity
- **Transparent**: `napoln telemetry show-data` displays exact payload
- **Auditable**: All telemetry code isolated in `src/napoln/telemetry.py`
- **Minimal**: Only what's needed to understand usage patterns

### 11.2 Collected Data

| Field | Example | Purpose |
|-------|---------|---------|
| `command` | `"add"` | Understand which commands are used |
| `source_type` | `"git"` | Git vs. local vs. registry distribution |
| `agent_count` | `2` | How many agents people target |
| `link_mode` | `"clone"` | Reflink adoption vs. fallback |
| `os` | `"darwin"` | Platform distribution |
| `arch` | `"arm64"` | Architecture distribution |
| `napoln_version` | `"0.1.0"` | Version distribution |
| `success` | `true` | Error rate |
| `duration_ms` | `340` | Performance |

### 11.3 Never Collected

- Skill names or descriptions
- Repository URLs or paths
- File contents
- User names, emails, or hostnames
- IP addresses (not logged server-side)

### 11.4 Endpoint

`POST https://telemetry.napoln.dev/v1/events`

Batched: events are queued locally and sent in batch on command completion. If the endpoint is unreachable, events are silently discarded (never retried, never persisted).

---

## 12. Content Hashing

### 12.1 Algorithm

SHA-256 over the deterministic concatenation of all files in a skill directory.

### 12.2 Procedure

```python
def hash_skill(skill_dir: Path) -> str:
    hasher = hashlib.sha256()
    
    # Collect all files, excluding .napoln provenance
    files = sorted(
        p.relative_to(skill_dir)
        for p in skill_dir.rglob("*")
        if p.is_file() and p.name != ".napoln"
    )
    
    for rel_path in files:
        abs_path = skill_dir / rel_path
        # Encode path (POSIX-normalized, forward slashes)
        hasher.update(str(rel_path.as_posix()).encode("utf-8"))
        hasher.update(b"\x00")
        # Encode content
        hasher.update(abs_path.read_bytes())
        hasher.update(b"\x00")
    
    return hasher.hexdigest()[:7]
```

### 12.3 Properties

- **Deterministic**: Same files → same hash, regardless of filesystem, OS, or time
- **Path-sensitive**: Renaming a file changes the hash
- **Content-sensitive**: Any byte change in any file changes the hash
- **Excludes `.napoln`**: Provenance metadata is not part of the content identity

---

## 13. Reflink Implementation

### 13.1 Python API

```python
import os
import shutil
from pathlib import Path

def clone_file(src: Path, dst: Path) -> str:
    """Clone a file using reflink. Returns the link mode used."""
    try:
        # macOS: clonefile via ctypes
        # Linux: ioctl_ficlone via fcntl
        _reflink(src, dst)
        return "clone"
    except (OSError, NotImplementedError):
        shutil.copy2(str(src), str(dst))
        return "copy"

def place_skill(store_path: Path, target_dir: Path) -> str:
    """Place a skill from store to agent directory. Returns link mode."""
    target_dir.mkdir(parents=True, exist_ok=True)
    link_mode = None
    
    for src_file in store_path.rglob("*"):
        if src_file.is_file():
            rel = src_file.relative_to(store_path)
            dst_file = target_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            mode = clone_file(src_file, dst_file)
            if link_mode is None:
                link_mode = mode  # Determined by first file
    
    return link_mode or "copy"
```

### 13.2 Platform Support

| Platform | Filesystem | Reflink | Fallback |
|----------|-----------|---------|----------|
| macOS | APFS | ✅ `clonefile()` | copy |
| macOS | HFS+ | ❌ | copy |
| Linux | btrfs | ✅ `ioctl_ficlone()` | copy |
| Linux | xfs | ✅ `ioctl_ficlone()` | copy |
| Linux | ext4 | ❌ | copy |
| Windows | ReFS (Dev Drive) | ✅ `block_clone()` | copy |
| Windows | NTFS | ❌ | copy |

### 13.3 Python Libraries

- [`reflink`](https://pypi.org/project/reflink/) — Cross-platform reflink support
- Alternatively, direct ctypes/fcntl calls (fewer dependencies)

---

## 14. Multi-Skill Repositories

### 14.1 Repository Layout

A repository can contain multiple skills. napoln discovers them by scanning for `SKILL.md` files.

#### Convention: `skills/` Directory

```
my-repo/
├── README.md
├── skills/
│   ├── code-review/
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── test-generator/
│   │   ├── SKILL.md
│   │   └── references/
│   └── deploy-checklist/
│       └── SKILL.md
```

#### Convention: Root-Level Skill

```
my-skill-repo/
├── SKILL.md
├── scripts/
└── README.md
```

### 14.2 Addressing

```bash
# Install all skills from a repo
napoln add owner/repo                     # Interactive: list and choose
napoln add owner/repo --skill '*'         # All skills

# Install specific skill
napoln add owner/repo --skill code-review
napoln add owner/repo/skills/code-review  # Direct path
```

### 14.3 No Repo-Level Manifest Required

napoln does not require a `napoln.toml` or any napoln-specific file in the source repository. Skill discovery is based purely on the Agent Skills standard: any directory containing a valid `SKILL.md` is a skill.

This means:
- Existing skills repos (Anthropic's, Vercel's, Aulë's, pi's) work without modification
- Skill authors don't need to know about napoln
- No lock-in to napoln's tooling

---

## 15. Error Handling

### 15.1 User-Facing Errors

All errors include:
1. **What happened** — clear description
2. **Why** — context about the cause
3. **How to fix** — actionable suggestion

Example:
```
Error: Could not reflink store/my-skill/1.2.0-ab3f7c/SKILL.md
       to ~/.claude/skills/my-skill/SKILL.md

Cause: Source and target are on different filesystems
       (store: /dev/disk1s1, target: /dev/disk2s1)

Fix:   napoln will use a full copy instead. To avoid this,
       set NAPOLN_HOME to a path on the same filesystem as
       your home directory.
```

### 15.2 Idempotency

All commands are idempotent:
- `napoln add` on an already-installed skill: no-op (or upgrade if version differs)
- `napoln remove` on a not-installed skill: no-op with message
- `napoln sync` on already-synced state: no-op
- `napoln upgrade` with no new version: no-op with message

### 15.3 Atomicity

Placement operations are pseudo-atomic:
1. Write to a temp directory adjacent to the target
2. Rename (atomic on same filesystem) to final location
3. If rename fails, clean up temp directory

This prevents partial placements from corrupted skills.

---

## 16. Project Structure

```
napoln/
├── pyproject.toml                      # Package metadata, dependencies, build config
├── README.md
├── ARCHITECTURE.md
├── SPEC.md                             # This document
├── LICENSE                             # MIT
│
├── src/
│   └── napoln/
│       ├── __init__.py                 # Version, public API
│       ├── cli.py                      # CLI entry point (typer)
│       ├── commands/                   # One module per command
│       │   ├── __init__.py
│       │   ├── add.py
│       │   ├── remove.py
│       │   ├── upgrade.py
│       │   ├── status.py
│       │   ├── diff.py
│       │   ├── resolve.py
│       │   ├── sync.py
│       │   ├── doctor.py
│       │   ├── gc.py
│       │   ├── list_cmd.py
│       │   ├── config.py
│       │   └── telemetry_cmd.py
│       ├── core/                       # Core logic (no CLI dependency)
│       │   ├── __init__.py
│       │   ├── manifest.py             # Manifest TOML read/write
│       │   ├── store.py                # Content-addressed store operations
│       │   ├── linker.py               # Reflink/copy placement with fallback
│       │   ├── resolver.py             # Git source resolution, version matching
│       │   ├── merger.py               # Three-way merge (delegates to git)
│       │   ├── hasher.py               # Content hashing (SHA-256)
│       │   ├── agents.py               # Agent detection, path configuration
│       │   └── validator.py            # SKILL.md validation
│       ├── telemetry.py                # Telemetry collection (isolated module)
│       ├── errors.py                   # Error types
│       ├── output.py                   # Terminal output formatting
│       └── skills/                     # Bundled bootstrap skills
│           └── napoln-manage/
│               └── SKILL.md
│
├── tests/
│   ├── conftest.py                     # Shared fixtures (tmp stores, fake agent dirs, skill builders)
│   │
│   ├── unit/                           # TDD — parameterized pytest tests per module
│   │   ├── test_hasher.py
│   │   ├── test_validator.py
│   │   ├── test_manifest.py
│   │   ├── test_store.py
│   │   ├── test_linker.py
│   │   ├── test_resolver.py
│   │   ├── test_merger.py
│   │   └── test_agents.py
│   │
│   ├── features/                       # BDD — pytest-bdd .feature files from STORIES.md
│   │   ├── first_run.feature
│   │   ├── install.feature
│   │   ├── upgrade.feature
│   │   ├── status_and_diff.feature
│   │   ├── team_workflow.feature
│   │   ├── health_check.feature
│   │   └── garbage_collection.feature
│   │
│   ├── steps/                          # BDD — step definitions
│   │   ├── conftest.py                 # BDD-specific fixtures
│   │   ├── given.py                    # Given steps (setup state)
│   │   ├── when.py                     # When steps (run commands)
│   │   └── then.py                     # Then steps (assert outcomes)
│   │
│   ├── integration/                    # CLI integration tests (typer.testing.CliRunner)
│   │   └── test_cli.py
│   │
│   └── fixtures/                       # Test skill fixtures
│       ├── valid-skill/
│       │   └── SKILL.md
│       ├── multi-skill-repo/
│       │   ├── skills/
│       │   │   ├── skill-a/SKILL.md
│       │   │   └── skill-b/SKILL.md
│       │   └── README.md
│       └── invalid-skill/
│           └── SKILL.md                # Missing required fields
│
└── docs/                               # User-facing documentation (future)
```

### 16.1 Dependencies

```toml
[project]
name = "napoln"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.24.1",           # CLI framework (type-hint based, wraps click)
    "tomli-w>=1.2",            # TOML writing (reading via stdlib tomllib)
    "httpx>=0.28",             # HTTP client (for telemetry, future registry)
    "reflink>=0.2.2",          # Cross-platform reflink support
]

[project.scripts]
napoln = "napoln.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 16.2 Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-bdd>=8.1",         # BDD feature files + step definitions
    "pytest-cov>=7.1",
    "ruff>=0.15",
    "ty>=0.0.30",              # Type checking (Astral, same team as ruff/uv)
]
```

---

## 17. Testing Strategy

napoln uses **TDD with parameterized tests** for unit-level logic and **BDD with pytest-bdd** for feature-level acceptance tests. Both use pytest as the runner.

### 17.1 Philosophy

| Layer | Style | Tool | What It Tests |
|-------|-------|------|---------------|
| **Unit** | TDD, parameterized | `pytest` + `@pytest.mark.parametrize` | Individual functions: hashing, validation, manifest parsing, linking, merging |
| **Feature** | BDD | `pytest-bdd` + `.feature` files | End-to-end user workflows: install, upgrade, merge, team sync |
| **Integration** | Functional | `typer.testing.CliRunner` | CLI argument parsing, output formatting, exit codes |

**Write tests first.** Each module in `src/napoln/core/` gets a corresponding parameterized test file before the implementation. Each story in [STORIES.md](STORIES.md) becomes a `.feature` file that drives the BDD tests.

### 17.2 TDD: Parameterized Unit Tests

Unit tests use `@pytest.mark.parametrize` to cover input variations, edge cases, and error conditions in a compact, readable table format.

#### Example: `tests/unit/test_hasher.py`

```python
import pytest
from napoln.core.hasher import hash_skill


class TestHashSkill:
    """Content hashing produces deterministic, content-sensitive hashes."""

    def test_deterministic(self, tmp_path):
        """Same content always produces the same hash."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")

        assert hash_skill(skill) == hash_skill(skill)

    def test_content_sensitive(self, tmp_path):
        """Changing any file content changes the hash."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# V1")
        hash_v1 = hash_skill(skill)

        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# V2")
        hash_v2 = hash_skill(skill)

        assert hash_v1 != hash_v2

    def test_excludes_napoln_provenance(self, tmp_path):
        """The .napoln provenance file is excluded from hashing."""
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# Hello")
        hash_without = hash_skill(skill)

        (skill / ".napoln").write_text('version = "1.0.0"')
        hash_with = hash_skill(skill)

        assert hash_without == hash_with

    @pytest.mark.parametrize(
        "files, expected_different",
        [
            # Adding a file changes the hash
            ({"SKILL.md": "# A"}, {"SKILL.md": "# A", "scripts/run.sh": "#!/bin/bash"}),
            # Renaming a file changes the hash
            ({"SKILL.md": "# A", "old.txt": "x"}, {"SKILL.md": "# A", "new.txt": "x"}),
            # Same content, different structure
            ({"SKILL.md": "# A", "a/b.md": "x"}, {"SKILL.md": "# A", "a-b.md": "x"}),
        ],
        ids=["add-file", "rename-file", "restructure"],
    )
    def test_path_sensitive(self, tmp_path, files, expected_different):
        """Hash changes when file paths change, even if content is the same."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        for d, file_map in [(dir_a, files), (dir_b, expected_different)]:
            d.mkdir()
            for path, content in file_map.items():
                f = d / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content)

        assert hash_skill(dir_a) != hash_skill(dir_b)
```

#### Example: `tests/unit/test_validator.py`

```python
import pytest
from napoln.core.validator import validate_skill, ValidationResult, ValidationLevel


class TestValidateSkill:
    """SKILL.md validation catches issues but remains lenient."""

    @pytest.mark.parametrize(
        "frontmatter, expect_valid",
        [
            ("name: my-skill\ndescription: Does things", True),
            ("name: my-skill\ndescription: Does things\nlicense: MIT", True),
            ("name: MY-SKILL\ndescription: Does things", True),   # warning, not error
            ("name: my-skill", False),                              # missing description
            ("description: Does things", False),                    # missing name
            ("", False),                                            # empty frontmatter
        ],
        ids=["minimal-valid", "with-optional", "uppercase-name", "no-desc", "no-name", "empty"],
    )
    def test_frontmatter_validation(self, tmp_path, frontmatter, expect_valid):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Body")

        result = validate_skill(skill_dir)
        assert result.is_valid == expect_valid

    @pytest.mark.parametrize(
        "name, expected_warnings",
        [
            ("good-name", []),
            ("a", []),                                     # min length
            ("a" * 64, []),                                # max length
            ("a" * 65, ["name exceeds 64 characters"]),    # too long
            ("UPPER", ["name must be lowercase"]),
            ("-leading", ["name must not start with hyphen"]),
            ("trailing-", ["name must not end with hyphen"]),
            ("double--hyphen", ["consecutive hyphens"]),
            ("has_underscore", ["invalid characters"]),
        ],
        ids=["valid", "min-len", "max-len", "too-long", "uppercase",
             "leading-hyphen", "trailing-hyphen", "double-hyphen", "underscore"],
    )
    def test_name_validation(self, tmp_path, name, expected_warnings):
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test\n---\n# Body"
        )

        result = validate_skill(skill_dir)
        warning_messages = [w.message for w in result.warnings]
        for expected in expected_warnings:
            assert any(expected in msg for msg in warning_messages)

    @pytest.mark.parametrize(
        "dir_name, yaml_name, expect_warning",
        [
            ("my-skill", "my-skill", False),
            ("my-skill", "other-name", True),
        ],
        ids=["matching", "mismatched"],
    )
    def test_name_matches_directory(self, tmp_path, dir_name, yaml_name, expect_warning):
        skill_dir = tmp_path / dir_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {yaml_name}\ndescription: Test\n---\n# Body"
        )

        result = validate_skill(skill_dir)
        has_mismatch_warning = any("match" in w.message for w in result.warnings)
        assert has_mismatch_warning == expect_warning
```

#### Example: `tests/unit/test_linker.py`

```python
import pytest
from napoln.core.linker import place_skill, clone_file


class TestPlaceSkill:
    """Skill placement via reflink with copy fallback."""

    def test_places_all_files(self, tmp_path):
        """All files from store are placed in target directory."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Hello")
        (store / "scripts").mkdir()
        (store / "scripts" / "run.sh").write_text("#!/bin/bash")

        target = tmp_path / "target" / "my-skill"
        place_skill(store, target)

        assert (target / "SKILL.md").read_text() == "# Hello"
        assert (target / "scripts" / "run.sh").read_text() == "#!/bin/bash"

    def test_returns_link_mode(self, tmp_path):
        """Returns 'clone' or 'copy' depending on filesystem support."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Hello")

        target = tmp_path / "target" / "my-skill"
        mode = place_skill(store, target)

        assert mode in ("clone", "copy")

    def test_creates_parent_directories(self, tmp_path):
        """Target parent directories are created if they don't exist."""
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# Hello")

        target = tmp_path / "deep" / "nested" / "path" / "my-skill"
        place_skill(store, target)

        assert (target / "SKILL.md").exists()

    @pytest.mark.parametrize(
        "existing_content, expect_overwrite",
        [
            (None, True),           # No existing file
            ("# Old", True),       # Existing file gets overwritten
        ],
        ids=["fresh", "overwrite"],
    )
    def test_overwrite_behavior(self, tmp_path, existing_content, expect_overwrite):
        store = tmp_path / "store" / "my-skill"
        store.mkdir(parents=True)
        (store / "SKILL.md").write_text("# New")

        target = tmp_path / "target" / "my-skill"
        target.mkdir(parents=True)
        if existing_content:
            (target / "SKILL.md").write_text(existing_content)

        place_skill(store, target)
        assert (target / "SKILL.md").read_text() == "# New"


class TestCloneFile:
    """File-level clone with copy fallback."""

    def test_content_matches(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("hello")

        clone_file(src, dst)

        assert dst.read_text() == "hello"

    def test_independence(self, tmp_path):
        """Modifying the clone does not affect the original."""
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("original")

        clone_file(src, dst)
        dst.write_text("modified")

        assert src.read_text() == "original"
```

### 17.3 BDD: Feature Files from STORIES.md

The BDD stories in [STORIES.md](STORIES.md) are translated directly into pytest-bdd `.feature` files. Each feature file maps to one story. Step definitions are shared across features.

#### Example: `tests/features/first_run.feature`

```gherkin
Feature: First run experience
  As a developer using Claude Code and Gemini CLI
  I want to install my first skill with minimal friction
  So that I can extend my agents' capabilities

  Background:
    Given Claude Code is installed
    And Gemini CLI is installed
    And napoln has never been run

  Scenario: First run bootstraps napoln and installs a skill
    When I run "napoln add" with a valid local skill
    Then the napoln home directory is created
    And the bootstrap skill "napoln-manage" is installed
    And the skill is stored in the content-addressed store
    And the skill is placed in the Claude Code skills directory
    And the skill is placed in the shared agents skills directory
    And the manifest contains both the skill and the bootstrap skill
    And the exit code is 0

  Scenario: First run without reflink support
    Given the filesystem does not support reflink
    When I run "napoln add" with a valid local skill
    Then all placements use copy mode
    And the provenance file records link_mode as "copy"
    And the exit code is 0

  Scenario: First run with no agents detected
    Given no agents are installed
    When I run "napoln add" with a valid local skill
    Then the output contains "No agents detected"
    And the exit code is 1
```

#### Example: `tests/features/upgrade.feature`

```gherkin
Feature: Upgrade with three-way merge
  As a developer who has customized a skill
  I want to upgrade without losing my changes
  So that I get upstream improvements while keeping my customizations

  Background:
    Given a skill "code-review" is installed at version "1.0.0"
    And the skill is placed for Claude Code and Gemini CLI

  Scenario: Fast-forward when no local changes
    Given the Gemini CLI placement is unmodified
    And upstream has released version "1.1.0"
    When I run "napoln upgrade code-review"
    Then the Gemini CLI placement is replaced with the new version
    And the manifest version is "1.1.0"
    And the exit code is 0

  Scenario: Clean merge with local changes
    Given the Claude Code placement has local changes to the "Review Steps" section
    And upstream version "1.1.0" adds a new "Performance" section
    When I run "napoln upgrade code-review"
    Then the Claude Code placement contains both local changes and the new section
    And the exit code is 0

  Scenario: Merge conflict
    Given the Claude Code placement has local changes to line 14
    And upstream version "1.1.0" also changes line 14
    When I run "napoln upgrade code-review"
    Then the Claude Code placement contains conflict markers
    And the output contains "Conflicts in code-review"
    And the exit code is 2

  Scenario: Dry run shows plan without modifying anything
    Given upstream has released version "1.1.0"
    When I run "napoln upgrade code-review --dry-run"
    Then no files are modified on disk
    And the manifest is unchanged
    And the output contains "Would" for each planned action

  Scenario: Force upgrade discards local changes
    Given the Claude Code placement has local changes
    When I run "napoln upgrade code-review --force"
    Then all placements match the new upstream version exactly
    And local changes are gone
```

#### Step Definitions: `tests/steps/given.py`

```python
import pytest
from pytest_bdd import given, parsers
from pathlib import Path


@given("Claude Code is installed")
def claude_code_installed(napoln_env):
    """Create a fake ~/.claude/ directory."""
    (napoln_env.home / ".claude").mkdir(parents=True, exist_ok=True)


@given("Gemini CLI is installed")
def gemini_cli_installed(napoln_env):
    """Create a fake ~/.gemini/ directory."""
    (napoln_env.home / ".gemini").mkdir(parents=True, exist_ok=True)


@given("no agents are installed")
def no_agents(napoln_env):
    """Ensure no agent directories exist."""
    pass  # napoln_env starts clean


@given("napoln has never been run")
def fresh_napoln(napoln_env):
    """Ensure ~/.napoln/ does not exist."""
    assert not (napoln_env.home / ".napoln").exists()


@given(parsers.parse('a skill "{name}" is installed at version "{version}"'))
def skill_installed(napoln_env, name, version):
    """Set up a skill in the store + manifest as if napoln add had been run."""
    napoln_env.install_skill(name, version)


@given(parsers.parse("the {agent} placement is unmodified"))
def placement_unmodified(napoln_env, agent):
    """Ensure the working copy matches the store."""
    pass  # Default state after install


@given(parsers.parse('the {agent} placement has local changes to the "{section}" section'))
def placement_modified_section(napoln_env, agent, section):
    """Edit the working copy to add content in a specific section."""
    napoln_env.modify_placement(agent, section=section)


@given(parsers.parse('upstream has released version "{version}"'))
def upstream_version(napoln_env, version):
    """Create a new version in the fake upstream source."""
    napoln_env.create_upstream_version(version)


@given("the filesystem does not support reflink")
def no_reflink(napoln_env, monkeypatch):
    """Patch reflink to always raise OSError."""
    from napoln.core import linker
    monkeypatch.setattr(linker, "_reflink", _always_fails)


def _always_fails(src, dst):
    raise OSError("reflink not supported")
```

#### Step Definitions: `tests/steps/when.py`

```python
from pytest_bdd import when, parsers
from typer.testing import CliRunner
from napoln.cli import app


@when('I run "napoln add" with a valid local skill')
def run_add_local(napoln_env, cli_runner):
    """Run napoln add with a local fixture skill."""
    skill_path = napoln_env.create_local_skill("test-skill")
    napoln_env.result = cli_runner.invoke(
        app, ["add", str(skill_path)], env=napoln_env.env_vars
    )


@when(parsers.parse('I run "napoln upgrade {name}"'))
def run_upgrade(napoln_env, cli_runner, name):
    napoln_env.result = cli_runner.invoke(
        app, ["upgrade", name], env=napoln_env.env_vars
    )


@when(parsers.parse('I run "napoln upgrade {name} --dry-run"'))
def run_upgrade_dry(napoln_env, cli_runner, name):
    napoln_env.result = cli_runner.invoke(
        app, ["upgrade", name, "--dry-run"], env=napoln_env.env_vars
    )


@when(parsers.parse('I run "napoln upgrade {name} --force"'))
def run_upgrade_force(napoln_env, cli_runner, name):
    napoln_env.result = cli_runner.invoke(
        app, ["upgrade", name, "--force"], env=napoln_env.env_vars
    )
```

#### Step Definitions: `tests/steps/then.py`

```python
from pytest_bdd import then, parsers


@then("the napoln home directory is created")
def napoln_home_exists(napoln_env):
    assert (napoln_env.home / ".napoln").is_dir()
    assert (napoln_env.home / ".napoln" / "manifest.toml").is_file()
    assert (napoln_env.home / ".napoln" / "config.toml").is_file()


@then(parsers.parse('the bootstrap skill "{name}" is installed'))
def bootstrap_installed(napoln_env, name):
    assert (napoln_env.home / ".claude" / "skills" / name / "SKILL.md").is_file()


@then("the skill is stored in the content-addressed store")
def skill_in_store(napoln_env):
    store = napoln_env.home / ".napoln" / "store"
    skill_dirs = list(store.iterdir())
    assert len(skill_dirs) >= 1


@then("the skill is placed in the Claude Code skills directory")
def skill_in_claude(napoln_env):
    skills = list((napoln_env.home / ".claude" / "skills").iterdir())
    assert any(s.name != "napoln-manage" for s in skills)


@then("the skill is placed in the shared agents skills directory")
def skill_in_agents(napoln_env):
    skills = list((napoln_env.home / ".agents" / "skills").iterdir())
    assert any(s.name != "napoln-manage" for s in skills)


@then(parsers.parse("the exit code is {code:d}"))
def check_exit_code(napoln_env, code):
    assert napoln_env.result.exit_code == code


@then(parsers.parse('the output contains "{text}"'))
def output_contains(napoln_env, text):
    assert text in napoln_env.result.output


@then("all placements use copy mode")
def all_copy_mode(napoln_env):
    import tomllib
    manifest = napoln_env.home / ".napoln" / "manifest.toml"
    data = tomllib.loads(manifest.read_text())
    for skill in data.get("skills", {}).values():
        for agent in skill.get("agents", {}).values():
            assert agent["link_mode"] == "copy"


@then("no files are modified on disk")
def no_disk_changes(napoln_env):
    """Verify disk state matches pre-command snapshot."""
    assert napoln_env.disk_snapshot_matches()


@then("the manifest is unchanged")
def manifest_unchanged(napoln_env):
    assert napoln_env.manifest_snapshot_matches()


@then(parsers.parse('the manifest version is "{version}"'))
def manifest_version(napoln_env, version):
    import tomllib
    manifest = napoln_env.home / ".napoln" / "manifest.toml"
    data = tomllib.loads(manifest.read_text())
    # Find the skill — there should be one under test
    for skill in data["skills"].values():
        assert skill["version"] == version


@then("the Claude Code placement contains conflict markers")
def has_conflict_markers(napoln_env):
    for skill_dir in (napoln_env.home / ".claude" / "skills").iterdir():
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text()
            if "<<<<<<<" in content:
                return
    pytest.fail("No conflict markers found")


@then(parsers.parse('the output contains "Would" for each planned action'))
def dry_run_output(napoln_env):
    assert "Would" in napoln_env.result.output
    assert "Dry run" in napoln_env.result.output
```

#### Shared BDD Fixture: `tests/steps/conftest.py`

```python
import pytest
from pathlib import Path
from typer.testing import CliRunner


class NapolnTestEnv:
    """Isolated napoln environment for BDD tests.

    Redirects HOME, NAPOLN_HOME, and all agent directories to a temporary
    directory so tests don't touch real agent installations.
    """

    def __init__(self, tmp_path: Path):
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.result = None
        self._disk_snapshot = None
        self._manifest_snapshot = None
        self.env_vars = {
            "HOME": str(self.home),
            "NAPOLN_HOME": str(self.home / ".napoln"),
            "NAPOLN_TELEMETRY": "off",  # Never prompt in tests
        }
        # Fake upstream repo for version tests
        self.upstream_dir = tmp_path / "upstream"
        self.upstream_dir.mkdir()

    def create_local_skill(self, name: str, version: str = "1.0.0") -> Path:
        skill_dir = self.home / "local-skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A test skill.\n"
            f"metadata:\n  version: \"{version}\"\n---\n\n# {name}\n\nTest body.\n"
        )
        return skill_dir

    def install_skill(self, name: str, version: str):
        """Simulate a full napoln add."""
        from napoln.cli import app
        skill_path = self.create_local_skill(name, version)
        runner = CliRunner()
        runner.invoke(app, ["add", str(skill_path)], env=self.env_vars)

    def modify_placement(self, agent: str, section: str = "default"):
        """Edit a placement's SKILL.md to simulate user customization."""
        agent_map = {
            "Claude Code": self.home / ".claude" / "skills",
            "Gemini CLI": self.home / ".agents" / "skills",
        }
        agent_dir = agent_map.get(agent, self.home / ".agents" / "skills")
        for skill_dir in agent_dir.iterdir():
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists() and skill_md.name != "napoln-manage":
                content = skill_md.read_text()
                content += f"\n## {section}\n\nCustom local addition.\n"
                skill_md.write_text(content)

    def create_upstream_version(self, version: str):
        """Create a new version of the skill in the fake upstream."""
        # Implementation depends on resolver — may create a new tagged commit
        # in a local git repo, or a new directory in upstream_dir
        pass

    def snapshot_disk(self):
        """Snapshot current state for dry-run assertions."""
        # Record file hashes for comparison
        pass

    def disk_snapshot_matches(self) -> bool:
        return True  # Compare against snapshot

    def manifest_snapshot_matches(self) -> bool:
        return True  # Compare manifest against snapshot


@pytest.fixture
def napoln_env(tmp_path):
    return NapolnTestEnv(tmp_path)


@pytest.fixture
def cli_runner():
    return CliRunner()
```

### 17.4 Test Organization Rules

1. **Unit tests come first.** Before implementing any module in `src/napoln/core/`, write the parameterized test file. Run the tests, watch them fail, then implement.

2. **Feature files mirror STORIES.md.** Each BDD story maps to one `.feature` file. When a story is updated, update the feature file. They are the executable version of the stories.

3. **Step definitions are shared.** Given/When/Then steps are reusable across features. Keep them in `tests/steps/given.py`, `when.py`, `then.py`. Use `parsers.parse()` for parameterized steps.

4. **Fixtures over mocks.** Prefer real filesystem operations in `tmp_path` over mocking. The `NapolnTestEnv` fixture creates an isolated home directory that mimics a real system. Only mock external I/O (network, reflink syscalls).

5. **Parameterize for coverage, don't duplicate tests.** If you're writing a second test that differs only by input, use `@pytest.mark.parametrize` instead.

6. **Integration tests use `CliRunner`.** Typer's `CliRunner` (wrapping Click's) captures output and exit codes without spawning a subprocess. Use it for all CLI tests.

### 17.5 Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# BDD features only
pytest tests/features/

# A specific feature
pytest tests/features/upgrade.feature

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=napoln --cov-report=term-missing

# Specific parameterized case
pytest tests/unit/test_validator.py -k "uppercase"
```

### 17.6 Test Pyramid Target

```
         ╱╲
        ╱  ╲         BDD Features (8 feature files, ~30 scenarios)
       ╱    ╲        End-to-end user workflows
      ╱──────╲
     ╱        ╲      Integration (CLI tests)
    ╱          ╲     Command parsing, output format, exit codes
   ╱────────────╲
  ╱              ╲   Unit (parameterized)
 ╱                ╲  Every function in core/ — edge cases, errors, happy paths
╱──────────────────╲
```

---

## 18. User Stories & Examples

See [STORIES.md](STORIES.md) for:

- **8 BDD scenarios** covering: first run, browsing, selective install, status/diff, upgrade with merge, team workflows, health checks, and garbage collection
- **5 detailed command output examples** with exact terminal output for: `--help`, `add` (first run), `add --dry-run`, `upgrade --dry-run` / `upgrade` (clean merge and conflict), `status` / `doctor` (including `--json` variants)
- **`--dry-run` design principles** and per-command applicability matrix

---

## 19. Implementation Plan

### Phase 1: Core (MVP)

**Goal:** `napoln add`, `napoln status`, `napoln remove` work end-to-end.

| Module | Scope |
|--------|-------|
| `hasher.py` | Content hashing |
| `store.py` | Store creation, content-addressed write |
| `linker.py` | Reflink with copy fallback |
| `agents.py` | Agent detection, path resolution |
| `manifest.py` | Read/write manifest TOML |
| `validator.py` | SKILL.md validation |
| `commands/add.py` | Install from local path |
| `commands/remove.py` | Uninstall |
| `commands/status.py` | Show installed skills |
| `cli.py` | CLI entry point |
| Bootstrap skill | `napoln-manage` SKILL.md |

**Deliverable:** Can install a skill from a local directory, place it in agent directories, track in manifest, remove it.

### Phase 2: Git Sources + Upgrade

**Goal:** Install from git, upgrade with three-way merge.

| Module | Scope |
|--------|-------|
| `resolver.py` | Git clone, tag resolution, semver matching |
| `merger.py` | Three-way merge via `git merge-file` |
| `commands/upgrade.py` | Upgrade flow with merge |
| `commands/diff.py` | Show local modifications |
| `commands/resolve.py` | Mark conflicts resolved |

**Deliverable:** Full install-customize-upgrade cycle from git sources.

### Phase 3: Reliability + Polish

**Goal:** Production-quality tooling.

| Module | Scope |
|--------|-------|
| `commands/sync.py` | Repair placements |
| `commands/doctor.py` | Health checks |
| `commands/gc.py` | Garbage collection |
| `commands/list_cmd.py` | List skills in a source |
| `telemetry.py` | Opt-in telemetry |
| `commands/config.py` | Config management |
| `output.py` | Rich terminal output |
| First-run experience | Bootstrap flow |

**Deliverable:** Stable CLI with good error messages, diagnostics, and first-run experience.

### Phase 4: Distribution + Community

**Goal:** Publish to PyPI, gather feedback, iterate.

| Activity | Scope |
|----------|-------|
| PyPI release | `uvx napoln` works |
| README + docs | User-facing documentation |
| Example skill repos | Demonstrate the workflow |
| Community skills | Encourage skill authoring |

### Future Phases

- Registry API and web UI
- `napoln search` via registry
- Skill ratings and reviews
- Compile-to-agent adapter (if agent formats diverge)
- Skill dependencies (if needed)
- Lock file (if dependencies are added)
