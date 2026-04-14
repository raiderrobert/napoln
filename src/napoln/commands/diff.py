"""napoln diff — Show local modifications vs. upstream."""

from __future__ import annotations

import difflib
from pathlib import Path

from napoln import output
from napoln.core import manifest
from napoln.core.store import get_stored_skill


def _get_napoln_home() -> Path:
    import os

    return Path(os.environ.get("NAPOLN_HOME", Path.home() / ".napoln"))


def run_diff(
    name: str,
    agent_id: str | None = None,
    scope: str = "global",
    project_root: Path | None = None,
) -> int:
    """Execute the diff command.

    Returns:
        Exit code (0=success, 1=error).
    """
    napoln_home = _get_napoln_home()
    manifest_path = manifest.get_manifest_path(napoln_home, scope, project_root)
    mf = manifest.read_manifest(manifest_path)

    if name not in mf.skills:
        output.error(f"Skill '{name}' is not installed.")
        return 1

    entry = mf.skills[name]
    store_path = get_stored_skill(name, entry.version, entry.store_hash, napoln_home)

    if store_path is None:
        output.error(
            f"Store entry not found for '{name}' v{entry.version}",
            fix="Run `napoln doctor` to check store integrity.",
        )
        return 1

    agents_to_diff = [agent_id] if agent_id else list(entry.agents.keys())
    has_diff = False

    for aid in agents_to_diff:
        if aid not in entry.agents:
            continue

        placement = entry.agents[aid]
        placement_path = Path(placement.path).expanduser()

        if not placement_path.exists():
            output.warning(f"Placement missing: {placement_path}")
            continue

        output.header(f"--- {aid}: {placement_path}")

        # Diff each file
        for store_file in sorted(store_path.rglob("*")):
            if store_file.is_file() and store_file.name != ".napoln":
                rel = store_file.relative_to(store_path)
                placement_file = placement_path / rel

                if not placement_file.exists():
                    output.warning(f"  Deleted: {rel}")
                    has_diff = True
                    continue

                store_content = store_file.read_text(encoding="utf-8", errors="replace")
                placement_content = placement_file.read_text(encoding="utf-8", errors="replace")

                if store_content != placement_content:
                    has_diff = True
                    diff = difflib.unified_diff(
                        store_content.splitlines(keepends=True),
                        placement_content.splitlines(keepends=True),
                        fromfile=f"upstream/{rel}",
                        tofile=f"local/{rel}",
                    )
                    for line in diff:
                        import typer

                        if line.startswith("+"):
                            typer.echo(typer.style(line.rstrip(), fg=typer.colors.GREEN))
                        elif line.startswith("-"):
                            typer.echo(typer.style(line.rstrip(), fg=typer.colors.RED))
                        else:
                            typer.echo(line.rstrip())

        # Check for new files in placement
        for placement_file in sorted(placement_path.rglob("*")):
            if placement_file.is_file() and placement_file.name != ".napoln":
                rel = placement_file.relative_to(placement_path)
                store_file = store_path / rel
                if not store_file.exists():
                    output.info(f"  Added: {rel}")
                    has_diff = True

    if not has_diff:
        output.info(f"'{name}' has no local modifications.")

    return 0
