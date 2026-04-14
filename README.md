# napoln

A package manager for [agent skills](https://agentskills.io/specification). Install from any git repo, upgrade without losing your customizations, and manage skills across every agent you use.

> *"I don't even have any good skills. You know, like nunchuck skills, bow hunting skills, computer hacking skills."*

- **Multi-agent.** One command places skills into Claude Code, Gemini CLI, pi, Codex, and Cursor.
- **Versioned upgrades.** Three-way merge on upgrade preserves your local customizations.
- **Decentralized.** Any git repo is a valid source. No registry required.
- **Content-addressed.** Every stored version has a deterministic SHA-256 hash.
- **Zero-copy placement.** Reflink (copy-on-write) on APFS and btrfs. Full copy fallback elsewhere.
- **Self-describing.** A bundled skill teaches your agents how to use napoln.

## Install

Requires Python 3.11+.

```bash
uvx napoln add owner/repo
```

Or install globally:

```bash
uv tool install napoln
```

## Quick Start

```bash
napoln add owner/repo --all
```

napoln clones the repo, discovers all skills, and places them in every detected agent's skill directory:

```
✓ Placed 'code-review' in ~/.claude/skills/code-review (clone)
✓ Placed 'code-review' in ~/.agents/skills/code-review (clone)
✓ Placed 'code-review' in ~/.cursor/skills/code-review (clone)
✓ Added 'code-review' v1.2.0
```

Install a specific skill, pin a version, or use a local path:

```bash
napoln add owner/repo --skill code-review   # specific skill by name
napoln add owner/repo@v1.2.0               # pinned to a tag
napoln add ./my-local-skill                 # local directory
```

Multi-skill repos show an interactive picker when no `--skill` or `--all` flag is given:

```bash
napoln add owner/repo
# ? Select skills to install:
# ❯ ◉ code-review — Review pull requests for quality and correctness
#   ◉ testing — Generate and improve test coverage
#   ◯ rust — Rust-specific development patterns
```

Customize a skill, then upgrade without losing your changes:

```bash
napoln upgrade code-review
# ✓ Merged 'code-review' at ~/.claude/skills/code-review (2 files updated)
```

## Commands

```
napoln add <source>           Install skills from a git repo or local path
napoln remove <name>          Remove an installed skill
napoln upgrade [<name>]       Upgrade one or all skills
napoln list                   Show installed skills and where they are placed
napoln install                Restore skill placements from manifests
napoln init [<name>]          Scaffold a new SKILL.md
napoln config                 View configuration and run housekeeping
```

All mutating commands support `--dry-run`. Use `-p` for project scope on any command.

## Supported Agents

| Agent | Global Path | Project Path |
|-------|------------|--------------|
| [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) | `~/.claude/skills/` | `.claude/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `~/.agents/skills/` | `.agents/skills/` |
| [pi](https://github.com/badlogic/pi) | `~/.agents/skills/` | `.agents/skills/` |
| [Codex](https://github.com/openai/codex) | `~/.agents/skills/` | `.agents/skills/` |
| [Cursor](https://www.cursor.com/) | `~/.cursor/skills/` | `.agents/skills/` |

Gemini CLI, pi, and Codex share `~/.agents/skills/` — one placement serves all three.

## Team Workflow

Install with `--project` and commit the manifest:

```bash
napoln add owner/repo --skill code-review --project
# Creates .napoln/manifest.toml  (commit this)
# Places into .claude/skills/    (gitignore these)
```

Teammates clone and run:

```bash
napoln install
# ✓ Synced 3 project skills (3 restored)
```

`napoln install` syncs both global and project manifests automatically.

## Documentation

- [SPEC.md](SPEC.md) — Full specification: store, placement, merge, CLI, manifest schema
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture decisions and prior art analysis
- [CONTRIBUTING.md](CONTRIBUTING.md) — Development setup, testing, how to add commands and agents

## License

[MIT](LICENSE)
