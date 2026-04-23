"""napoln init — Scaffold a new SKILL.md."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.core import agents as agents_mod


SKILL_TEMPLATE = """\
---
name: {name}
description: ""
---

# {title}

Describe what this skill does and when to use it.

## Instructions

1. Step one
2. Step two
"""

_GITIGNORE_HEADER = "# napoln skill placements"


def run_init(name: str | None = None) -> int:
    """Execute the init command.

    Args:
        name: Skill name. If given, creates {name}/SKILL.md.
              If omitted, creates ./SKILL.md using current dir name.

    Returns:
        Exit code (0=created, 1=already exists).
    """
    if name:
        target_dir = Path.cwd() / name
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_md = target_dir / "SKILL.md"
    else:
        name = Path.cwd().name
        skill_md = Path.cwd() / "SKILL.md"

    if skill_md.exists():
        output.error(f"SKILL.md already exists at {skill_md}")
        return 1

    title = name.replace("-", " ").replace("_", " ").title()

    skill_md.write_text(SKILL_TEMPLATE.format(name=name, title=title))
    output.success(f"Created {skill_md}")

    _update_gitignore(Path.cwd())

    return 0


def _find_git_root(start: Path) -> Path | None:
    """Walk up from ``start`` looking for a directory containing ``.git``."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _placement_gitignore_entries() -> list[str]:
    """Return unique placement directories (with trailing slash) for every agent.

    Covers both project-scope and global-scope directories so users who
    accidentally create either inside a repo do not commit placements.
    """
    seen: list[str] = []
    for agent in agents_mod.AGENTS.values():
        for raw in (agent.project_skill_dir, agent.global_skill_dir):
            entry = f"{raw.rstrip('/')}/"
            if entry not in seen:
                seen.append(entry)
    return seen


def _update_gitignore(cwd: Path) -> None:
    """Append missing placement-directory entries to the repo's .gitignore."""
    git_root = _find_git_root(cwd)
    if git_root is None:
        return

    gitignore = git_root / ".gitignore"
    entries = _placement_gitignore_entries()

    if gitignore.exists():
        existing_text = gitignore.read_text(encoding="utf-8")
        existing_lines = {line.strip() for line in existing_text.splitlines()}
    else:
        existing_text = ""
        existing_lines = set()

    missing = [e for e in entries if e not in existing_lines]
    if not missing:
        output.info(f"{gitignore} already lists skill placement directories.")
        return

    prefix = ""
    if existing_text and not existing_text.endswith("\n"):
        prefix = "\n"
    block = prefix + f"\n{_GITIGNORE_HEADER}\n" + "\n".join(missing) + "\n"

    with gitignore.open("a", encoding="utf-8") as fh:
        fh.write(block)

    output.success(
        f"Updated {gitignore} with {len(missing)} skill placement "
        f"{'entry' if len(missing) == 1 else 'entries'}: {', '.join(missing)}"
    )
