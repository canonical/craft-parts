#!/usr/bin/env python3
"""Assert that a version tag matches the version in Cargo.toml.

Used in CI when new tags are pushed.
"""

import os
import re
import sys
from pathlib import Path

CARGO_TOML = Path(__file__).resolve().parent.parent / "Cargo.toml"


def main() -> int:
    """Check that a version tag matches the Cargo.toml package version."""
    ref = os.getenv("GITHUB_REF", "")
    tag = ref.removeprefix("refs/tags/")
    if not re.fullmatch(r"\d+\.\d+\.\d+", tag):
        print(f"✓ no version tag in pushed ref {ref!r}")
        return 0
    return 0 if check(tag) else 1


def check(tag: str) -> bool:
    """Return True if ``tag`` matches the Cargo.toml package version."""
    match = re.search(r'^version = "(.+)"', CARGO_TOML.read_text(), flags=re.MULTILINE)
    if not match:
        print(f"✖ no version field found in {CARGO_TOML}")
        return False

    cargo_version = match.group(1)
    if cargo_version == tag:
        print(f"✓ tag {tag!r} matches {CARGO_TOML} version {cargo_version!r}")
        return True

    print(f"✖ tag {tag!r} does not match {CARGO_TOML} version {cargo_version!r}")
    return False


if __name__ == "__main__":
    sys.exit(main())
