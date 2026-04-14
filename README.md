# napoln

A quality-first skills package manager for terminal-based coding agents.

"Vote for me and all your wildest dreams will come true."

## What is this?

`napoln` manages reusable instruction sets ("skills") for AI coding agents. Think of it as a package manager purpose-built for agent capabilities — not a file copier with a leaderboard.

Install via [uv](https://docs.astral.sh/uv/):

```bash
uvx napoln add owner/repo/skill
```

## Target Agents

Starting with depth over breadth — 3 agents done well:

- **Claude Code** — Anthropic's CLI agent
- **Gemini CLI** — Google's CLI agent
- **pi** — Open-source, provider-agnostic coding agent

## Design Principles

### 1. Versioned File Management (not copy/symlink)

Inspired by [graft](https://github.com/raiderrobert/graft). Skills are tracked dependencies with:
- Semantic versioning
- Three-way merge on upgrade (preserves your local customizations)
- A manifest file that is the source of truth

No symlink fragility. No copy drift.

### 2. Smart Distribution Model

Blending ideas from:
- **Go modules** — decentralized, any git repo is a valid source
- **Nix** — content-addressed, reproducible, you know exactly what you have
- **npm** — optional central registry for discovery (not required for installation)

### 3. Bootstrap Skills (Dogfooding)

`napoln` ships with skills that teach agents how to use it. The tool describes itself to the agent, so users can discover and manage skills without leaving their preferred agent.

### 4. Agent-Native Discovery

No need to visit a website or run a separate CLI search. A bundled skill lets you ask your agent "what skills exist for writing better tests?" and get results inline.

### 5. Transparent Telemetry

Telemetry is important for understanding usage, but it must be:
- Clearly documented (not buried in a FAQ)
- Opt-in or prominently disclosed
- Honest about what's collected and why

### 6. Depth Over Breadth

3 agents supported well > 40 agents supported poorly. Each target agent gets first-class integration, tested and validated.

## Prior Art & Inspiration

| Project | What we take from it |
|---------|---------------------|
| [Vercel skills](https://github.com/vercel-labs/skills) | The problem space, but not the execution |
| [graft](https://github.com/raiderrobert/graft) | Versioned file-level dependency management with three-way merge |
| Go modules | Decentralized sourcing, minimal infrastructure |
| Nix | Content-addressed packages, reproducibility |
| npm/cargo | Registry-based discovery, semantic versioning |

## Status

Early design phase. This repo captures the current thinking.
