"""Reflink/copy placement with fallback.

Primary: reflink (copy-on-write) via the `reflink` package.
Fallback: full copy via shutil.copy2 if reflink is unavailable.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _reflink_copy(src: Path, dst: Path) -> None:
    """Attempt a reflink (copy-on-write) clone of a single file."""
    try:
        import reflink as reflink_mod
    except ImportError:
        raise OSError("reflink not available")

    try:
        from reflink.error import ReflinkImpossibleError

        _reflink_errors = (OSError, NotImplementedError, ReflinkImpossibleError)
    except ImportError:
        _reflink_errors = (OSError, NotImplementedError)

    try:
        reflink_mod.reflink(str(src), str(dst))
    except _reflink_errors:
        raise OSError("reflink not supported")


def clone_file(src: Path, dst: Path) -> str:
    """Clone a file using reflink with copy fallback.

    Args:
        src: Source file path.
        dst: Destination file path.

    Returns:
        "clone" if reflink succeeded, "copy" if fallback was used.
    """
    try:
        _reflink_copy(src, dst)
        return "clone"
    except OSError:
        shutil.copy2(str(src), str(dst))
        return "copy"


def place_skill(store_path: Path, target_dir: Path) -> str:
    """Place a skill from the store to a target directory.

    Files are staged into a sibling temp directory, then atomically renamed
    into place. If staging fails, the existing target_dir is left untouched.

    Args:
        store_path: Path to the skill in the content-addressed store.
        target_dir: Path to the target agent skill directory.

    Returns:
        "clone" or "copy" depending on the link mode used.
    """
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = target_dir.parent / f".{target_dir.name}.tmp-placement"
    old_dir = target_dir.parent / f".{target_dir.name}.old-{os.getpid()}"

    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    if old_dir.exists():
        shutil.rmtree(old_dir)

    try:
        temp_dir.mkdir()
        link_mode = _populate(store_path, temp_dir)

        if target_dir.exists():
            os.rename(target_dir, old_dir)
            try:
                os.rename(temp_dir, target_dir)
            except OSError:
                # Swap failed — put the original back before re-raising.
                os.rename(old_dir, target_dir)
                raise
            shutil.rmtree(old_dir)
        else:
            os.rename(temp_dir, target_dir)
    except BaseException:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return link_mode


def _populate(store_path: Path, target_dir: Path) -> str:
    """Copy every file from store_path into target_dir, preferring reflink."""
    link_mode: str | None = None

    for src_file in sorted(store_path.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(store_path)
        dst_file = target_dir / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        if link_mode == "copy":
            shutil.copy2(str(src_file), str(dst_file))
            continue

        mode = clone_file(src_file, dst_file)
        if link_mode is None:
            link_mode = mode

    return link_mode or "copy"


def write_provenance(
    target_dir: Path,
    source: str,
    version: str,
    store_hash: str,
    link_mode: str,
) -> None:
    """Write the .napoln provenance file to a placement."""
    from datetime import datetime, timezone

    from napoln import __version__

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    provenance = (
        f'source = "{source}"\n'
        f'version = "{version}"\n'
        f'store_hash = "{store_hash}"\n'
        f'link_mode = "{link_mode}"\n'
        f'installed = "{now}"\n'
        f'napoln_version = "{__version__}"\n'
    )
    (target_dir / ".napoln").write_text(provenance)


def restore_placement(
    store_path: Path,
    placement_path: Path,
    source: str,
    version: str,
    store_hash: str,
) -> str | None:
    """Place a skill from the store if the placement doesn't already exist.

    Returns the link mode ("clone" or "copy") if placed, or None if already present.
    """
    if placement_path.exists():
        return None

    link_mode = place_skill(store_path, placement_path)
    write_provenance(placement_path, source, version, store_hash, link_mode)
    return link_mode
