"""Reflink/copy placement with fallback.

Primary: reflink (copy-on-write) via the `reflink` package.
Fallback: full copy via shutil.copy2 if reflink is unavailable.
"""

from __future__ import annotations

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

    All files from store_path are cloned/copied to target_dir.
    The link mode is determined by the first file and used consistently.

    Args:
        store_path: Path to the skill in the content-addressed store.
        target_dir: Path to the target agent skill directory.

    Returns:
        "clone" or "copy" depending on the link mode used.
    """
    if target_dir.exists():
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    link_mode: str | None = None

    for src_file in sorted(store_path.rglob("*")):
        if src_file.is_file():
            rel = src_file.relative_to(store_path)
            dst_file = target_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            mode = clone_file(src_file, dst_file)
            if link_mode is None:
                link_mode = mode
                # If first file failed reflink, don't try again
                if mode == "copy":
                    _use_copy_only(store_path, target_dir, rel)
                    return "copy"

    return link_mode or "copy"


def _use_copy_only(store_path: Path, target_dir: Path, already_copied: Path) -> None:
    """Copy remaining files after reflink fallback was triggered."""
    for src_file in sorted(store_path.rglob("*")):
        if src_file.is_file():
            rel = src_file.relative_to(store_path)
            if rel == already_copied:
                continue
            dst_file = target_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dst_file))
