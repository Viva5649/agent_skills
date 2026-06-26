#!/usr/bin/env python3
"""Runtime paths for creator-signal-digest."""
from pathlib import Path


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def generated_root() -> Path:
    path = skill_root() / "generated"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir() -> Path:
    path = generated_root() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_file(name: str) -> Path:
    return runtime_dir() / name
