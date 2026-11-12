# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Integration tests for the ``organize`` keyword.

Each test case is driven by a YAML fixture file stored under
``data/organize/``.  The fixture format is::

    description: <human-readable description>

    parts:
      <part-name>:
        plugin: dump
        source: src
        organize:
          <src-pattern>: <dst-path>
          ...

    # Optional: directories to create before running the lifecycle.
    setup_dirs:
      - src/some/subdir

    # Files to create (as empty files) before running the lifecycle.
    setup_files:
      - src/some/file

    # Paths that must exist inside ``prime/`` after the lifecycle completes.
    expected_prime_present:
      - usr/bin/foo

    # Paths that must *not* exist inside ``prime/`` after the lifecycle completes.
    expected_prime_absent:
      - original/foo

The fixture files are collected from ``data/organize/*.yaml`` and each
becomes a separate parametrised test case identified by the file stem.
"""

from __future__ import annotations

import pathlib
from typing import Any

import craft_parts
import craft_parts.packages
import pytest
import yaml
from craft_parts import Step
from craft_parts.packages.base import DummyRepository

_DATA_DIR = pathlib.Path(__file__).parent / "data" / "organize"


def _load_fixture(path: pathlib.Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


@pytest.mark.parametrize(
    "fixture_path",
    sorted(_DATA_DIR.glob("*.yaml")),
    ids=lambda p: p.stem,
)
def test_organize(new_dir, mocker, fixture_path: pathlib.Path) -> None:
    """Run a lifecycle to PRIME and verify organize results.

    For each fixture file the test:

    1. Creates the directories and files listed under ``setup_dirs`` /
       ``setup_files`` relative to the temporary working directory.
    2. Runs the craft-parts lifecycle up to ``Step.PRIME``.
    3. Asserts that every path in ``expected_prime_present`` exists inside
       ``prime/`` and every path in ``expected_prime_absent`` does *not*.
    """
    # Use DummyRepository so that the tests do not require an apt back-end.
    mocker.patch.object(craft_parts.packages, "Repository", DummyRepository)
    data = _load_fixture(fixture_path)

    # --- Set up the source tree ---
    for directory in data.get("setup_dirs", []):
        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    for file_path in data.get("setup_files", []):
        path = pathlib.Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    # --- Run the lifecycle ---
    lf = craft_parts.LifecycleManager(
        {"parts": data["parts"]},
        application_name="test_organize",
        cache_dir=new_dir,
    )
    actions = lf.plan(Step.PRIME)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # --- Assert expected outcomes ---
    for rel_path in data.get("expected_prime_present", []):
        target = pathlib.Path("prime") / rel_path
        assert target.exists(), (
            f"Expected '{rel_path}' to be present in prime/ but it was not found.\n"
            f"  (fixture: {fixture_path.name})"
        )

    for rel_path in data.get("expected_prime_absent", []):
        target = pathlib.Path("prime") / rel_path
        assert not target.exists(), (
            f"Expected '{rel_path}' to be absent from prime/ but it was found.\n"
            f"  (fixture: {fixture_path.name})"
        )
