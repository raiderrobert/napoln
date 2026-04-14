# Architecture: Reflink-First Store with Per-Agent Working Copies

## Design Principles

**Versioned, not copied.** Skills are tracked dependencies with semantic versioning and three-way merge. No symlink fragility. No copy drift. Inspired by [graft](https://github.com/raiderrobert/graft).

**Decentralized.** Any git repo is a valid source. No registry required to publish or install. Go modules model, not npm-central model.

**Content-addressed.** Every stored version has a deterministic SHA-256 hash. Same content → same hash. You always know exactly what you have. Nix model.

**Depth over breadth.** Five agents supported well beats forty supported poorly. Each target agent gets tested, validated integration.

**Transparent telemetry.** Opt-in only. `napoln telemetry show-data` shows exactly what would be sent. Nothing is collected by default.

**Self-describing.** napoln ships a bootstrap skill (`napoln-manage`) that teaches agents how to use it. The tool describes itself to the agent, so users can discover and manage skills without leaving their preferred agent.

## Prior Art

| Project | What we learned |
|---------|----------------|
| [Vercel skills](https://github.com/vercel-labs/skills) | The problem space and the [Agent Skills standard](https://agentskills.io/specification) |
| [graft](https://github.com/raiderrobert/graft) | Versioned file-level dependency management with three-way merge |
| Go modules | Decentralized sourcing, minimal infrastructure |
| Nix | Content-addressed packages, reproducibility |
| npm / cargo / uv | Registry-based discovery, semantic versioning, lockfile patterns |

## Design Inspiration

This architecture draws directly from how **uv** and **pnpm** solve the same fundamental problem: content needs to appear in multiple locations without wasting disk or creating fragile links.

| Tool | Store | Placement | Mutability | Fallback |
|------|-------|-----------|------------|----------|
| **pnpm** | Content-addressed file store (`~/.local/share/pnpm/store/v3/`) | Hardlinks per-file, symlinks for directory graph | Immutable (packages never edited) | Copy |
| **uv** | Cache directory (`~/.cache/uv/`) | Clone/reflink per-file | Immutable (packages never edited) | Clone → Hardlink → Copy |
| **napoln** | Origin store (`~/.napoln/store/`) | Clone/reflink per-file | **Mutable** (skills are customized) | Clone → Copy (skip hardlink — see below) |

The key difference: pnpm and uv install immutable packages. napoln installs mutable skills that users customize. This makes **clone/reflink the ideal strategy** — it gives us zero-cost copies that naturally diverge on write, enabling per-agent customization without any extra machinery.

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

Codex additionally supports an optional `agents/openai.yaml` sidecar file for richer metadata (display name, icons, tool dependencies, invocation policy). napoln treats this like any other supporting file in the skill directory.

---

## Store Layout

```
~/.napoln/
├── config.toml                             # User config: registry, telemetry, default agents
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

When a new version of a skill is fetched, a new directory appears in the store. Old versions are retained until `napoln gc` or `napoln upgrade` cleans them up.

### What's In Agent Directories

```
# These are WORKING COPIES — the user's editable versions.
# Created via reflink from the store.

~/.claude/skills/my-skill/
├── SKILL.md                    # reflink of store/.../SKILL.md (zero-cost until edited)
├── scripts/
│   └── run.sh                  # reflink of store/.../scripts/run.sh
└── .napoln                     # napoln tracking metadata (hidden file)

~/.gemini/skills/my-skill/
├── SKILL.md                    # independent reflink (free until edited)
├── scripts/
│   └── run.sh
└── .napoln

~/.agents/skills/my-skill/      # shared by Gemini CLI + pi
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

This makes each placement self-describing. Even without the global manifest, napoln can figure out what it's looking at.

---

## Link Strategy

### Primary: Clone/Reflink (Copy-on-Write)

On APFS (macOS) and btrfs/xfs/bcachefs (Linux), `clonefile()` / `ioctl_ficlone()` creates a copy that:
- **Looks like a regular file** — no symlink weirdness, no tool confusion
- **Costs zero disk** — shares storage blocks with the original until modified
- **Diverges on write** — if the user edits the file, only the modified blocks are allocated. The original (store) is untouched.

This is exactly what we want. Each agent gets an independent working copy for free. If the user customizes a skill for Claude Code but not Gemini, only the Claude Code copy costs extra storage.

### Fallback: Copy

If reflink is unavailable (older filesystems, cross-device, Windows without Dev Drive):
- Fall back directly to **copy**
- Skip hardlink — hardlinks share writes, meaning an edit in one agent directory would affect all agents. This is wrong for mutable content where per-agent customization should be possible.

```
Fallback chain:  clone/reflink  →  copy
                 (preferred)       (universal)
```

This is simpler than uv's chain (clone → hardlink → copy) because our mutability requirement rules out hardlinks as a useful intermediate.

### Why Not Hardlinks?

pnpm and uv use hardlinks because their packages are immutable. For mutable skills:
- Editing `~/.claude/skills/my-skill/SKILL.md` would silently modify `~/.gemini/skills/my-skill/SKILL.md` (same inode)
- The user would have no idea this happened
- Per-agent customization would be impossible
- Some editors break hardlinks on save (write-to-temp + rename), causing silent divergence that's hard to debug

Hardlinks are the wrong tool for mutable content.

### Why Not Symlinks?

uv explicitly warns against symlinks: "clearing the cache will break all installed packages." The same applies here — if the store is cleaned up, symlinks break and agents silently lose skills.

Additionally:
- Claude Code watches skill directories for changes; symlinks may confuse file watchers
- `.gitignore` and git behave differently with symlinks
- Some tools don't follow symlinks
- They create tight coupling between the store and agent directories

Reflinks give us the independence of copies with the efficiency of links.

---

## Manifest

```toml
# ~/.napoln/manifest.toml

[napoln]
version = "0.1.0"
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
  path = "~/.gemini/skills/my-skill"
  link_mode = "clone"
  scope = "global"

  [skills.my-skill.agents.pi]
  path = "~/.agents/skills/my-skill"
  link_mode = "copy"              # fell back to copy on this system
  scope = "global"

[skills.code-review]
source = "github.com/other/repo/skills/code-review"
version = "2.0.1"
store_hash = "d19e4a..."
installed = "2026-04-14T10:00:00Z"

  [skills.code-review.agents.claude-code]
  path = ".claude/skills/code-review"   # relative = project-level
  link_mode = "clone"
  scope = "project"
```

### Project-Level Manifest

Projects can also have a `.napoln/manifest.toml` at the project root, tracking project-scoped skill installations:

```
my-project/
├── .napoln/
│   └── manifest.toml               # Project-level skill tracking
├── .claude/skills/code-review/     # Reflinked working copy
├── .gemini/skills/code-review/     # Reflinked working copy
├── .agents/skills/code-review/     # Reflinked working copy
└── ...
```

---

## Core Workflows

### Install

```
$ napoln add github.com/owner/repo/skills/my-skill

1. Resolve source
   - Parse source identifier
   - Clone/fetch git repo (or download from registry)
   - Locate skill directory in repo

2. Store
   - Hash skill contents → ab3f7c...
   - Copy to store: ~/.napoln/store/my-skill/1.2.0-ab3f7c/
   - This is the pristine upstream — immutable from this point

3. Detect agents
   - Scan for ~/.claude/, ~/.gemini/, ~/.pi/, ~/.agents/
   - Or use explicit --agents flag

4. Place working copies
   - For each target agent:
     a. Try reflink/clone from store → agent skill directory
     b. If reflink fails on first file: fall back to copy
     c. Write .napoln provenance file
     d. Record link_mode in manifest

5. Update manifest
   - Add entry to ~/.napoln/manifest.toml
   - Record version, hash, agent placements, link modes
```

### Upgrade

```
$ napoln upgrade my-skill

1. Fetch new upstream
   - Resolve latest version (or specified version)
   - Download to cache, extract

2. Store new version
   - Hash new contents → d19e4a...
   - Store at ~/.napoln/store/my-skill/1.3.0-d19e4a/

3. Three-way merge (per agent)
   For each agent placement:

   BASE:   store/my-skill/1.2.0-ab3f7c/SKILL.md    (pristine v1.2.0)
   OURS:   ~/.claude/skills/my-skill/SKILL.md        (user's working copy, may be customized)
   THEIRS: store/my-skill/1.3.0-d19e4a/SKILL.md     (pristine v1.3.0)

   Cases:
   a. OURS == BASE (no local changes)
      → Replace with reflink of new store version. Fast path.

   b. OURS != BASE, no conflicts with THEIRS
      → Apply three-way merge. Write result to agent directory.
      → The result is a plain file (no longer a reflink — it has merged content).

   c. OURS != BASE, conflicts with THEIRS
      → Write merge result with conflict markers to agent directory.
      → Alert user (or let bootstrap skill resolve).

   d. Repeat for scripts/, references/, etc.
      → For non-SKILL.md files, default to "replace if unchanged, warn if changed."

4. Update manifest
   - Point store_hash to new version
   - Retain old store version until `napoln gc`

5. Optionally clean old store version
   - `napoln gc` removes store versions not referenced by any manifest
```

### Sync / Repair

```
$ napoln sync

For each skill in manifest:
  For each agent placement:
    - Verify agent directory exists and has expected files
    - If missing: re-place from store (reflink or copy)
    - If .napoln provenance file is missing: warn but don't overwrite
      (user may have manually placed a skill)

$ napoln doctor

  - Verify store integrity (hash check)
  - Verify all manifest entries have valid store versions
  - Verify all agent placements exist
  - Report link_mode per placement
  - Report which skills have local modifications (diff against store)
```

### Status / Diff

```
$ napoln status

my-skill v1.2.0 (github.com/owner/repo)
  claude-code  ~/.claude/skills/my-skill     modified (SKILL.md)
  gemini-cli   ~/.gemini/skills/my-skill     clean
  pi           ~/.agents/skills/my-skill     clean

code-review v2.0.1 (github.com/other/repo)
  claude-code  .claude/skills/code-review    clean
  gemini-cli   .gemini/skills/code-review    clean

$ napoln diff my-skill --agent claude-code

--- store (upstream v1.2.0)
+++ ~/.claude/skills/my-skill/SKILL.md (working copy)
@@ -5,3 +5,5 @@
 ## Instructions
 1. Review the code
+2. Focus on security implications
+3. Check error handling
 ...
```

### Uninstall

```
$ napoln remove my-skill

1. Remove agent directory placements
   - Delete ~/.claude/skills/my-skill/
   - Delete ~/.gemini/skills/my-skill/
   - Delete ~/.agents/skills/my-skill/

2. Remove from manifest

3. Store version retained until `napoln gc`
   (allows undo / reinstall at same version)
```

---

## Three-Way Merge Details

### Algorithm

We use a standard three-way merge (same algorithm as `git merge-file`):

```
         BASE (store pristine v1)
        /    \
      OURS    THEIRS
  (working     (store pristine v2)
   copy)
        \    /
        MERGED
```

Python has `difflib` in the standard library, but for robust three-way merge we should use a proper implementation. Options:
- Shell out to `git merge-file` (available everywhere git is installed — and our users have git)
- Use `merge3` Python library
- Implement using `difflib.SequenceMatcher`

Given our users are developers with git installed, `git merge-file` is the pragmatic choice. It handles conflict markers, whitespace, and edge cases correctly. If git isn't available, fall back to a simpler Python implementation.

### What Gets Merged

| File | Merge strategy |
|------|---------------|
| `SKILL.md` | Full three-way merge (this is the primary content users customize) |
| `scripts/*` | Replace if unchanged; warn + keep local if modified |
| `references/*` | Replace if unchanged; warn + keep local if modified |
| `assets/*` | Replace if unchanged; warn + keep local if modified |
| `.napoln` | Always overwritten with new provenance |

### Conflict Resolution

When three-way merge produces conflicts:

1. **Write conflict markers** to the file (standard `<<<<<<<` / `=======` / `>>>>>>>` format)
2. **Print a clear message** telling the user which files have conflicts
3. **Let the agent help** — the bootstrap skill teaches agents to look for and resolve conflict markers
4. **`napoln resolve my-skill --agent claude-code`** — marks conflicts as resolved after user/agent edits

### The "No Local Changes" Fast Path

Most users won't customize most skills. On upgrade:
1. Diff working copy against store base
2. If identical → just reflink the new version over the old. No merge needed.
3. This should be the common case and should be instant.

---

## Edge Cases

### Cross-Filesystem Placements

If `~/.napoln/store/` and `~/.claude/` are on different filesystems:
- Reflink will fail (reflinks are same-filesystem only)
- Fall back to copy
- This is detected on first file and recorded in manifest

### Disk Usage with Copies

When the fallback is copy, we're duplicating content. For skills (typically a few KB of markdown + small scripts), this is negligible. A skill with 10KB of content across 3 agents = 30KB of copies + 10KB store = 40KB total. Not a concern.

### User Edits the Store Directly

The store is not exposed to users. It lives in `~/.napoln/store/` which is an implementation detail. If someone edits it, `napoln doctor` will detect the hash mismatch and warn.

### Agent Creates/Modifies a Skill

Some agents (Gemini CLI's `skill-creator`) can create new skills. If an agent creates a skill in `.gemini/skills/new-skill/`, napoln doesn't know about it — it's not in the manifest. This is fine. napoln only manages skills it installed. `napoln status` could note untracked skills.

If an agent modifies a napoln-managed skill, the modification happens on the working copy. This is the intended workflow — `napoln upgrade` will merge the changes.

### Multiple Projects, Same Skill, Different Versions

Project A wants `my-skill@1.2.0`, Project B wants `my-skill@1.3.0`. Both versions exist in the store. Each project's `.claude/skills/my-skill/` is reflinked from its respective store version. No conflict — the store is versioned.

### Windows

Windows support for reflinks:
- **Dev Drive (ReFS)**: Supports `block_clone` (reflinks). uv uses this on Windows with Dev Drive.
- **NTFS**: No reflink support. Fall back to copy.
- **WSL**: APFS/btrfs behavior depending on filesystem.

For Windows without Dev Drive, napoln falls back to copy. Skills are small; the disk cost is negligible.

---

## Distribution Model

### Source Resolution

Skills can come from:

```bash
# Git repo (Go-module style — any repo is a valid source)
napoln add github.com/owner/repo                    # whole repo as skill source
napoln add github.com/owner/repo/skills/my-skill    # specific skill in repo
napoln add github.com/owner/repo@v1.2.0             # pinned version

# Registry (npm-style — optional, for discovery)
napoln add my-skill                                  # resolve from registry
napoln add @owner/my-skill                           # namespaced registry lookup

# Local path (for development)
napoln add ./path/to/skill
```

### Version Resolution

- **Git tags**: `v1.2.0` → semver. `napoln upgrade` finds the latest semver tag.
- **Git branches**: `@main` → track a branch. `napoln upgrade` pulls latest commit.
- **Git commits**: `@abc123` → pin to exact commit. No upgrade unless explicit.
- **Registry**: Semver ranges, similar to npm/cargo. `^1.2.0`, `~1.2.0`, `>=1.0`.

### Content Addressing

Each stored version is identified by `{version}-{hash}` where hash = SHA-256 of:
```
sort(all files in skill directory) → for each: "{relative_path}\0{file_contents}\0" → SHA-256
```

This gives us:
- **Integrity verification**: Know exactly what you have
- **Deduplication**: Same content from different sources = same hash = one store entry
- **Reproducibility**: Pin to a hash for bit-for-bit certainty

---

## Bootstrap Skills

napoln ships with skills that teach agents how to use it:

### `napoln-manage`

```markdown
---
name: napoln-manage
description: >
  Search, install, upgrade, and manage agent skills using napoln.
  Use when the user wants to find new skills, install a skill,
  check for updates, or manage their installed skills.
---

# napoln — Skill Package Manager

You can manage skills for the user using the `napoln` CLI.

## Search for Skills

\`\`\`bash
napoln search "testing"
napoln search "code review" --agent claude-code
\`\`\`

## Install a Skill

\`\`\`bash
napoln add github.com/owner/repo/skills/skill-name
napoln add skill-name              # from registry
\`\`\`

## Check Status

\`\`\`bash
napoln status                     # show all installed skills
napoln diff skill-name            # show local modifications
\`\`\`

## Upgrade

\`\`\`bash
napoln upgrade                    # upgrade all skills
napoln upgrade skill-name         # upgrade one skill
\`\`\`

## Resolve Merge Conflicts

After upgrade, if there are conflicts:
1. Look for `<<<<<<<`, `=======`, `>>>>>>>` markers in SKILL.md
2. Edit to resolve, keeping the best of both versions
3. Run `napoln resolve skill-name`
```

This skill is installed automatically when napoln is first run. It dogfoods the skill format — it's a regular skill managed by napoln itself.

---

## Telemetry

Telemetry is a first-class concern, not an afterthought.

### What's Collected

```toml
# ~/.napoln/config.toml

[telemetry]
enabled = true                    # explicit opt-in during first run
anonymous_id = "uuid"             # random, not tied to identity

# What we send:
# - Command name (add, upgrade, remove, search)
# - Skill source (registry vs git)
# - Agent targets
# - Link mode used (clone, copy)
# - OS and architecture
# - napoln version
# - Success/failure
#
# What we never send:
# - Skill names or content
# - File paths
# - Git URLs or repo names
# - Any user-identifiable information
```

### First-Run Prompt

```
napoln collects anonymous usage data to improve the tool.
This includes: commands used, OS type, link mode, success/failure.
This never includes: skill names, file paths, or personal info.

Enable telemetry? [y/N]
```

### Transparency

- `napoln telemetry status` — show what's enabled, what's been sent
- `napoln telemetry disable` — turn off
- `napoln telemetry show-data` — display exactly what would be sent
- All telemetry code is in one module, easy to audit

---

## CLI Surface

```
napoln add <source> [--agents <a,b,c>] [--version <constraint>] [--global|--project]
napoln remove <name> [--agents <a,b,c>]
napoln upgrade [<name>] [--version <constraint>]
napoln status
napoln diff <name> [--agent <agent>]
napoln resolve <name> [--agent <agent>]
napoln search <query> [--agent <agent>]
napoln sync                        # repair/recreate placements from manifest + store
napoln doctor                      # health check: store integrity, placement validity
napoln gc                          # remove unreferenced store versions
napoln config                      # edit config.toml
napoln telemetry <status|enable|disable|show-data>
```

---

## Project Structure

```
napoln/
├── pyproject.toml
├── src/
│   └── napoln/
│       ├── __init__.py
│       ├── cli.py                  # Click/Typer CLI entry point
│       ├── manifest.py             # Manifest read/write (TOML)
│       ├── store.py                # Content-addressed store operations
│       ├── linker.py               # Reflink/copy with fallback chain
│       ├── resolver.py             # Source resolution (git, registry, local)
│       ├── merger.py               # Three-way merge (shells to git merge-file)
│       ├── agents.py               # Agent detection and path configuration
│       ├── hasher.py               # Content hashing for store addressing
│       ├── telemetry.py            # Telemetry collection and reporting
│       └── skills/                 # Bootstrap skills (bundled)
│           └── napoln-manage/
│               └── SKILL.md
├── tests/
└── README.md
```

---

## Resolved Questions

These were open during design. Decisions are now implemented.

1. **Registry at launch?** No. v0.1 ships with git-only sources. The CLI parses registry identifiers and returns a clear "not yet available" message. The manifest format supports it for future addition.

2. **Lock file?** No. The manifest pins exact versions and content hashes, which provides sufficient reproducibility. A lock file adds value when there are transitive dependencies — skills don't have dependencies on other skills.

3. **Skill authoring format:** Just a directory with `SKILL.md`. No `napoln.toml` required. Skill discovery is purely based on the Agent Skills standard. This means existing skill repos work without modification.

4. **Agent-specific frontmatter:** One SKILL.md serves all agents. Agents ignore fields they don't understand, so a single file can include a superset (`allowed-tools` for Claude Code, `disable-model-invocation` for pi). No overlay mechanism.

5. **`.gitignore` strategy:** Commit the manifest, gitignore the placements. Team members run `napoln install` after clone. Same pattern as `package.json` + `node_modules/`.

## Future Considerations

- **Registry API and web UI** for discovery beyond git
- **Compile-to-agent adapter** if agent formats diverge significantly
- **Skill dependencies** and a lock file if skills ever depend on other skills
