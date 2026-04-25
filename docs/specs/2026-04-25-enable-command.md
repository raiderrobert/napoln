# napoln enable Command

## Overview

Add a new `enable` command that extends already-installed skills to additional agents without re-downloading.

## Motivation

When adding a new agent support (e.g., Hermes), users need a way to enable existing skills for the new agent without re-installing. This provides better ergonomics than `napoln add` for this use case.

## Command Interface

```
napoln enable [agent] [--project] [--global]
```

### Without agent argument
1. Interactive picker: select which agent(s) to enable
2. Interactive picker: select which skills to enable for selected agent(s)
3. Apply placements

### With agent argument
1. Read skills from manifest (respects `--project`/`--global`)
2. Filter out skills already placed for that agent
3. If no skills need enabling: `✓ All skills already enabled for <agent>`
4. Interactive picker: select skills to enable
5. Place selected skills and update manifest

## Behavior

- Uses existing store entries (no re-download)
- Skips skills already placed for the target agent
- Supports `--project` flag for project-scoped operations
- Interactive picker via existing `pick_skills` infrastructure

## Implementation

New file: `src/napoln/commands/enable.py`
- `run_enable()` function
- Import existing `_install_single_skill` logic or create shared placement helper
- Integrate with CLI in `src/napoln/cli.py`

## Example

```
$ napoln enable hermes
Found 5 skills. Already enabled: 2. Select skills to enable for Hermes:

  [x] code-review     v1.2.0  owner/repo
  [ ] brainstorming   v0.1.0  other/repo
  [ ] citation        v2.0.0  another/repo

✓ Enabled 'code-review' for hermes → ~/.hermes/skills/code-review
```
