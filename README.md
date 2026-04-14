# napoln

> "I don't even have any good skills. You know, like nunchuck skills, bow hunting skills, computer hacking skills."

Your agents don't have any good skills either. **napoln** fixes that.

napoln is a package manager for [agent skills](https://agentskills.io/specification) — reusable instruction sets that make AI coding agents actually useful. Install from any git repo, upgrade without losing your customizations, and manage skills across every agent you use.

```bash
uvx napoln add owner/repo --skill '*'
```

## Why?

Skills are just markdown files that tell agents what to do. But right now managing them means:

- Manually copying files between `~/.claude/skills/`, `~/.agents/skills/`, `~/.cursor/skills/`
- No versioning — you copy a skill, customize it, then the upstream changes and you're stuck
- No way to share a project's skills with your team
- No idea what you have installed or where it came from

napoln treats skills like dependencies. You `add` them, you `upgrade` them, you track them in a manifest. Same mental model as npm, cargo, or uv — but for agent capabilities instead of code libraries.

## Quick Start

```bash
# Install a skill from GitHub
napoln add owner/repo

# Install all skills from a multi-skill repo
napoln add owner/repo --skill '*'

# Install a specific skill by path
napoln add owner/repo/skills/code-review

# Install from a local directory
napoln add ./my-skill

# Pin to a version
napoln add owner/repo@v1.2.0
```

napoln auto-detects your installed agents and places skills in the right directories:

```
✓ Placed 'code-review' in ~/.claude/skills/code-review (clone)
✓ Placed 'code-review' in ~/.agents/skills/code-review (clone)
✓ Placed 'code-review' in ~/.cursor/skills/code-review (clone)
✓ Added 'code-review' v1.2.0
```

## Supported Agents

Five agents, done well:

| Agent | Global Path | Project Path |
|-------|------------|--------------|
| [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) | `~/.claude/skills/` | `.claude/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `~/.agents/skills/` | `.agents/skills/` |
| [pi](https://github.com/badlogic/pi) | `~/.agents/skills/` | `.agents/skills/` |
| [Codex](https://github.com/openai/codex) | `~/.agents/skills/` | `.agents/skills/` |
| [Cursor](https://www.cursor.com/) | `~/.cursor/skills/` | `.agents/skills/` |

Gemini CLI, pi, Codex, and Cursor all read from `.agents/skills/` at the project level — one placement serves all four. Only Claude Code needs its own `.claude/skills/` path.

## Commands

```bash
napoln add <source>           # Install a skill
napoln remove <name>          # Remove a skill
napoln upgrade [<name>]       # Upgrade one or all skills
napoln status                 # Show installed skills and modification state
napoln diff <name>            # Show local changes vs. upstream
napoln sync                   # Re-create missing placements from manifest
napoln doctor                 # Health check: store integrity, placements, provenance
napoln gc                     # Remove unreferenced store entries
napoln list <source>          # List skills in a repo without installing
```

Every mutating command supports `--dry-run`:

```bash
napoln upgrade --dry-run
# Dry run — no changes will be made
#   Would upgrade 'code-review' from v1.0.0 to v1.1.0
#   Would merge changes into ~/.claude/skills/code-review
# Run without --dry-run to apply.
```

## How It Works

### Content-Addressed Store

Every skill version is stored immutably at `~/.napoln/store/<name>/<version>-<hash>/`. The hash is a SHA-256 over all files, so identical content always produces the same entry. This store is the merge base for upgrades.

### Reflink Placement

Skills are placed into agent directories using [reflink](https://en.wikipedia.org/wiki/Copy-on-write#In_file_systems) (copy-on-write) on APFS and btrfs. This means placements cost zero extra disk space until you modify them. Falls back to regular copy on filesystems that don't support it.

### Three-Way Merge on Upgrade

When you customize a skill and then upgrade, napoln does a three-way merge — your changes, the original version, and the new upstream — just like `git merge`. Your customizations survive.

```
napoln upgrade code-review
# ✓ Merged 'code-review' at ~/.claude/skills/code-review (2 files updated)
```

If both you and upstream changed the same lines, you get standard conflict markers:

```markdown
<<<<<<< local (your changes)
2. Focus on security implications
=======
2. Use the OWASP checklist
>>>>>>> upstream (v1.3.0)
```

Resolve them, then run `napoln resolve code-review`.

### Manifest

`~/.napoln/manifest.toml` is the source of truth. It tracks every installed skill, its source, version, content hash, and where it's placed:

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
```

### Team Workflow

For projects, install with `--project` and commit the manifest:

```bash
napoln add owner/repo/skills/code-review --project
# Creates .napoln/manifest.toml (commit this)
# Places into .claude/skills/ and .agents/skills/ (gitignore these)

# Teammate clones and runs:
napoln install
# ✓ Synced 'code-review' to .claude/skills/code-review
```

### Self-Describing

napoln ships a bootstrap skill (`napoln-manage`) that teaches your agents how to use it. After installation, you can ask your agent *"install a skill for code review"* and it knows what to do — no docs lookup required.

## Design Principles

**Versioned, not copied.** Skills are tracked dependencies with semantic versioning and three-way merge. No symlink fragility. No copy drift. Inspired by [graft](https://github.com/raiderrobert/graft).

**Decentralized.** Any git repo is a valid source. No registry required to publish or install. Go modules model, not npm-central model.

**Content-addressed.** Every stored version has a deterministic hash. Same content → same hash. You always know exactly what you have. Nix model.

**Depth over breadth.** Five agents supported well beats forty supported poorly. Each target agent gets tested, validated integration.

**Transparent telemetry.** Opt-in only. `napoln telemetry show-data` shows exactly what would be sent. Nothing is collected by default.

## Install

Requires Python 3.11+. Install with [uv](https://docs.astral.sh/uv/):

```bash
# Run directly
uvx napoln add owner/repo

# Or install globally
uv tool install napoln
```

## Prior Art & Inspiration

| Project | What we learned |
|---------|----------------|
| [Vercel skills](https://github.com/vercel-labs/skills) | The problem space and the [Agent Skills standard](https://agentskills.io/specification) |
| [graft](https://github.com/raiderrobert/graft) | Versioned file-level dependency management with three-way merge |
| Go modules | Decentralized sourcing, minimal infrastructure |
| Nix | Content-addressed packages, reproducibility |
| npm / cargo / uv | Registry-based discovery, semantic versioning, lockfile patterns |
