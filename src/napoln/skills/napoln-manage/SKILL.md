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
