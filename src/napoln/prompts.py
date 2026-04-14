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

    # Override questionary's default ○/● indicators. Some terminal fonts
    # render them identically or not at all. ✓ and a blank cell avoid the
    # problem, keep alignment, and need no color styling.
    q_constants.INDICATOR_SELECTED = "✓"
    q_constants.INDICATOR_UNSELECTED = " "
    q_common.INDICATOR_SELECTED = "✓"
    q_common.INDICATOR_UNSELECTED = " "

    # questionary places `[SetCursorPosition]` between the `»` pointer and
    # the indicator, so the terminal's block cursor inverts the indicator
    # character on the highlighted row. Wrap `_get_choice_tokens` to move
    # the marker to the start of the row, where it lands on a blank cell.
    if not getattr(q_common.InquirerControl, "_napoln_cursor_patched", False):
        original = q_common.InquirerControl._get_choice_tokens

        def patched(self):
            tokens = original(self)
            # Drop the original marker and re-insert it right before the
            # trailing newline of the row it belonged to. The newline cell
            # is invisible, so the terminal's block cursor has nothing
            # visible to invert.
            result = []
            pending = False
            for tok in tokens:
                if tok[0] == "[SetCursorPosition]":
                    pending = True
                    continue
                if pending and "\n" in tok[1]:
                    result.append(("[SetCursorPosition]", ""))
                    pending = False
                result.append(tok)
            if pending:
                result.append(("[SetCursorPosition]", ""))
            return result

        q_common.InquirerControl._get_choice_tokens = patched
        q_common.InquirerControl._napoln_cursor_patched = True

    # Find longest name for alignment
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
        options.append(questionary.Choice(title=tokens, value=c, checked=False))

    style = questionary.Style(
        [
            ("selected", "noreverse"),
            ("highlighted", "noreverse bold"),
        ]
    )

    selected = questionary.checkbox(
        "Select skills to install:",
        choices=options,
        style=style,
    ).ask()

    if selected is None:
        # User pressed ctrl-c
        return []

    return selected
