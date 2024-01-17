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
import textwrap

import pytest

from tests.integration.lifecycle import test_lifecycle

# This wildcard import has pytest run any non-overridden lifecycle tests here.
# pylint: disable=wildcard-import,function-redefined,unused-import,unused-wildcard-import
from tests.integration.lifecycle.test_lifecycle import *  # noqa: F403  # pyright: ignore[reportGeneralTypeIssues]

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
    """Run all cleaning tests with partitions enabled."""


class TestUpdating(test_lifecycle.TestUpdating):
    """Run all updating tests with partitions enabled."""
