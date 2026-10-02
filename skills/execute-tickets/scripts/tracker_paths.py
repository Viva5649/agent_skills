"""Resolve repository-relative directories supplied by the tracker-reading caller."""

from pathlib import Path


def resolve_directory(root: Path, value: str | None, default: str, option: str) -> Path:
    if value is None:
        tracker = root / "docs/agents/issue-tracker.md"
        if tracker.exists() or tracker.is_symlink():
            raise ValueError(f"{option} is required when docs/agents/issue-tracker.md is present")
        value = default
    requested = Path(value)
    directory = (root / requested).resolve()
    if (
        not value
        or requested.is_absolute()
        or ".." in requested.parts
        or not directory.is_relative_to(root)
    ):
        raise ValueError(f"{option} must be a repository-relative directory inside the repository")
    return directory
