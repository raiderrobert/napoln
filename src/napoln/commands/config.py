"""napoln config — View or edit configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from napoln import output


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_config_show() -> int:
    """Show current configuration."""
    napoln_home = _get_napoln_home()
    config_path = napoln_home / "config.toml"

    if not config_path.exists():
        output.info("No configuration file found.")
        return 0

    content = config_path.read_text(encoding="utf-8")
    import typer
    typer.echo(content)
    return 0


def run_config_set(key: str, value: str) -> int:
    """Set a configuration value.

    Keys use dot notation: e.g., "telemetry.enabled", "napoln.default_scope"
    """
    napoln_home = _get_napoln_home()
    config_path = napoln_home / "config.toml"

    if config_path.exists():
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    else:
        data = {}

    # Parse key
    parts = key.split(".")
    if len(parts) != 2:
        output.error(
            f"Invalid key: {key}",
            fix="Use dot notation, e.g.: napoln config set telemetry.enabled false",
        )
        return 1

    section, field = parts
    if section not in data:
        data[section] = {}

    # Parse value
    parsed_value: str | bool | int | list
    if value.lower() in ("true", "yes"):
        parsed_value = True
    elif value.lower() in ("false", "no"):
        parsed_value = False
    elif value.isdigit():
        parsed_value = int(value)
    elif "," in value:
        parsed_value = [v.strip() for v in value.split(",")]
    else:
        parsed_value = value

    data[section][field] = parsed_value

    napoln_home.mkdir(parents=True, exist_ok=True)
    config_path.write_text(tomli_w.dumps(data), encoding="utf-8")
    output.success(f"Set {key} = {parsed_value}")

    return 0
