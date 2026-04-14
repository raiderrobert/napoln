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
napoln add owner/repo --skill '*'
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
napoln add owner/repo/skills/code-review    # specific skill by path
napoln add owner/repo@v1.2.0                # pinned to a tag
napoln add ./my-local-skill                  # local directory
```

Customize a skill, then upgrade without losing your changes:

```bash
napoln upgrade code-review
# ✓ Merged 'code-review' at ~/.claude/skills/code-review (2 files updated)
```

## Commands

```
napoln add <source>           Install a skill
napoln remove <name>          Remove a skill
napoln upgrade [<name>]       Upgrade one or all skills
napoln status                 Show installed skills and modification state
napoln diff <name>            Show local changes vs. upstream
napoln sync                   Re-create missing placements from manifest
napoln doctor                 Health check
napoln gc                     Remove unreferenced store entries
napoln list <source>          List skills in a repo without installing
```

All mutating commands support `--dry-run`.

## Supported Agents

| Agent | Global Path | Project Path |
|-------|------------|--------------|
| [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) | `~/.claude/skills/` | `.claude/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `~/.agents/skills/` | `.agents/skills/` |
| [pi](https://github.com/badlogic/pi) | `~/.agents/skills/` | `.agents/skills/` |
| [Codex](https://github.com/openai/codex) | `~/.agents/skills/` | `.agents/skills/` |
| [Cursor](https://www.cursor.com/) | `~/.cursor/skills/` | `.agents/skills/` |

Gemini CLI, pi, Codex, and Cursor share `.agents/skills/` at the project level — one placement serves all four.

## Team Workflow

Install with `--project` and commit the manifest:

```bash
napoln add owner/repo/skills/code-review --project
# Creates .napoln/manifest.toml  (commit this)
# Places into .claude/skills/    (gitignore these)
```

Teammates clone and run:

```bash
napoln install
# ✓ Synced 'code-review' to .claude/skills/code-review
```

## Documentation

- [SPEC.md](SPEC.md) — Full specification: store, placement, merge, CLI, manifest schema
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture decisions and prior art analysis
- [STORIES.md](STORIES.md) — BDD user stories and detailed command output examples

## License

[MIT](LICENSE)
