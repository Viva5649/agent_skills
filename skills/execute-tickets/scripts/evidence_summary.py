#!/usr/bin/env python3
"""Collect explicit evidence references and reported outcomes without judging acceptance."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from gate_state import StateError, write_new_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", nargs=2, metavar=("ID", "PATH"), action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        artifacts = []
        ids = set()
        for artifact_id, source in args.artifact:
            if not artifact_id.strip() or artifact_id in ids:
                raise ValueError(f"empty or duplicate artifact ID: {artifact_id!r}")
            ids.add(artifact_id)
            path = Path(source).resolve(strict=True)
            raw = path.read_bytes()
            reported = {}
            if path.suffix.lower() == ".json":
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError(f"JSON result must be an object: {path}")
                reported = {
                    key: record[key]
                    for key in ("status", "result", "exit_code", "verdict")
                    if key in record and not isinstance(record[key], (dict, list))
                }
            artifacts.append({
                "id": artifact_id,
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "reported": reported,
            })
        content = (json.dumps({"artifacts": artifacts}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        write_new_file(args.output, content)
        print(json.dumps({"path": str(args.output.resolve()), "sha256": hashlib.sha256(content).hexdigest()}))
        return 0
    except (OSError, ValueError, StateError) as error:
        print(f"evidence-summary: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
