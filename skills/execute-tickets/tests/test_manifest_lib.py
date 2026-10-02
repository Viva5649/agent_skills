#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "manifest_lib.py"

VALID_BLOCK = b"---\ndisplay_title: Runtime mode\n---\n"
BODY = b"# Spec\n\nAuthority bytes.\n"

# Every block shape the authority boundary must refuse. A refused block leaves the whole
# file as authority, so a malformed block costs an extra review instead of skipping one.
REFUSED_BLOCKS = {
    "unknown key": b"---\nowner: platform\n---\n",
    "unknown key beside an allowed one": b"---\ndisplay_title: Runtime mode\nowner: platform\n---\n",
    "duplicate key": b"---\ndisplay_title: First\ndisplay_title: Second\n---\n",
    "empty value": b"---\ndisplay_title:\n---\n",
    "whitespace-only value": b"---\ndisplay_title:   \n---\n",
    "indented key": b"---\n  display_title: Runtime mode\n---\n",
    "nested mapping": b"---\ndisplay_title:\n  nested: Runtime mode\n---\n",
    "unterminated block": b"---\ndisplay_title: Runtime mode\n",
    "empty block": b"---\n---\n",
}


def load_manifest_lib():
    module_spec = importlib.util.spec_from_file_location("manifest_lib_under_test", SCRIPT)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class AuthorityBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_lib = load_manifest_lib()
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def write(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_terminated_block_with_one_allowed_key_is_excluded(self) -> None:
        self.assertEqual(
            len(VALID_BLOCK), self.manifest_lib.authority_offset(VALID_BLOCK + BODY)
        )

    def test_file_without_a_leading_block_stays_wholly_authority(self) -> None:
        self.assertEqual(0, self.manifest_lib.authority_offset(BODY))

    def test_refused_block_shapes_keep_the_whole_file_as_authority(self) -> None:
        for shape, block in REFUSED_BLOCKS.items():
            with self.subTest(shape=shape):
                self.assertEqual(0, self.manifest_lib.authority_offset(block + BODY))

    def test_refused_block_bytes_are_covered_by_the_authority_digest(self) -> None:
        for shape, block in REFUSED_BLOCKS.items():
            with self.subTest(shape=shape):
                data = block + BODY
                path = self.write("spec.md", data)
                self.assertEqual(
                    hashlib.sha256(data).hexdigest(),
                    self.manifest_lib.authority_sha256(path),
                )

    def test_accepted_block_bytes_are_excluded_from_the_authority_digest(self) -> None:
        original = self.write("spec.md", VALID_BLOCK + BODY)
        retitled = self.write(
            "retitled.md", b"---\ndisplay_title: A different title\n---\n" + BODY
        )
        self.assertEqual(hashlib.sha256(BODY).hexdigest(), self.manifest_lib.authority_sha256(original))
        self.assertEqual(
            self.manifest_lib.authority_sha256(original),
            self.manifest_lib.authority_sha256(retitled),
        )

    def test_body_change_under_an_accepted_block_changes_the_authority_digest(self) -> None:
        original = self.write("spec.md", VALID_BLOCK + BODY)
        edited = self.write("edited.md", VALID_BLOCK + BODY + b"One more sentence.\n")
        self.assertNotEqual(
            self.manifest_lib.authority_sha256(original),
            self.manifest_lib.authority_sha256(edited),
        )


if __name__ == "__main__":
    unittest.main()
