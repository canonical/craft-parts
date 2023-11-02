# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2023 Canonical Ltd.
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


import pytest

from tests.unit.executor import test_migration


@pytest.mark.usefixtures("new_dir")
class TestFileMigration(test_migration.TestFileMigration):
    """Tests for file migration with partitions enabled."""


@pytest.mark.usefixtures("new_dir")
class TestHelpers(test_migration.TestHelpers):
    """Tests for helpers with partitions enabled."""


@pytest.mark.usefixtures("new_dir")
class TestFilterWhiteouts(test_migration.TestFilterWhiteouts):
    """Tests for filter whiteouts with partitions enabled."""
