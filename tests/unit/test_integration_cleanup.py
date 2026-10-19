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

import contextlib
from unittest.mock import MagicMock

from tests.integration.conftest import _cleanup_integration_temp_dir_impl

pytest_plugins = ["pytester"]


def test_integration_cleanup_success_in_ci(monkeypatch, tmp_path):
    monkeypatch.setenv("CI", "true")
    target_dir = tmp_path / "integration_test_dir"
    target_dir.mkdir()

    request = MagicMock()
    rep_call = MagicMock()
    rep_call.passed = True
    request.node.rep_call = rep_call
    request.fixturenames = ["new_dir"]
    request.getfixturevalue.side_effect = lambda name: (
        target_dir if name == "new_dir" else None
    )

    gen = _cleanup_integration_temp_dir_impl(request)
    next(gen)  # Yield
    with contextlib.suppress(StopIteration):
        next(gen)

    assert not target_dir.exists()


def test_integration_cleanup_failure_in_ci(monkeypatch, tmp_path):
    monkeypatch.setenv("CI", "true")
    target_dir = tmp_path / "integration_test_dir"
    target_dir.mkdir()

    request = MagicMock()
    rep_call = MagicMock()
    rep_call.passed = False
    request.node.rep_call = rep_call
    request.fixturenames = ["new_dir"]
    request.getfixturevalue.side_effect = lambda name: (
        target_dir if name == "new_dir" else None
    )

    gen = _cleanup_integration_temp_dir_impl(request)
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert target_dir.exists()


def test_integration_cleanup_success_not_in_ci(monkeypatch, tmp_path):
    monkeypatch.delenv("CI", raising=False)
    target_dir = tmp_path / "integration_test_dir"
    target_dir.mkdir()

    request = MagicMock()
    rep_call = MagicMock()
    rep_call.passed = True
    request.node.rep_call = rep_call
    request.fixturenames = ["new_dir"]
    request.getfixturevalue.side_effect = lambda name: (
        target_dir if name == "new_dir" else None
    )

    gen = _cleanup_integration_temp_dir_impl(request)
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert target_dir.exists()


def test_pytester_integration_cleanup_in_ci(pytester, monkeypatch):
    monkeypatch.setenv("CI", "true")
    pytester.plugins.append("tests.integration.conftest")
    pytester.makepyfile(
        """
        def test_dummy_integration(tmp_path):
            (tmp_path / "file.txt").write_text("hello")
            assert (tmp_path / "file.txt").exists()
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_pytester_integration_cleanup_on_failure_in_ci(pytester, monkeypatch):
    monkeypatch.setenv("CI", "true")
    pytester.plugins.append("tests.integration.conftest")
    pytester.makepyfile(
        """
        def test_dummy_integration_failing(tmp_path):
            (tmp_path / "file.txt").write_text("hello")
            assert False
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
