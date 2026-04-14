"""SKILL.md validation per the Agent Skills standard.

Validation produces warnings (not errors) — a skill with warnings is still installed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class ValidationLevel(Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    level: ValidationLevel
    message: str


@dataclass
class ValidationResult:
    is_valid: bool
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)
    name: str | None = None
    description: str | None = None
    metadata: dict | None = None

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


# Name validation pattern: lowercase alphanumeric + hyphens
_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def _parse_frontmatter(content: str) -> dict | None:
    """Extract and parse YAML frontmatter from markdown content.

    Returns None if no valid frontmatter found.
    """
    content = content.strip()
    if not content.startswith("---"):
        return None

    # Find the closing ---
    end = content.find("---", 3)
    if end == -1:
        return None

    yaml_str = content[3:end].strip()
    if not yaml_str:
        return None

    try:
        parsed = yaml.safe_load(yaml_str)
        if not isinstance(parsed, dict):
            return None
        return parsed
    except yaml.YAMLError:
        return None


def _validate_name(name: str, dir_name: str) -> list[ValidationIssue]:
    """Validate the skill name field."""
    issues: list[ValidationIssue] = []

    if len(name) > 64:
        issues.append(ValidationIssue(ValidationLevel.WARNING, "name exceeds 64 characters"))

    if name != name.lower():
        issues.append(ValidationIssue(ValidationLevel.WARNING, "name must be lowercase"))

    if name.startswith("-"):
        issues.append(
            ValidationIssue(ValidationLevel.WARNING, "name must not start with hyphen")
        )

    if name.endswith("-"):
        issues.append(ValidationIssue(ValidationLevel.WARNING, "name must not end with hyphen"))

    if "--" in name:
        issues.append(ValidationIssue(ValidationLevel.WARNING, "consecutive hyphens in name"))

    # Check for invalid characters (allow lowercase, digits, single hyphens)
    name_lower = name.lower()
    if not re.match(r"^[a-z0-9-]+$", name_lower):
        issues.append(
            ValidationIssue(ValidationLevel.WARNING, "invalid characters in name")
        )

    if name != dir_name:
        issues.append(
            ValidationIssue(
                ValidationLevel.WARNING,
                f"name '{name}' does not match directory name '{dir_name}'",
            )
        )

    return issues


def validate_skill(skill_dir: Path) -> ValidationResult:
    """Validate a skill directory.

    Checks:
    1. SKILL.md exists
    2. Frontmatter parses as valid YAML
    3. `name` field is present and valid
    4. `description` field is present and non-empty
    5. `name` matches parent directory name

    Args:
        skill_dir: Path to the skill directory.

    Returns:
        ValidationResult with is_valid, warnings, and errors.
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    skill_md = skill_dir / "SKILL.md"

    # 1. SKILL.md must exist
    if not skill_md.exists():
        errors.append(ValidationIssue(ValidationLevel.ERROR, "SKILL.md not found"))
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    content = skill_md.read_text(encoding="utf-8")

    # 2. Frontmatter must parse
    frontmatter = _parse_frontmatter(content)
    if frontmatter is None:
        errors.append(
            ValidationIssue(ValidationLevel.ERROR, "No valid YAML frontmatter found in SKILL.md")
        )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # 3. name field
    name = frontmatter.get("name")
    if not name:
        errors.append(ValidationIssue(ValidationLevel.ERROR, "Missing required field: name"))
    else:
        name = str(name)
        name_warnings = _validate_name(name, skill_dir.name)
        warnings.extend(name_warnings)

    # 4. description field
    description = frontmatter.get("description")
    if not description:
        errors.append(
            ValidationIssue(ValidationLevel.ERROR, "Missing required field: description")
        )
    else:
        description = str(description)

    is_valid = len(errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        warnings=warnings,
        errors=errors,
        name=name if isinstance(name, str) else None,
        description=description if isinstance(description, str) else None,
        metadata=frontmatter.get("metadata"),
    )
