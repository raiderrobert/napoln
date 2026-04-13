# Brainstorm Context

Resume this brainstorm by reading this file and the README.md.

## Problem Statement

Vercel Labs built a skills package manager (https://github.com/vercel-labs/skills, https://skills.sh/) that is low-effort:

1. **Installation is naive** — only copy or symlink, no versioned tracking. Copy drifts, symlinks break when sources move/version.
2. **No bootstrap skills** — doesn't dogfood its own format to teach agents how to use the tool.
3. **Discovery is CLI/website only** — should be agent-native. A bundled skill that queries the registry from inside your agent.
4. **Site ranking is shallow** — "All Time / Trending / Hot" sorted by install count. No quality signals, no reviews, no real categorization.
5. **Telemetry lacks transparency** — it exists but is buried in a FAQ, not prominently documented or opt-in.
6. **Breadth over depth** — supports 40+ agents but probably none of them well.

## What We're Building

`napoln` (Napoleon Dynamite reference — "he helps you get skills"). A quality-first skills package manager for terminal-based coding agents.

- **Target agents:** Claude Code, Gemini CLI, pi (https://github.com/badlogic/pi-mono)
- **Language:** Python
- **Distribution:** `uvx napoln`
- **Name on PyPI:** `napoln` (confirmed free)

## Key Design Decisions Made

### Installation Model
Graft-style (https://github.com/raiderrobert/graft) versioned file management:
- Tracked dependencies in a manifest
- Three-way merge on upgrade preserving local customizations
- NOT symlinks, NOT copies

### Distribution Model
Blend of three packaging philosophies:
- **Go modules** — decentralized, any git repo is a valid source, minimal infrastructure
- **Nix** — content-addressed, reproducible, bit-for-bit certainty of what you have
- **npm** — optional central registry for discovery (not required for install)

### Skill Format
Not yet decided. Options discussed:
- A) One canonical format translated per-agent at install time
- B) Agent-agnostic markdown that each agent reads from wherever the tool puts it
- C) Skills can include agent-specific variants with a shared core

Will shake out once we look at how different the three agents' instruction formats actually are.

### Bootstrap Skills
The tool ships skills that teach agents how to use it. Dogfoods its own format.

### Agent-Native Discovery
A bundled skill lets users search/browse the registry from inside their agent. No separate website or CLI subcommand needed.

### Telemetry
Telemetry is crucial but must be transparent, well-documented, and a first-class concern — not an afterthought buried in docs.

## What's Next

- Propose 2-3 architectural approaches with trade-offs
- Present detailed design
- Write spec doc
- Implementation plan

## Prior Art

- Vercel skills: https://github.com/vercel-labs/skills / https://skills.sh/
- graft: https://github.com/raiderrobert/graft
- Go modules, Nix, npm/cargo packaging models
