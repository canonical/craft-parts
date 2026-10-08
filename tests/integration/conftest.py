# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
"""Configuration for integration tests."""

import contextlib
import os
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    """Store test result report on item for fixture teardown inspection."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def _cleanup_integration_temp_dir_impl(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Clean up temporary directory after successful integration tests in CI."""
    yield

    if not os.getenv("CI"):
        return

    rep_call = getattr(request.node, "rep_call", None)
    if not rep_call or not rep_call.passed:
        return

    dirs_to_delete = set()
    for fixture_name in (
        "new_dir",
        "new_path",
        "tmp_path",
        "tmpdir",
        "tmp_homedir_path",
        "new_homedir_path",
    ):
        if fixture_name in request.fixturenames:
            with contextlib.suppress(Exception):
                val = request.getfixturevalue(fixture_name)
                path = Path(val).resolve()
                if path.exists() and path.is_dir():
                    dirs_to_delete.add(path)

    for path in dirs_to_delete:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def _cleanup_integration_temp_dir(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Clean up temporary directory after successful integration tests in CI."""
    return _cleanup_integration_temp_dir_impl(request)
