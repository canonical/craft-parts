# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2025 Canonical Ltd.
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
from craft_parts import errors, features
from craft_parts.executor import filesets
from craft_parts.executor.filesets import Fileset

from tests.unit.executor import test_migration


@pytest.mark.usefixtures("new_dir")
class TestFileMigration(test_migration.TestFileMigration):
    """Tests for file migration with partitions enabled."""


@pytest.mark.usefixtures("new_dir")
class TestFileMigrationErrors:
    def test_migratable_filesets_partition_not_defined_error(self):
        """Error if the partition feature is enabled and a partition is not provided."""
        with pytest.raises(errors.FeatureError) as raised:
            filesets.migratable_filesets(
                Fileset(["*"]), "install", default_partition="default", partition=None
            )

        assert features.Features().enable_partitions
        assert (
            "A partition must be provided if the partition feature is enabled."
        ) in str(raised.value)


@pytest.mark.usefixtures("new_dir")
class TestHelpers(test_migration.TestHelpers):
    """Tests for helpers with partitions enabled."""


@pytest.mark.usefixtures("new_dir")
class TestFilterWhiteouts(test_migration.TestFilterWhiteouts):
    """Tests for filter whiteouts with partitions enabled."""
