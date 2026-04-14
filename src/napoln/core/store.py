"""Content-addressed store operations.

The store lives at ~/.napoln/store/ and holds immutable upstream snapshots
of skills, identified by {version}-{hash-prefix}/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from napoln.core.hasher import hash_skill
from napoln.errors import StoreError


def get_store_dir(napoln_home: Path) -> Path:
    """Return the store directory path, creating it if needed."""
    store = napoln_home / "store"
    store.mkdir(parents=True, exist_ok=True)
    return store


def store_skill(
    skill_dir: Path, skill_name: str, version: str, napoln_home: Path
) -> tuple[Path, str]:
    """Store a skill in the content-addressed store.

    Copies the skill directory into the store at:
        {napoln_home}/store/{skill_name}/{version}-{hash_prefix}/

    If the exact same version+hash already exists, this is a no-op.

    Args:
        skill_dir: Path to the skill directory to store.
        skill_name: Name of the skill.
        version: Version string.
        napoln_home: Path to the napoln home directory.

    Returns:
        Tuple of (store_path, hash_prefix).
    """
    store = get_store_dir(napoln_home)
    content_hash = hash_skill(skill_dir)
    version_dir_name = f"{version}-{content_hash}"
    store_path = store / skill_name / version_dir_name

    if store_path.exists():
        # Already stored — verify integrity
        existing_hash = hash_skill(store_path)
        if existing_hash != content_hash:
            raise StoreError(
                f"Store corruption detected for {skill_name}/{version_dir_name}",
                cause=f"Expected hash {content_hash}, got {existing_hash}",
                fix="Run `napoln doctor` to diagnose and repair.",
            )
        return store_path, content_hash

    # Create parent and copy to a temp dir first (pseudo-atomic)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = store_path.parent / f".{version_dir_name}.tmp"
    try:
        if temp_path.exists():
            shutil.rmtree(temp_path)
        shutil.copytree(str(skill_dir), str(temp_path))

        # Remove .napoln provenance if it was copied from a previous placement
        napoln_file = temp_path / ".napoln"
        if napoln_file.exists():
            napoln_file.unlink()

        # Atomic rename
        temp_path.rename(store_path)
    except Exception:
        if temp_path.exists():
            shutil.rmtree(temp_path)
        raise

    return store_path, content_hash


def get_stored_skill(
    skill_name: str, version: str, content_hash: str, napoln_home: Path
) -> Path | None:
    """Look up a stored skill by name, version, and hash.

    Returns:
        Path to the stored skill directory, or None if not found.
    """
    store = get_store_dir(napoln_home)
    store_path = store / skill_name / f"{version}-{content_hash}"
    if store_path.exists():
        return store_path
    return None


def list_stored_versions(skill_name: str, napoln_home: Path) -> list[tuple[str, str, Path]]:
    """List all stored versions of a skill.

    Returns:
        List of (version, hash_prefix, path) tuples.
    """
    store = get_store_dir(napoln_home)
    skill_store = store / skill_name
    if not skill_store.exists():
        return []

    versions = []
    for entry in sorted(skill_store.iterdir()):
        if entry.is_dir() and "-" in entry.name and not entry.name.startswith("."):
            parts = entry.name.rsplit("-", 1)
            if len(parts) == 2:
                versions.append((parts[0], parts[1], entry))
    return versions


def verify_store_entry(store_path: Path) -> bool:
    """Verify a store entry's integrity by re-hashing.

    Returns:
        True if the hash matches, False if corrupted.
    """
    dir_name = store_path.name
    if "-" not in dir_name:
        return False
    expected_hash = dir_name.rsplit("-", 1)[1]
    actual_hash = hash_skill(store_path)
    return actual_hash == expected_hash
