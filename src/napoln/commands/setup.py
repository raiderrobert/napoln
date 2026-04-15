"""napoln setup — One-time interactive onboarding to choose default agents."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import tomli_w

from napoln import output
from napoln.core import agents as agents_mod
from napoln.prompts import pick_agents


def _get_napoln_home() -> Path:
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def _ensure_initialized(napoln_home: Path) -> None:
    napoln_home.mkdir(parents=True, exist_ok=True)
    (napoln_home / "store").mkdir(exist_ok=True)
    (napoln_home / "cache").mkdir(exist_ok=True)


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _write_default_agents(config_path: Path, agent_ids: list[str]) -> None:
    data = _load_config(config_path)
    section = data.setdefault("napoln", {})
    section["default_agents"] = agent_ids
    section.setdefault("default_scope", "global")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(tomli_w.dumps(data), encoding="utf-8")


def run_setup(force: bool = False) -> int:
    """Run the interactive onboarding wizard.

    Detects available agents, prompts the user to pick defaults, and persists
    the selection to ``[napoln].default_agents`` in ``~/.napoln/config.toml``.

    Args:
        force: Re-run even if defaults are already configured.

    Returns:
        Exit code (0 on success, 1 on cancel/error).
    """
    napoln_home = _get_napoln_home()
    home = Path(os.environ.get("HOME", Path.home()))
    config_path = napoln_home / "config.toml"

    _ensure_initialized(napoln_home)

    existing = agents_mod.load_default_agent_ids(napoln_home)
    if existing and not force:
        names = ", ".join(agents_mod.AGENTS[aid].display_name for aid in existing)
        output.info(f"Default agents already configured: {names}")
        output.info("Re-run with --force to change them.")
        return 0

    detected = agents_mod.detect_agents(home)
    if not detected:
        output.error(
            "No agents detected on this machine.",
            fix=(
                "Install one of: Claude Code, Gemini CLI, pi, Codex, Cursor — "
                "then re-run `napoln setup`."
            ),
        )
        return 1

    output.header("napoln setup")
    output.info(f"Detected {len(detected)} agent(s) on this machine.")

    preselected = existing or [a.id for a in detected]
    selected = pick_agents(detected, preselected_ids=preselected)

    if selected is None:
        output.warning("Setup cancelled.")
        return 1

    if not selected:
        output.warning("No agents selected — defaults will not be saved.")
        return 1

    selected_ids = [a.id for a in selected]
    _write_default_agents(config_path, selected_ids)

    names = ", ".join(a.display_name for a in selected)
    output.success(f"Saved default agents: {names}")
    output.info(f"Wrote {config_path}")
    output.info("Future `napoln add` commands will install to these agents by default.")
    output.info("Override per-command with `--agents <id1,id2,...>`.")
    return 0
