# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

# Allow redefinition in order to include parent tests below.
# mypy: disable-error-code="no-redef"
import pathlib
import textwrap

import pytest
from craft_parts import Step

from tests.integration.lifecycle import test_lifecycle

# This wildcard import has pytest run any non-overridden lifecycle tests here.
# pylint: disable=wildcard-import,function-redefined,unused-import,unused-wildcard-import
from tests.integration.lifecycle.test_lifecycle import *  # noqa: F403  # pyright: ignore[reportGeneralTypeIssues,reportAssignmentType]

basic_parts_yaml = textwrap.dedent(
    """\
    parts:
      bar:
        after: [foo]
        plugin: nil

      foo:
        plugin: nil
        source: a.tar.gz

      foobar:
        plugin: nil"""
)


@pytest.mark.usefixtures("new_dir")
class TestCleaning(test_lifecycle.TestCleaning):
    @pytest.fixture()
    def foo_files(self):
        return [
            pathlib.Path("parts/foo/src/foo.txt"),
            pathlib.Path("parts/foo/install/default/foo.txt"),
            pathlib.Path("stage/default/foo.txt"),
            pathlib.Path("prime/default/foo.txt"),
        ]

    @pytest.fixture()
    def bar_files(self):
        return [
            pathlib.Path("parts/bar/src/bar.txt"),
            pathlib.Path("parts/bar/install/default/bar.txt"),
            pathlib.Path("stage/default/bar.txt"),
            pathlib.Path("prime/default/bar.txt"),
        ]

    @pytest.mark.parametrize(
        ("step", "test_dir", "state_file"),
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install/default", "build"),
            (Step.STAGE, "stage/default", "stage"),
            (Step.PRIME, "prime/default", "prime"),
        ],
    )
    def test_clean_step(self, step, test_dir, state_file):
        super().test_clean_step(step, test_dir, state_file)


class TestUpdating(test_lifecycle.TestUpdating):
    """Run all updating tests with partitions enabled."""
