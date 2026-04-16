# napoln

A package manager for [agent skills](https://agentskills.io/specification). Install from any git repo, upgrade without losing your customizations, and manage skills across every agent you use.

## Install

Requires Python 3.11+.

Run without installing:

```bash
uvx napoln add owner/repo
```

Or install globally:

```bash
uv tool install napoln    # recommended
pipx install napoln       # alternative
pip install napoln        # plain pip
```

## Features

- **Multi-agent.** One command places skills into Claude Code, Gemini CLI, pi, Codex, and Cursor.
- **Versioned upgrades.** Three-way merge on upgrade preserves your local customizations.
- **Decentralized.** Any git repo is a valid source. No registry required.
- **Content-addressed.** Every stored version has a deterministic SHA-256 hash.
- **Zero-copy placement.** Reflink (copy-on-write) on APFS and btrfs. Full copy fallback elsewhere.
- **Self-describing.** A bundled skill teaches your agents how to use napoln.

![napoln demo](napoln-demo.gif)

## Add

Install skills from a git repository:

```bash
napoln add owner/repo                    # Interactive picker for multi-skill repos
napoln add owner/repo --all              # Install all skills from a repo
napoln add owner/repo --skill name       # Install a specific skill by name
napoln add owner/repo@v1.2.0            # Pinned version
```

Or from a local path:

```bash
napoln add ./path/to/skill
```

## List

```bash
napoln list              # Show all installed skills and their placements
napoln list -v           # Show full placement paths
napoln list --json       # Machine-readable output
```

## Upgrade

```bash
napoln upgrade              # Upgrade all skills
napoln upgrade <name>       # Upgrade specific skill
napoln upgrade --dry-run    # Preview changes without applying
```

If upgrade produces merge conflicts (customized a skill and upstream also changed the same lines), conflicts appear as `<<<<<<<` / `=======` / `>>>>>>>` markers. Edit to resolve, then run `upgrade` again.

## Remove

```bash
napoln remove <name>
```

## Other Commands

```bash
napoln init my-skill      # Scaffold a new SKILL.md
napoln install            # Restore all placements from manifests
napoln config             # View configuration and detected agents
napoln config doctor      # Verify store integrity
napoln config gc          # Remove unreferenced store entries
```

All mutating commands support `--dry-run`. Use `-p` for project scope.

## Supported Agents

| Agent | Global Path | Project Path |
|-------|------------|--------------|
| [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) | `~/.claude/skills/` | `.claude/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `~/.agents/skills/` | `.agents/skills/` |
| [pi](https://github.com/badlogic/pi) | `~/.agents/skills/` | `.agents/skills/` |
| [Codex](https://github.com/openai/codex) | `~/.agents/skills/` | `.agents/skills/` |
| [Cursor](https://www.cursor.com/) | `~/.cursor/skills/` | `.agents/skills/` |

Gemini CLI, pi, and Codex share `~/.agents/skills/` — one placement serves all three.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and how to add commands or agents.

## License

[MIT](LICENSE)
