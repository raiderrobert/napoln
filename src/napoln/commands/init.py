"""napoln init — Scaffold a new SKILL.md."""

from __future__ import annotations

from pathlib import Path

from napoln import output


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

    # Title-case the name for the heading
    title = name.replace("-", " ").replace("_", " ").title()

    skill_md.write_text(SKILL_TEMPLATE.format(name=name, title=title))
    output.success(f"Created {skill_md}")
    return 0
