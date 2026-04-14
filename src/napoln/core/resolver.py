"""Source resolution — parse source identifiers and resolve skills.

Handles git repos, local paths, and (future) registry sources.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from napoln.errors import MultipleSkillsError, ResolverError


@dataclass
class ResolvedSource:
    """A resolved skill source."""

    source_type: str  # "local", "git", "registry"
    source_id: str  # Original source identifier
    skill_dir: Path  # Path to the skill directory (possibly in cache/temp)
    version: str  # Resolved version
    cleanup: bool = False  # Whether to clean up skill_dir after use
    skill_name: str = ""  # Resolved skill name (from SKILL.md or directory name)


# Git shorthand patterns
_GITHUB_SHORT = re.compile(r"^([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:/(.+?))?(?:@(.+))?$")
_GIT_URL = re.compile(r"^(?:https?://|git@)([^/]+)[/:](.+?)(?:\.git)?$")
_DOMAIN_PATH = re.compile(
    r"^([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:/(.+?))?(?:@(.+))?$"
)
_SEMVER_TAG = re.compile(r"^v?(\d+\.\d+\.\d+(?:-.+)?)$")


@dataclass
class ParsedSource:
    """Parsed source identifier."""

    source_type: str  # "local", "git", "registry"
    host: str  # e.g. "github.com"
    owner: str  # e.g. "owner"
    repo: str  # e.g. "repo"
    path: str  # subdirectory path within repo
    version: str  # tag, branch, commit, or ""
    original: str  # original input string
    local_path: Path | None = None  # for local sources


def parse_source(source: str) -> ParsedSource:
    """Parse a source identifier into its components.

    Handles:
        - Local paths: ./path, /absolute/path
        - GitHub shorthand: owner/repo, owner/repo@v1.0
        - Full domain: github.com/owner/repo/path@version
        - Git URLs: https://github.com/owner/repo.git
        - Registry names (future): my-skill, @owner/my-skill

    Args:
        source: Source identifier string.

    Returns:
        ParsedSource with parsed components.
    """
    # Local path
    if source.startswith(("./", "../", "/")):
        local_path = Path(source).resolve()
        return ParsedSource(
            source_type="local",
            host="",
            owner="",
            repo="",
            path="",
            version="",
            original=source,
            local_path=local_path,
        )

    # Check if it looks like a Windows path or just a directory name
    local_path = Path(source)
    if local_path.exists() and local_path.is_dir():
        return ParsedSource(
            source_type="local",
            host="",
            owner="",
            repo="",
            path="",
            version="",
            original=source,
            local_path=local_path.resolve(),
        )

    # Full domain form: github.com/owner/repo/path@version
    m = _DOMAIN_PATH.match(source)
    if m:
        host, owner, repo, path, version = m.groups()
        return ParsedSource(
            source_type="git",
            host=host,
            owner=owner,
            repo=repo,
            path=path or "",
            version=version or "",
            original=source,
        )

    # Git URL: https://github.com/owner/repo.git
    m = _GIT_URL.match(source)
    if m:
        host, path = m.groups()
        parts = path.split("/")
        owner = parts[0] if len(parts) > 0 else ""
        repo = parts[1] if len(parts) > 1 else ""
        return ParsedSource(
            source_type="git",
            host=host,
            owner=owner,
            repo=repo,
            path="",
            version="",
            original=source,
        )

    # GitHub shorthand: owner/repo, owner/repo/path, owner/repo@version
    m = _GITHUB_SHORT.match(source)
    if m:
        owner, repo, path, version = m.groups()
        return ParsedSource(
            source_type="git",
            host="github.com",
            owner=owner,
            repo=repo,
            path=path or "",
            version=version or "",
            original=source,
        )

    # Registry name (future)
    if re.match(r"^@?[a-z0-9-]+(/[a-z0-9-]+)?$", source):
        return ParsedSource(
            source_type="registry",
            host="",
            owner="",
            repo="",
            path="",
            version="",
            original=source,
        )

    raise ResolverError(
        f"Could not parse source: {source}",
        fix=(
            "Use one of these formats:\n"
            "  napoln add ./path/to/skill        (local)\n"
            "  napoln add owner/repo              (GitHub)\n"
            "  napoln add github.com/owner/repo   (full URL)"
        ),
    )


def resolve_local(parsed: ParsedSource) -> ResolvedSource:
    """Resolve a local source to a skill directory.

    Args:
        parsed: Parsed source identifier with local_path set.

    Returns:
        ResolvedSource pointing to the skill directory.
    """
    if parsed.local_path is None:
        raise ResolverError(f"No local path in source: {parsed.original}")

    skill_dir = parsed.local_path
    if not skill_dir.exists():
        raise ResolverError(
            f"Path does not exist: {skill_dir}",
            fix="Check the path and try again.",
        )

    if not skill_dir.is_dir():
        raise ResolverError(
            f"Not a directory: {skill_dir}",
            fix="Provide a path to a skill directory containing SKILL.md.",
        )

    # Determine version from metadata
    version = _extract_version(skill_dir)

    return ResolvedSource(
        source_type="local",
        source_id=str(skill_dir),
        skill_dir=skill_dir,
        version=version,
    )


def resolve_git(
    parsed: ParsedSource,
    cache_dir: Path,
    skill_filter: str | None = None,
) -> ResolvedSource | list[ResolvedSource]:
    """Resolve a git source by cloning the repo.

    Args:
        parsed: Parsed source with git details.
        cache_dir: Directory to use for cloning.
        skill_filter: If '*', return all skills. If a name, return that one.
                      If None, error on multi-skill repos.

    Returns:
        ResolvedSource or list of ResolvedSource for multi-skill repos.
    """
    if not shutil.which("git"):
        raise ResolverError(
            "git is not installed",
            fix="Install git and try again.",
        )

    repo_url = f"https://{parsed.host}/{parsed.owner}/{parsed.repo}.git"
    clone_dir = cache_dir / f"{parsed.owner}-{parsed.repo}"

    try:
        if clone_dir.exists():
            # Update existing clone
            subprocess.run(
                ["git", "fetch", "--all", "--tags"],
                cwd=str(clone_dir),
                capture_output=True,
                check=True,
            )
        else:
            # Fresh clone
            clone_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--quiet", repo_url, str(clone_dir)],
                capture_output=True,
                check=True,
            )
    except subprocess.CalledProcessError as e:
        raise ResolverError(
            f"Failed to clone {repo_url}",
            cause=e.stderr.decode("utf-8", errors="replace").strip(),
            fix="Check the URL and your network connection.",
        )

    # Checkout the right version
    ref = parsed.version or _resolve_latest_version(clone_dir)
    if ref:
        try:
            subprocess.run(
                ["git", "checkout", "--quiet", ref],
                cwd=str(clone_dir),
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise ResolverError(
                f"Could not checkout '{ref}' in {repo_url}",
                cause=e.stderr.decode("utf-8", errors="replace").strip(),
                fix=f"Check that the tag/branch/commit '{ref}' exists.",
            )

    source_id = f"{parsed.host}/{parsed.owner}/{parsed.repo}"

    # Handle multi-skill repos
    if skill_filter and not parsed.path:
        skill_dirs = _find_all_skills_in_repo(clone_dir)
        if skill_filter != "*":
            # Filter to a specific skill
            skill_dirs = [d for d in skill_dirs if d.name == skill_filter]
            if not skill_dirs:
                raise ResolverError(
                    f"Skill '{skill_filter}' not found in the repository",
                    fix="Use `napoln list <source>` to see available skills.",
                )

        results = []
        for sd in skill_dirs:
            version = _resolve_version(sd, ref, clone_dir)
            rel = sd.relative_to(clone_dir)
            sid = f"{source_id}/{rel}" if str(rel) != "." else source_id
            results.append(
                ResolvedSource(
                    source_type="git",
                    source_id=sid,
                    skill_dir=sd,
                    version=version,
                    cleanup=False,
                    skill_name=sd.name,
                )
            )
        if len(results) == 1:
            return results[0]
        return results

    # Single skill resolution
    skill_dir = _find_skill_in_repo(clone_dir, parsed.path)
    version = _resolve_version(skill_dir, ref, clone_dir)

    if parsed.path:
        source_id += f"/{parsed.path}"

    return ResolvedSource(
        source_type="git",
        source_id=source_id,
        skill_dir=skill_dir,
        version=version,
        cleanup=False,
        skill_name=skill_dir.name,
    )


def _get_head_short_hash(repo_dir: Path) -> str:
    """Get the short commit hash of HEAD."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def _resolve_version(skill_dir: Path, ref: str, repo_dir: Path) -> str:
    """Resolve a skill's version from metadata, git ref, or HEAD hash.

    Priority:
    1. metadata.version from SKILL.md frontmatter
    2. The git ref (tag/branch) if it looks like a semver
    3. The git ref as-is (branch name, commit)
    4. HEAD short commit hash (e.g. '0.1.0+a3f7c4d' if no semver, or just the hash)
    """
    # 1. Check SKILL.md metadata
    meta_version = _extract_version(skill_dir)
    if meta_version != "0.0.0":
        return meta_version

    # 2/3. Use the ref if one was resolved (tag or branch)
    if ref:
        v = ref
        if v.startswith("v") and _SEMVER_TAG.match(v):
            v = v[1:]
        return v

    # 4. Fall back to HEAD commit hash
    short_hash = _get_head_short_hash(repo_dir)
    if short_hash:
        return f"0.0.0+{short_hash}"

    return "0.0.0"


def _resolve_latest_version(repo_dir: Path) -> str:
    """Find the latest semver tag, or HEAD if no tags."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        tags = result.stdout.strip().split("\n")
        semver_tags = []
        for tag in tags:
            tag = tag.strip()
            if tag and _SEMVER_TAG.match(tag):
                semver_tags.append(tag)

        if semver_tags:
            # Sort by semver (simple string sort works for most cases)
            semver_tags.sort(key=_semver_sort_key, reverse=True)
            return semver_tags[0]
    except subprocess.CalledProcessError:
        pass

    return ""  # Use default branch HEAD


def _semver_sort_key(tag: str) -> tuple[int, ...]:
    """Create a sort key from a semver tag."""
    version = tag.lstrip("v").split("-")[0]
    parts = version.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0, 0, 0)


def _find_all_skills_in_repo(repo_dir: Path) -> list[Path]:
    """Find all skill directories in a repo (for --skill '*')."""
    results: list[Path] = []

    # Root-level skill
    if (repo_dir / "SKILL.md").exists():
        results.append(repo_dir)
        return results

    # Scan for SKILL.md files everywhere
    for skill_md in sorted(repo_dir.rglob("SKILL.md")):
        if ".git" not in skill_md.parts:
            results.append(skill_md.parent)

    return results


def _find_skill_in_repo(repo_dir: Path, subpath: str) -> Path:
    """Find a skill directory in a cloned repo.

    Checks:
    1. If subpath is specified, use repo_dir/subpath
    2. If repo root has SKILL.md, use root
    3. If repo has skills/ directory, look there
    4. Scan for any SKILL.md files
    """
    if subpath:
        skill_dir = repo_dir / subpath
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            return skill_dir
        raise ResolverError(
            f"No SKILL.md found at {subpath} in the repository",
            fix="Check the path within the repository.",
        )

    # Root-level skill
    if (repo_dir / "SKILL.md").exists():
        return repo_dir

    # Convention: skills/ directory
    skills_dir = repo_dir / "skills"
    if skills_dir.is_dir():
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
        if len(skill_dirs) == 1:
            return skill_dirs[0]
        if len(skill_dirs) > 1:
            raise MultipleSkillsError(repo_dir, skill_dirs)

    # Scan for any SKILL.md
    skill_files = list(repo_dir.rglob("SKILL.md"))
    # Filter out git internals
    skill_files = [f for f in skill_files if ".git" not in f.parts]
    if len(skill_files) == 1:
        return skill_files[0].parent
    if len(skill_files) > 1:
        raise MultipleSkillsError(repo_dir, [f.parent for f in skill_files])

    raise ResolverError(
        "No SKILL.md found in the repository",
        fix="Make sure the repository contains a valid skill with a SKILL.md file.",
    )


def _extract_version(skill_dir: Path) -> str:
    """Extract version from SKILL.md frontmatter metadata."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return "0.0.0"

    try:
        import yaml

        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return "0.0.0"
        end = content.find("---", 3)
        if end == -1:
            return "0.0.0"
        frontmatter = yaml.safe_load(content[3:end])
        if isinstance(frontmatter, dict):
            # Check metadata.version first, then version
            metadata = frontmatter.get("metadata", {})
            if isinstance(metadata, dict) and "version" in metadata:
                return str(metadata["version"])
            if "version" in frontmatter:
                return str(frontmatter["version"])
    except Exception:
        pass

    return "0.0.0"


def _extract_description(skill_dir: Path) -> str:
    """Extract description from SKILL.md frontmatter."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ""

    try:
        import yaml

        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return ""
        end = content.find("---", 3)
        if end == -1:
            return ""
        frontmatter = yaml.safe_load(content[3:end])
        if isinstance(frontmatter, dict):
            return str(frontmatter.get("description", ""))
    except Exception:
        pass

    return ""


def discover_skills_in_repo(repo_dir: Path) -> list[Path]:
    """Discover all skill directories in a repository.

    Returns:
        List of paths to directories containing SKILL.md.
    """
    skill_dirs = []

    # Root-level skill
    if (repo_dir / "SKILL.md").exists():
        skill_dirs.append(repo_dir)
        return skill_dirs

    # Scan for SKILL.md files
    for skill_md in sorted(repo_dir.rglob("SKILL.md")):
        if ".git" not in skill_md.parts:
            skill_dirs.append(skill_md.parent)

    return skill_dirs


def discover_skill_choices(repo_dir: Path) -> list[tuple[str, str, Path]]:
    """Discover skills with names and descriptions.

    Returns:
        List of (name, description, path) tuples.
    """
    results = []
    for skill_dir in discover_skills_in_repo(repo_dir):
        name = skill_dir.name
        desc = _extract_description(skill_dir)
        results.append((name, desc, skill_dir))
    return results
