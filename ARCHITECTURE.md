# Architecture: Reflink-First Store with Per-Agent Working Copies

## Design Principles

**Versioned, not copied.** Skills are tracked dependencies with semantic versioning and three-way merge. No symlink fragility. No copy drift. Inspired by [graft](https://github.com/raiderrobert/graft).

**Decentralized.** Any git repo is a valid source. No registry required to publish or install. Go modules model, not npm-central model.

**Content-addressed.** Every stored version has a deterministic SHA-256 hash. Same content → same hash. Nix model.

**Depth over breadth.** Five agents supported well beats forty supported poorly. Each target agent gets tested, validated integration.

**Self-describing.** napoln ships a bootstrap skill (`napoln-manage`) that teaches agents how to use it. The tool describes itself to the agent, so users can discover and manage skills without leaving their preferred agent.

## Prior Art

| Project | Lesson |
|---------|----------------|
| [Vercel skills](https://github.com/vercel-labs/skills) | The problem space and the [Agent Skills standard](https://agentskills.io/specification) |
| [graft](https://github.com/raiderrobert/graft) | Versioned file-level dependency management with three-way merge |
| [mise](https://mise.jdx.dev/) | Dual-scope model (global config + per-project config), `install` syncs both |
| Go modules | Decentralized sourcing, minimal infrastructure |
| Nix | Content-addressed packages, reproducibility |
| Homebrew | `Brewfile` dump/restore pattern for declarative tool management |
| npm / cargo / uv | Registry-based discovery, semantic versioning, lockfile patterns |

## Design Inspiration

This architecture draws directly from how **uv** and **pnpm** solve the same fundamental problem: content needs to appear in multiple locations without wasting disk or creating fragile links.

| Tool | Store | Placement | Mutability | Fallback |
|------|-------|-----------|------------|----------|
| **pnpm** | Content-addressed file store (`~/.local/share/pnpm/store/v3/`) | Hardlinks per-file, symlinks for directory graph | Immutable (packages never edited) | Copy |
| **uv** | Cache directory (`~/.cache/uv/`) | Clone/reflink per-file | Immutable (packages never edited) | Clone → Hardlink → Copy |
| **napoln** | Origin store (`~/.napoln/store/`) | Clone/reflink per-file | **Mutable** (skills are customized) | Clone → Copy (skip hardlink — see below) |

The key difference: pnpm and uv install immutable packages. napoln installs mutable skills that users customize. Clone/reflink is the ideal strategy — zero-cost copies that naturally diverge on write, enabling per-agent customization without extra machinery.

---

## Agent Skill Discovery (Constraints)

All five target agents implement the [Agent Skills standard](https://agentskills.io/specification) with identical `SKILL.md` format. The only difference is the directory they read from:

| Agent | Global | Project | Custom Paths? |
|-------|--------|---------|---------------|
| **Claude Code** | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` | ❌ No |
| **Gemini CLI** | `~/.gemini/skills/<name>/`, `~/.agents/skills/<name>/` | `.gemini/skills/<name>/`, `.agents/skills/<name>/` | ❌ No |
| **pi** | `~/.pi/agent/skills/<name>/`, `~/.agents/skills/<name>/` | `.pi/skills/<name>/`, `.agents/skills/<name>/` | ✅ Yes |
| **Codex** | `~/.agents/skills/<name>/` | `.agents/skills/<name>/` | ❌ No |
| **Cursor** | `~/.cursor/skills/<name>/` | `.agents/skills/<name>/` | ❌ No |

Claude Code and Cursor have their own global paths. Gemini CLI, pi, and Codex all read from `~/.agents/skills/`. At the project level, `.agents/skills/` is shared by Gemini CLI, pi, Codex, Cursor, and [40+ other agents](https://github.com/vercel-labs/skills#available-agents). Only Claude Code requires `.claude/skills/`.

---

## Store Layout

```
~/.napoln/
├── config.toml                             # User config: default agents, default scope
├── manifest.toml                           # Global manifest: all installed skills
│
├── store/                                  # Pristine upstream snapshots (immutable)
│   └── <name>/
│       └── <version>-<hash>/               # e.g. my-skill/1.2.0-ab3f7c/
│           ├── SKILL.md                    # Original upstream content — NEVER edited
│           ├── scripts/
│           └── references/
│
└── cache/                                  # Downloaded tarballs, git clones (purgeable)
    └── github.com/
        └── owner/repo/
            └── <hash>.tar.gz
```

### What's In the Store

The store holds **pristine upstream content**. It is the merge base for three-way merge. It is never edited by the user. It is content-addressed: the hash suffix is derived from the SHA-256 of all files in the skill directory (sorted, concatenated).

When a new version of a skill is fetched, a new directory appears in the store. Old versions are retained until `napoln config gc` cleans them up.

### What's In Agent Directories

```
# These are WORKING COPIES — the user's editable versions.
# Created via reflink from the store.

~/.claude/skills/my-skill/
├── SKILL.md                    # reflink of store/.../SKILL.md (zero-cost until edited)
├── scripts/
│   └── run.sh                  # reflink of store/.../scripts/run.sh
└── .napoln                     # napoln tracking metadata (hidden file)

~/.agents/skills/my-skill/      # shared by Gemini CLI, pi, Codex
├── SKILL.md
├── scripts/
│   └── run.sh
└── .napoln
```

The `.napoln` file in each skill directory tracks provenance:

```toml
# .napoln — provenance tracking (do not edit)
source = "github.com/owner/repo/skills/my-skill"
version = "1.2.0"
store_hash = "ab3f7c..."
link_mode = "clone"             # or "copy" if reflink unavailable
installed = "2026-04-14T09:00:00Z"
```

Each placement is self-describing. Even without the global manifest, napoln can recover provenance from the `.napoln` file alone.

---

## Link Strategy

### Primary: Clone/Reflink (Copy-on-Write)

On APFS (macOS) and btrfs/xfs/bcachefs (Linux), `clonefile()` / `ioctl_ficlone()` creates a copy that:
- **Looks like a regular file** — no symlink weirdness, no tool confusion
- **Costs zero disk** — shares storage blocks with the original until modified
- **Diverges on write** — if the user edits the file, only the modified blocks are allocated. The original (store) is untouched.

Each agent gets an independent working copy at zero disk cost. If a user customizes a skill for Claude Code but not Gemini, only the Claude Code copy allocates extra storage.

### Fallback: Copy

If reflink is unavailable (ext4, older filesystems, cross-device, Windows without Dev Drive):
- Fall back directly to **copy**
- Skip hardlink — hardlinks share writes, meaning an edit in one agent directory would affect all agents. Incompatible with mutable content where per-agent customization is expected.

```
Fallback chain:  clone/reflink  →  copy
                 (preferred)       (universal)
```

### Why Not Hardlinks?

pnpm and uv use hardlinks because their packages are immutable. For mutable skills:
- Editing `~/.claude/skills/my-skill/SKILL.md` would silently modify `~/.agents/skills/my-skill/SKILL.md` (same inode)
- Per-agent customization would be impossible
- Some editors break hardlinks on save (write-to-temp + rename), causing silent divergence

### Why Not Symlinks?

uv explicitly warns against symlinks: "clearing the cache will break all installed packages." The same applies here — if the store is cleaned up, symlinks break and agents silently lose skills. Additionally, some tools don't follow symlinks, and `.gitignore` behaves differently with them.

Reflinks provide the independence of copies with the efficiency of links.

---

## Manifest

```toml
# ~/.napoln/manifest.toml

[napoln]
schema = 1

[skills.my-skill]
source = "github.com/owner/repo/skills/my-skill"
version = "1.2.0"
store_hash = "ab3f7c..."
installed = "2026-04-14T09:00:00Z"

  [skills.my-skill.agents.claude-code]
  path = "~/.claude/skills/my-skill"
  link_mode = "clone"
  scope = "global"

  [skills.my-skill.agents.gemini-cli]
  path = "~/.agents/skills/my-skill"
  link_mode = "clone"
  scope = "global"
```

### Dual-Scope Manifests

Following the mise model, napoln supports both global and project manifests:

- **Global** (`~/.napoln/manifest.toml`): Skills always available. Put this in dotfiles for the new-machine story.
- **Project** (`.napoln/manifest.toml`): Skills specific to a codebase. Committed to git. Teammates run `napoln install`.

`napoln install` syncs both manifests automatically, similar to `mise install`.

---

## Core Workflows

### Add

```
$ napoln add owner/repo --skill code-review

1. Parse source → clone/fetch git repo → locate skill directory
2. Hash skill contents → store at ~/.napoln/store/code-review/1.2.0-ab3f7c/
3. Detect agents (or use --agents override)
4. Place working copies via reflink (or copy fallback) into each agent directory
5. Write .napoln provenance file in each placement
6. Update manifest with version, hash, agent placements
```

For multi-skill repos without `--skill` or `--all`, an interactive picker is shown.

### Upgrade

```
$ napoln upgrade code-review

1. Re-resolve source → fetch latest version → store new version
2. For each agent placement, three-way merge:

   BASE:   store/code-review/1.2.0-ab3f7c/SKILL.md  (pristine old)
   OURS:   ~/.claude/skills/code-review/SKILL.md      (user's working copy)
   THEIRS: store/code-review/1.3.0-d19e4a/SKILL.md  (pristine new)

   Cases:
   a. OURS == BASE → fast-forward (reflink new version over old)
   b. OURS != BASE, no conflicts → apply three-way merge
   c. OURS != BASE, conflicts → write conflict markers, exit code 2
   d. Non-SKILL.md files → replace if unchanged, keep + warn if modified

3. Update manifest only if merge was clean
```

Uses `git merge-file` as primary implementation. Falls back to `difflib`-based Python merge when git is unavailable.

### Install

```
$ napoln install

Reads global manifest + project manifest (if present).
For each skill, re-places from store if placement is missing.
Reports what was synced.
```

### List

```
$ napoln list
Global (→ .claude, .cursor, .agents):
  code-review    1.2.0   owner/repo
  my-skill       0.3.1   other/repo

$ napoln list -v
Global (→ ~/.claude/skills  ~/.cursor/skills  ~/.agents/skills):
  code-review    1.2.0   owner/repo
  my-skill       0.3.1   other/repo
```

---

## Three-Way Merge Details

### Algorithm

napoln uses a standard three-way merge (same algorithm as `git merge-file`):

```
         BASE (store pristine v1)
        /    \
      OURS    THEIRS
  (working     (store pristine v2)
   copy)
        \    /
        MERGED
```

`git merge-file` is the primary implementation. When git is unavailable, napoln falls back to a `difflib`-based Python implementation.

### What Gets Merged

| File | Merge strategy |
|------|---------------|
| `SKILL.md` | Full three-way merge (primary content users customize) |
| `scripts/*` | Replace if unchanged; warn + keep local if modified |
| `references/*` | Replace if unchanged; warn + keep local if modified |
| `assets/*` | Replace if unchanged; warn + keep local if modified |
| `.napoln` | Always overwritten with new provenance |

### Conflict Resolution

When three-way merge produces conflicts:

1. Write conflict markers to the file (standard `<<<<<<<` / `=======` / `>>>>>>>` format)
2. Keep the manifest at the old version so re-running `upgrade` works after resolution
3. Print a message telling the user which files have conflicts
4. Exit code 2 to signal conflicts

### The Fast Path

Most users do not customize most skills. On upgrade:
1. Diff working copy against store base
2. If identical → reflink the new version over the old. No merge needed.

---

## Edge Cases

### Cross-Filesystem Placements

If `~/.napoln/store/` and `~/.claude/` are on different filesystems, reflink will fail (same-filesystem only). Fall back to copy. Detected on first file and recorded in manifest.

### Disk Usage with Copies

With the copy fallback, content is duplicated. For skills (typically a few KB of markdown + small scripts), the overhead is negligible.

### User Edits the Store Directly

The store is an implementation detail. If edited directly, `napoln config doctor` detects the hash mismatch and reports corruption.

### Agent Creates/Modifies a Skill

napoln only manages skills it installed. If an agent modifies a napoln-managed skill, the modification happens on the working copy. `napoln upgrade` merges these changes with the new upstream version.

### Multiple Projects, Same Skill, Different Versions

Both versions coexist in the store. Each project's `.claude/skills/my-skill/` is reflinked from its respective store version. The store's version-hash directory structure prevents conflicts.

### Windows

- **Dev Drive (ReFS)**: Supports reflinks. uv uses this on Windows with Dev Drive.
- **NTFS**: No reflink support. Fall back to copy.
- **WSL**: Filesystem-dependent behavior.

The disk cost for skills (typically a few KB) makes copy fallback negligible.

---

## Distribution Model

### Source Resolution

```bash
# Git repo (any repo is a valid source)
napoln add owner/repo                      # interactive picker for multi-skill repos
napoln add owner/repo --all                # install all skills
napoln add owner/repo --skill my-skill     # specific skill by name
napoln add owner/repo@v1.2.0              # pinned version

# Local path (for development)
napoln add ./path/to/skill
```

### Version Resolution

Priority chain: (1) `metadata.version` from SKILL.md frontmatter, (2) semver git tag, (3) git ref, (4) `0.0.0+<short-hash>`.

### Content Addressing

Each stored version is identified by `{version}-{hash}` where hash = SHA-256 of:
```
sort(all files in skill directory) → for each: "{relative_path}\0{file_contents}\0" → SHA-256
```

---

## CLI Surface

```
napoln add <source> [-a|--all] [-s|--skill <name>] [-p|--project] [--agents <list>]
                    [--version <ver>] [--name <name>] [--dry-run]
napoln remove <name> [-p|--project] [--agents <list>] [--dry-run]
napoln upgrade [<name>] [-p|--project] [--version <ver>] [--force] [--dry-run]
napoln list [-p|--project] [-g|--global] [-v|--verbose] [--json]
napoln install [-p|--project] [-g|--global] [--dry-run]
napoln init [<name>]
napoln config
napoln config set <key> <value>
napoln config doctor [-p|--project] [--json]
napoln config gc [--dry-run]
```

---

## Project Structure

```
napoln/
├── pyproject.toml
├── justfile
├── src/
│   └── napoln/
│       ├── __init__.py
│       ├── cli.py                  # Typer CLI entry point (7 commands)
│       ├── errors.py               # Error types
│       ├── output.py               # Terminal output formatting
│       ├── prompts.py              # Interactive skill picker (questionary)
│       ├── commands/               # One module per CLI command
│       │   ├── add.py
│       │   ├── remove.py
│       │   ├── upgrade.py
│       │   ├── list_cmd.py
│       │   ├── install.py
│       │   ├── init.py
│       │   └── config.py          # Also contains doctor and gc subcommands
│       ├── core/                   # Core logic (no CLI dependency)
│       │   ├── agents.py               # Agent detection, path configuration
│       │   ├── hasher.py               # Content hashing (SHA-256)
│       │   ├── linker.py               # Reflink/copy placement
│       │   ├── manifest.py             # Manifest TOML read/write
│       │   ├── merger.py               # Three-way merge (git merge-file + fallback)
│       │   ├── resolver.py             # Source resolution (git, local, registry)
│       │   ├── store.py                # Content-addressed store operations
│       │   └── validator.py            # SKILL.md validation
│       └── skills/                 # Bundled bootstrap skills
│           └── napoln-manage/
│               └── SKILL.md
├── tests/
│   ├── unit/                   # Parameterized pytest tests per core module
│   ├── integration/            # CLI tests via typer.testing.CliRunner
│   ├── features/               # BDD .feature files (pytest-bdd)
│   ├── steps/                  # BDD step definitions
│   └── fixtures/               # Test skill directories
└── README.md
```

---

## Resolved Questions

1. **Registry at launch?** No. v0.1 ships with git-only sources. The CLI parses registry identifiers and returns a clear "not yet available" message.

2. **Lock file?** No. The manifest pins exact versions and content hashes, which provides sufficient reproducibility. A lock file adds value when there are transitive dependencies — skills don't have dependencies on other skills.

3. **Skill authoring format:** A directory with `SKILL.md`. No `napoln.toml` required. Existing skill repos work without modification.

4. **Agent-specific frontmatter:** One SKILL.md serves all agents. Agents ignore fields they don't understand.

5. **`.gitignore` strategy:** Commit the manifest, gitignore the placements. Team members run `napoln install` after clone.

## Future Considerations

- **Registry API and web UI** for discovery beyond git
- **Compile-to-agent adapter** if agent formats diverge significantly
- **Skill dependencies** and a lock file if skills ever depend on other skills
- **Telemetry** with opt-in collection and transparent audit
