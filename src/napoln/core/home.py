"""Resolve the napoln home directory.

The home directory holds the store, cache, and global manifest.
Defaults to ~/.napoln/, overridable with NAPOLN_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_napoln_home() -> Path:
    """Return the configured napoln home directory."""
    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))
