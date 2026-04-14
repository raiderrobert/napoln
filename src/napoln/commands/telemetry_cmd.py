"""napoln telemetry — Manage telemetry settings."""

from __future__ import annotations

from pathlib import Path

from napoln import output
from napoln.commands.config import run_config_set


def _get_napoln_home() -> Path:
    import os
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_telemetry_status() -> int:
    """Show telemetry status."""
    from napoln.telemetry import get_collector

    napoln_home = _get_napoln_home()
    collector = get_collector(napoln_home)

    if collector.enabled:
        output.info("Telemetry is enabled.")
    else:
        output.info("Telemetry is disabled.")

    return 0


def run_telemetry_enable() -> int:
    """Enable telemetry."""
    import uuid

    result = run_config_set("telemetry.enabled", "true")
    if result == 0:
        # Generate anonymous ID if not present
        import tomllib
        napoln_home = _get_napoln_home()
        config_path = napoln_home / "config.toml"
        if config_path.exists():
            data = tomllib.loads(config_path.read_text())
            if not data.get("telemetry", {}).get("anonymous_id"):
                run_config_set("telemetry.anonymous_id", str(uuid.uuid4()))
        output.success("Telemetry enabled.")
    return result


def run_telemetry_disable() -> int:
    """Disable telemetry."""
    result = run_config_set("telemetry.enabled", "false")
    if result == 0:
        output.success("Telemetry disabled.")
    return result


def run_telemetry_show_data() -> int:
    """Show what data would be sent."""
    from napoln.telemetry import get_collector, TelemetryEvent

    napoln_home = _get_napoln_home()
    collector = get_collector(napoln_home)

    # Create a sample event
    sample = TelemetryEvent(command="example")
    output.header("Telemetry data fields:")
    import dataclasses
    for field in dataclasses.fields(sample):
        value = getattr(sample, field.name)
        output.info(f"  {field.name}: {value!r}")

    output.dim("\nNote: Skill names, repo URLs, file contents, and user identity are never collected.")
    return 0
