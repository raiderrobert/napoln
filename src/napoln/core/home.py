"""Resolve the napoln home directory.

The home directory holds the store, cache, and global manifest.
Defaults to ~/.napoln/, overridable with NAPOLN_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path


NAPOLN_DIR = ".napoln"


def get_napoln_home() -> Path:
    """Return the configured napoln home directory."""
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / NAPOLN_DIR))


def ensure_napoln_dirs(napoln_home: Path) -> None:
    """Ensure napoln home directory structure exists (napoln_home/, store/, cache/)."""
    napoln_home.mkdir(parents=True, exist_ok=True)
    (napoln_home / "store").mkdir(exist_ok=True)
    (napoln_home / "cache").mkdir(exist_ok=True)
