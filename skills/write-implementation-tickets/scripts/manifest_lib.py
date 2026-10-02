"""Shared byte-freeze primitives for the deterministic manifest and admission scripts.

This module owns only mechanical facts about exact file bytes: hashing,
repository containment, presentation-block boundaries, and
`{path, sha256, size, authority_sha256}` records. Each consuming script keeps its
own manifest schema, validation semantics, and CLI.

The authoring and execution skills carry byte-identical copies of this file. A
divergent authority boundary would let one skill admit bytes the other refuses,
so any change here must land in both copies together.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


DELIMITER = b"---"
PRESENTATION_KEYS = frozenset({"display_title"})
PRESENTATION_LINE = re.compile(rb"^([a-z_]+):[ \t]*(\S.*)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authority_offset(data: bytes) -> int:
    """Return the byte offset where authority content starts.

    A leading presentation block is excluded only when it is unambiguous: a
    terminated `---` block whose flat `key: value` lines all name an allowed
    presentation key exactly once. Every other shape — unknown key, duplicate
    key, empty value, indentation, nesting, unterminated block — returns 0 so the
    whole file stays authority. The degradation always adds authority rather than
    removing it, so a malformed block costs an extra review instead of skipping one.
    """
    lines = data.split(b"\n")
    if not lines or lines[0] != DELIMITER:
        return 0

    seen: set[str] = set()
    offset = len(lines[0]) + 1
    for line in lines[1:]:
        if line == DELIMITER:
            return offset + len(line) + 1 if seen else 0
        match = PRESENTATION_LINE.match(line)
        if match is None:
            return 0
        key = match.group(1).decode("ascii")
        if key not in PRESENTATION_KEYS or key in seen:
            return 0
        seen.add(key)
        offset += len(line) + 1
    return 0


def authority_sha256(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data[authority_offset(data) :]).hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def repository_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.is_dir():
        raise ValueError(f"repository does not exist: {root}")
    return root


def file_record(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    return {
        "path": relative,
        "sha256": sha256(path),
        "size": path.stat().st_size,
        "authority_sha256": authority_sha256(path),
    }


def record_authority(record: dict[str, object]) -> object:
    """Read a record's authority digest, falling back to a pre-authority manifest."""
    return record.get("authority_sha256", record.get("sha256"))
