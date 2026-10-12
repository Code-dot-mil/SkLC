"""Shared exception types for assessment commands."""

from pathlib import Path


class SkillValidationError(ValueError):
    """A skill package does not meet validation requirements."""


class InvalidSkillDirectoryError(SkillValidationError):
    """The selected path is not a skill directory."""


class MissingFrontmatterError(SkillValidationError):
    """SKILL.md does not start with frontmatter."""


class UnclosedFrontmatterError(SkillValidationError):
    """The frontmatter closing marker is missing."""


class MalformedFrontmatterError(SkillValidationError):
    """The frontmatter is not valid YAML."""


class NonMappingFrontmatterError(SkillValidationError):
    """The frontmatter is not a mapping."""


class InvalidSkillFrontmatterKeyError(SkillValidationError):
    """A required frontmatter key is missing or is not a nonempty string."""


class SkillNameMismatchError(SkillValidationError):
    """The name does not match the skill directory."""


class ScanError(RuntimeError):
    """Scanning failed; any available artifacts remain in report_dir."""

    def __init__(self, message: str, report_dir: Path):
        self.report_dir = report_dir
        super().__init__(f"{message}; artifacts: {report_dir}")


class IncompleteScanError(ScanError):
    """The requested analysis did not complete without degradation."""


class InvalidOutputDirectoryError(ValueError):
    """Reports must be stored outside the scanned skill."""
