"""Content-addressed hashing for skill directories.

Produces a deterministic SHA-256 hash over all files in a skill directory
(sorted by relative path, excluding .napoln provenance files).
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_skill(skill_dir: Path) -> str:
    """Hash a skill directory and return the first 7 hex chars of the SHA-256.

    The hash is computed over a deterministic concatenation:
        for each file (sorted by relative POSIX path, excluding .napoln):
            relative_path \\x00 file_contents \\x00

    Args:
        skill_dir: Path to the skill directory.

    Returns:
        7-character hex prefix of the SHA-256 hash.
    """
    hasher = hashlib.sha256()

    # Collect all files, excluding .napoln provenance
    files = sorted(
        p.relative_to(skill_dir)
        for p in skill_dir.rglob("*")
        if p.is_file() and p.name != ".napoln"
    )

    for rel_path in files:
        abs_path = skill_dir / rel_path
        # Encode path (POSIX-normalized, forward slashes)
        hasher.update(str(rel_path.as_posix()).encode("utf-8"))
        hasher.update(b"\x00")
        # Encode content
        hasher.update(abs_path.read_bytes())
        hasher.update(b"\x00")

    return hasher.hexdigest()[:7]


def hash_skill_full(skill_dir: Path) -> str:
    """Return the full SHA-256 hex digest for a skill directory."""
    hasher = hashlib.sha256()

    files = sorted(
        p.relative_to(skill_dir)
        for p in skill_dir.rglob("*")
        if p.is_file() and p.name != ".napoln"
    )

    for rel_path in files:
        abs_path = skill_dir / rel_path
        hasher.update(str(rel_path.as_posix()).encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(abs_path.read_bytes())
        hasher.update(b"\x00")

    return hasher.hexdigest()
