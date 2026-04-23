"""Three-way merge for skill upgrades.

Uses `git merge-file` when available, falls back to Python's difflib.
Merges per-file: SKILL.md gets full three-way merge, other files use
replace-if-unchanged semantics.
"""

from __future__ import annotations

import difflib
import shutil
import subprocess
import tempfile
from pathlib import Path


def has_git() -> bool:
    """Check if git is available."""
    return shutil.which("git") is not None


def merge_file(ours: Path, base: Path, theirs: Path) -> tuple[str, bool]:
    """Three-way merge a single file.

    Args:
        ours: Path to the user's current version.
        base: Path to the pristine version from when the skill was installed.
        theirs: Path to the new upstream version.

    Returns:
        Tuple of (merged_content, has_conflicts).
    """
    if has_git():
        return _git_merge_file(ours, base, theirs)
    return _python_merge_file(ours, base, theirs)


def _git_merge_file(ours: Path, base: Path, theirs: Path) -> tuple[str, bool]:
    """Merge using git merge-file."""
    # git merge-file modifies the first file in-place, so use temp copies
    with tempfile.TemporaryDirectory() as tmp:
        tmp_ours = Path(tmp) / "ours"
        tmp_base = Path(tmp) / "base"
        tmp_theirs = Path(tmp) / "theirs"

        shutil.copy2(str(ours), str(tmp_ours))
        shutil.copy2(str(base), str(tmp_base))
        shutil.copy2(str(theirs), str(tmp_theirs))

        result = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                "--marker-size=7",
                "-L",
                "local (your changes)",
                "-L",
                "base",
                "-L",
                "upstream",
                str(tmp_ours),
                str(tmp_base),
                str(tmp_theirs),
            ],
            capture_output=True,
            text=True,
        )

        # git merge-file returns 0 for clean merge, >0 for conflicts
        merged = result.stdout
        has_conflicts = result.returncode > 0

        return merged, has_conflicts


def _python_merge_file(ours: Path, base: Path, theirs: Path) -> tuple[str, bool]:
    """Fallback merge using Python difflib.

    Simple approach: if only one side changed, use that side.
    If both sides changed, insert conflict markers.
    """
    ours_content = ours.read_text(encoding="utf-8")
    base_content = base.read_text(encoding="utf-8")
    theirs_content = theirs.read_text(encoding="utf-8")

    ours_changed = ours_content != base_content
    theirs_changed = theirs_content != base_content

    if not ours_changed and not theirs_changed:
        # No changes
        return base_content, False
    elif not ours_changed:
        # Only upstream changed — fast forward
        return theirs_content, False
    elif not theirs_changed:
        # Only local changed — keep ours
        return ours_content, False
    else:
        # Both changed — try line-by-line merge
        return _line_merge(ours_content, base_content, theirs_content)


def _line_merge(ours: str, base: str, theirs: str) -> tuple[str, bool]:
    """Hunk-based three-way line merge.

    Disjoint changes on ours and theirs are applied together without conflicts.
    Overlapping changes produce conflict markers scoped to the conflicting
    region instead of the whole file.
    """
    ours_lines = ours.splitlines(keepends=True)
    base_lines = base.splitlines(keepends=True)
    theirs_lines = theirs.splitlines(keepends=True)

    if ours_lines == theirs_lines:
        return "".join(ours_lines), False

    ours_hunks = _diff_hunks(base_lines, ours_lines)
    theirs_hunks = _diff_hunks(base_lines, theirs_lines)

    tagged = [(i1, i2, new, "ours") for (i1, i2, new) in ours_hunks] + [
        (i1, i2, new, "theirs") for (i1, i2, new) in theirs_hunks
    ]
    tagged.sort(key=lambda h: (h[0], h[1]))

    groups: list[list[tuple[int, int, list[str], str]]] = []
    for hunk in tagged:
        if groups and hunk[0] <= max(h[1] for h in groups[-1]):
            groups[-1].append(hunk)
        else:
            groups.append([hunk])

    merged: list[str] = []
    base_idx = 0
    has_conflicts = False

    for group in groups:
        g_start = min(h[0] for h in group)
        g_end = max(h[1] for h in group)
        merged.extend(base_lines[base_idx:g_start])

        sides = {h[3] for h in group}
        if sides == {"ours"} or sides == {"theirs"}:
            merged.extend(_apply_hunks(base_lines, group, g_start, g_end))
        else:
            ours_region = _apply_hunks(
                base_lines, [h for h in group if h[3] == "ours"], g_start, g_end
            )
            theirs_region = _apply_hunks(
                base_lines, [h for h in group if h[3] == "theirs"], g_start, g_end
            )
            if ours_region == theirs_region:
                merged.extend(ours_region)
            else:
                merged.append("<<<<<<< local (your changes)\n")
                merged.extend(ours_region)
                merged.append("=======\n")
                merged.extend(theirs_region)
                merged.append(">>>>>>> upstream\n")
                has_conflicts = True

        base_idx = g_end

    merged.extend(base_lines[base_idx:])
    return "".join(merged), has_conflicts


def _diff_hunks(base: list[str], other: list[str]) -> list[tuple[int, int, list[str]]]:
    """Return the non-equal opcodes as (base_start, base_end, replacement_lines)."""
    matcher = difflib.SequenceMatcher(a=base, b=other, autojunk=False)
    hunks: list[tuple[int, int, list[str]]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        hunks.append((i1, i2, other[j1:j2]))
    return hunks


def _apply_hunks(
    base: list[str],
    hunks: list[tuple[int, int, list[str], str]],
    start: int,
    end: int,
) -> list[str]:
    """Apply a set of non-overlapping hunks to base[start:end]."""
    result: list[str] = []
    idx = start
    for i1, i2, new_lines, _side in sorted(hunks, key=lambda h: h[0]):
        if i1 > idx:
            result.extend(base[idx:i1])
        result.extend(new_lines)
        idx = i2
    if idx < end:
        result.extend(base[idx:end])
    return result


def merge_skill(
    working_copy: Path,
    store_base: Path,
    store_new: Path,
) -> tuple[list[str], list[str]]:
    """Merge an entire skill directory (three-way).

    Args:
        working_copy: The user's current working copy.
        store_base: The pristine version from when the skill was installed.
        store_new: The new upstream version.

    Returns:
        Tuple of (updated_files, conflicted_files).
    """
    updated_files: list[str] = []
    conflicted_files: list[str] = []

    # Get all files across all three versions
    all_files: set[str] = set()
    for d in [working_copy, store_base, store_new]:
        if d.exists():
            for f in d.rglob("*"):
                if f.is_file() and f.name != ".napoln":
                    all_files.add(str(f.relative_to(d)))

    for rel_path in sorted(all_files):
        ours = working_copy / rel_path
        base = store_base / rel_path
        theirs = store_new / rel_path

        ours_exists = ours.exists()
        base_exists = base.exists()
        theirs_exists = theirs.exists()

        if not base_exists and not theirs_exists:
            # File only in working copy — user-created, leave it
            continue

        if not base_exists and theirs_exists:
            # New file in upstream — add it
            ours.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(theirs), str(ours))
            updated_files.append(rel_path)
            continue

        if base_exists and not theirs_exists:
            # File deleted in upstream
            if ours_exists:
                ours_content = ours.read_bytes()
                base_content = base.read_bytes()
                if ours_content == base_content:
                    # Unmodified — safe to delete
                    ours.unlink()
                    updated_files.append(rel_path)
                # else: modified locally, keep it + warn (handled by caller)
            continue

        if not ours_exists:
            # File deleted locally but still in upstream — re-add from upstream
            ours.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(theirs), str(ours))
            updated_files.append(rel_path)
            continue

        # Both base and theirs exist, and ours exists
        ours_content = ours.read_bytes()
        base_content = base.read_bytes()
        theirs_content = theirs.read_bytes()

        ours_changed = ours_content != base_content
        theirs_changed = theirs_content != base_content

        if not ours_changed and not theirs_changed:
            # No changes anywhere
            continue

        if not ours_changed:
            # Fast-forward: replace with upstream
            shutil.copy2(str(theirs), str(ours))
            updated_files.append(rel_path)
            continue

        if not theirs_changed:
            # Local changes only, upstream unchanged — no-op
            continue

        # Both changed — need to merge
        if rel_path == "SKILL.md" or rel_path.endswith(".md"):
            # Three-way merge for markdown files
            merged, has_conflicts = merge_file(ours, base, theirs)
            ours.write_text(merged, encoding="utf-8")
            updated_files.append(rel_path)
            if has_conflicts:
                conflicted_files.append(rel_path)
        else:
            # Binary/script files: keep local + warn
            conflicted_files.append(rel_path)

    return updated_files, conflicted_files


def has_conflict_markers(file_path: Path) -> bool:
    """Check if a file contains git-style conflict markers."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return "<<<<<<< " in content and "=======" in content and ">>>>>>> " in content
    except Exception:
        return False
