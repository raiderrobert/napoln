"""Interactive prompts for napoln."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillChoice:
    """A skill available for selection."""

    name: str
    description: str
    path: Path


def pick_skills(choices: list[SkillChoice]) -> list[SkillChoice]:
    """Interactive checkbox picker for skills.

    Returns the selected choices, or empty list if the user cancels.
    Falls back to selecting all if not running in a TTY.
    """
    if not sys.stdin.isatty():
        return choices

    import questionary

    options = []
    for c in choices:
        label = c.name
        if c.description:
            # Truncate long descriptions
            desc = c.description if len(c.description) <= 60 else c.description[:57] + "..."
            label = f"{c.name} ({desc})"
        options.append(questionary.Choice(title=label, value=c))

    selected = questionary.checkbox(
        "Select skills to install (space to toggle, enter to confirm):",
        choices=options,
    ).ask()

    if selected is None:
        # User pressed ctrl-c
        return []

    return selected
