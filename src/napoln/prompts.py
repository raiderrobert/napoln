"""Interactive prompts for napoln."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from napoln.core.agents import AgentConfig


@dataclass
class SkillChoice:
    """A skill available for selection."""

    name: str
    description: str
    path: Path
    installed: bool = False


def _short_description(desc: str, max_len: int = 60) -> str:
    """Extract a short summary from a potentially long description.

    Takes the first sentence (up to the first period followed by a space,
    or the first comma, or the whole string) and truncates to max_len.
    """
    if not desc:
        return ""

    # Strip common prefixes like "Use when..." that are trigger instructions
    text = desc.strip()
    for prefix in (
        "Use when ",
        "Use for ",
        "Use if ",
        "Use after ",
        "Use before ",
        "Use BEFORE ",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            # Capitalize the remainder
            text = text[0].upper() + text[1:] if text else text
            break

    # Take first sentence
    for sep in (". ", "; ", " — ", " Trigger", " Keywords"):
        idx = text.find(sep)
        if idx > 0:
            text = text[:idx]
            break

    if len(text) <= max_len:
        return text

    # Truncate at last word boundary
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        truncated = truncated[:last_space]
    return truncated + "..."


def pick_skills(choices: list[SkillChoice]) -> list[SkillChoice]:
    """Interactive checkbox picker for skills.

    Returns the selected choices, or empty list if the user cancels.
    Falls back to selecting all if not running in a TTY.
    """
    if not sys.stdin.isatty():
        return choices

    import questionary
    from questionary import constants as q_constants
    from questionary.prompts import common as q_common

    # Use ✓ and a blank cell as indicators. Some terminal fonts don't render
    # the default ○/● glyphs distinctly.
    q_constants.INDICATOR_SELECTED = "✓"
    q_constants.INDICATOR_UNSELECTED = " "
    q_common.INDICATOR_SELECTED = "✓"
    q_common.INDICATOR_UNSELECTED = " "

    max_name = max(len(c.name) for c in choices) if choices else 0

    options = []
    for c in choices:
        short = _short_description(c.description)
        # Use token list for title so questionary doesn't apply
        # class:selected/class:highlighted background to the entire line.
        # Only the name gets highlighted; the description stays neutral.
        tokens: list[tuple[str, str]] = [("class:text", f"{c.name:<{max_name}}")]
        if short:
            tokens.append(("class:text", f"  {short}"))
        # Already-installed skills are pre-checked. The ✓ carries the signal.
        options.append(questionary.Choice(title=tokens, value=c, checked=c.installed))

    # prompt_toolkit's built-in default applies "reverse" to class:selected,
    # which inverts the ✓ indicator. Explicitly cancel it.
    style = questionary.Style([("selected", "noreverse")])

    selected = questionary.checkbox(
        "Select skills to install:",
        choices=options,
        style=style,
    ).ask()

    if selected is None:
        # User pressed ctrl-c
        return []

    return selected


def pick_agents(
    available: list[AgentConfig],
    preselected_ids: list[str] | None = None,
) -> list[AgentConfig] | None:
    """Interactive checkbox picker for agents.

    Returns the selected agents, or None if the user cancelled (ctrl-c).
    Returns an empty list if the user confirmed with nothing selected.

    Falls back to selecting all available agents in non-TTY environments so
    automation does not hang.
    """
    if not available:
        return []

    if not sys.stdin.isatty():
        return list(available)

    import questionary
    from questionary import constants as q_constants
    from questionary.prompts import common as q_common

    q_constants.INDICATOR_SELECTED = "✓"
    q_constants.INDICATOR_UNSELECTED = " "
    q_common.INDICATOR_SELECTED = "✓"
    q_common.INDICATOR_UNSELECTED = " "

    preselected = set(preselected_ids or [])
    max_name = max(len(a.display_name) for a in available)

    options = []
    for agent in available:
        tokens: list[tuple[str, str]] = [
            ("class:text", f"{agent.display_name:<{max_name}}"),
            ("class:text", f"  ({agent.id})"),
        ]
        options.append(
            questionary.Choice(
                title=tokens,
                value=agent,
                checked=agent.id in preselected,
            )
        )

    style = questionary.Style([("selected", "noreverse")])

    selected = questionary.checkbox(
        "Select default agents (skills will install to these unless overridden):",
        choices=options,
        style=style,
    ).ask()

    return selected
