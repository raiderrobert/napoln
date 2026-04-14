"""Telemetry collection for napoln.

All telemetry is opt-in. Events are batched and sent on command completion.
If the endpoint is unreachable, events are silently discarded.
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from napoln import __version__


@dataclass
class TelemetryEvent:
    """A single telemetry event."""

    command: str
    source_type: str = ""
    agent_count: int = 0
    link_mode: str = ""
    os: str = platform.system().lower()
    arch: str = platform.machine()
    napoln_version: str = __version__
    success: bool = True
    duration_ms: int = 0


class TelemetryCollector:
    """Collects and sends telemetry events."""

    ENDPOINT = "https://telemetry.napoln.dev/v1/events"

    def __init__(self, config_dir: Path):
        self._config_dir = config_dir
        self._events: list[TelemetryEvent] = []
        self._enabled: bool | None = None
        self._anonymous_id: str = ""
        self._start_time: float = 0

    @property
    def enabled(self) -> bool:
        if self._enabled is None:
            self._load_state()
        return self._enabled or False

    def _load_state(self) -> None:
        """Load telemetry state from config."""
        env_val = os.environ.get("NAPOLN_TELEMETRY", "").lower()
        if env_val in ("off", "false", "0", "no"):
            self._enabled = False
            return
        if env_val in ("on", "true", "1", "yes"):
            self._enabled = True
            return

        # Check config file
        config_file = self._config_dir / "config.toml"
        if config_file.exists():
            try:
                import tomllib

                data = tomllib.loads(config_file.read_text())
                self._enabled = data.get("telemetry", {}).get("enabled", False)
                self._anonymous_id = data.get("telemetry", {}).get("anonymous_id", "")
            except Exception:
                self._enabled = False
        else:
            self._enabled = False

    def start_command(self) -> None:
        """Mark the start of a command for duration tracking."""
        self._start_time = time.monotonic()

    def record(self, event: TelemetryEvent) -> None:
        """Record a telemetry event."""
        if not self.enabled:
            return
        if self._start_time:
            event.duration_ms = int((time.monotonic() - self._start_time) * 1000)
        self._events.append(event)

    def flush(self) -> None:
        """Send collected events. Silently discards on failure."""
        if not self.enabled or not self._events:
            return

        try:
            import httpx

            payload = {
                "anonymous_id": self._anonymous_id,
                "events": [asdict(e) for e in self._events],
            }
            httpx.post(self.ENDPOINT, json=payload, timeout=5.0)
        except Exception:
            pass  # Silently discard

        self._events.clear()

    def get_data(self) -> list[dict]:
        """Return the data that would be sent (for `telemetry show-data`)."""
        return [asdict(e) for e in self._events]


# Module-level singleton
_collector: TelemetryCollector | None = None


def get_collector(config_dir: Path | None = None) -> TelemetryCollector:
    """Get or create the telemetry collector."""
    global _collector
    if _collector is None:
        if config_dir is None:
            config_dir = Path.home() / ".napoln"
        _collector = TelemetryCollector(config_dir)
    return _collector
