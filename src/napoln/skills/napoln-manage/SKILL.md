---
name: napoln-manage
description: >
  Search for, install, upgrade, and manage agent skills using the napoln
  package manager. Use when the user wants to find new capabilities, install
  a skill from a git repository, check for skill updates, view local
  modifications to installed skills, or resolve merge conflicts after upgrade.
metadata:
  version: "0.1.0"
  author: napoln
---

# napoln — Skill Manager

napoln manages reusable skills for AI coding agents. When running commands
for the user, prefer `uvx napoln` over bare `napoln` to avoid PATH issues.

## Running Commands

napoln is installed as a Python tool and may not be in PATH when an agent
runs. Use `uvx` to invoke it without relying on PATH:

```bash
uvx napoln add owner/repo            # add (preferred — no PATH dependency)
uvx napoln list                     # list
uvx napoln upgrade                  # upgrade
uvx napoln remove <name>...       # remove (or --from-source)
uvx napoln install                  # sync from manifests
uvx napoln init my-skill            # scaffold a new skill
uvx napoln config doctor            # verify integrity
```

If `uvx` is unavailable, fall back to `python -m napoln` or `pipx run napoln`.

## Install a Skill

```bash
# From a git repository
uvx napoln add owner/repo                    # Interactive picker for multi-skill repos
uvx napoln add owner/repo --all              # Install all skills from a repo
uvx napoln add owner/repo --skill name       # Install a specific skill by name
uvx napoln add owner/repo@v1.2.0            # Pinned version

# From a local path
uvx napoln add ./path/to/skill
```

## Check What's Installed

```bash
uvx napoln list              # Show all installed skills and their placements
uvx napoln list -v           # Show full placement paths
uvx napoln list --json       # Machine-readable output
```

## Upgrade Skills

```bash
uvx napoln upgrade              # Upgrade all skills
uvx napoln upgrade <name>       # Upgrade specific skill
uvx napoln upgrade --dry-run    # Preview changes without applying
```

If upgrade produces merge conflicts (the user customized a skill and the
upstream also changed the same lines):
1. Conflicts appear as `<<<<<<<` / `=======` / `>>>>>>>` markers in SKILL.md
2. Edit the file to resolve — keep the best of both versions
3. Run `uvx napoln upgrade <name>` again to complete the upgrade

## Remove a Skill

Remove one or more skills:

```bash
uvx napoln remove design-audit design-frontend design-preflight
```

Remove all skills from a specific repository:

```bash
uvx napoln remove --from-source raiderrobert/flow
```

Combine explicit names with `--from-source` filter:

```bash
uvx napoln remove --from-source raiderrobert/flow design-audit
```

## Scaffold a New Skill

```bash
uvx napoln init my-skill      # Creates my-skill/SKILL.md
uvx napoln init               # Creates SKILL.md in current directory
```

## Restore / Sync

```bash
uvx napoln install            # Restore all placements from manifests
```

## Housekeeping

```bash
uvx napoln config             # View configuration and detected agents
uvx napoln config doctor      # Verify store integrity and placement validity
uvx napoln config gc          # Remove unreferenced store entries
```
