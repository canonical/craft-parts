#!/usr/bin/env python3
"""Assert that a version tag matches the version in Cargo.toml.

Usage:
  - CI:             check_version.py          (reads the tag from GITHUB_REF)
  - pre-push hook:  check_version.py          (reads PRE_COMMIT_LOCAL_BRANCH)
  - manual:         check_version.py X.Y.Z

The release tag is the single source of truth for the published version;
this check ensures the hand-maintained Cargo.toml version agrees with it
before artifacts are built and published.
"""

import os
import re
import sys
from pathlib import Path

CARGO_TOML = Path(__file__).resolve().parent.parent / "Cargo.toml"


def main() -> int:
    """Check that a version tag matches the Cargo.toml package version.

    Without arguments, the tag comes from GITHUB_REF (CI) or
    PRE_COMMIT_LOCAL_BRANCH (pre-commit pre-push hook); a push containing no
    version tag passes. With an argument, that tag is checked directly.
    """
    if len(sys.argv) > 1:
        return 0 if check(sys.argv[1]) else 1

    ref = os.getenv("GITHUB_REF") or os.getenv("PRE_COMMIT_LOCAL_BRANCH", "")
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
