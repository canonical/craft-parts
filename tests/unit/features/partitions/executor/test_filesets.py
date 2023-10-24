# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
from craft_parts.executor import filesets


@pytest.mark.parametrize(
    ("entries", "includes", "excludes"),
    [
        ([], [], []),
        (["foo", "-bar"], ["default/foo"], ["default/bar"]),
        (["(foo)/bar", "-baz"], ["foo/bar"], ["default/baz"]),
        (["(foo)/file1", "-file1"], ["foo/file1"], ["default/file1"]),
    ],
)
def test_partition_filesets(entries, includes, excludes):
    """Test that partitions are correctly applied to fileset include and excludes."""
    fs = filesets.Fileset(entries)

    assert includes == fs.includes
    assert excludes == fs.excludes


@pytest.mark.parametrize(
    ("entries", "includes", "excludes"),
    [
        ([], ["*"], []),
        (["foo", "-bar"], ["default/foo"], ["default/bar"]),
        (["(foo)/bar", "-baz"], ["foo/bar"], ["default/baz"]),
        (["(foo)/file1", "-file1"], ["foo/file1"], ["default/file1"]),
    ],
)
def test_get_file_list_with_partitions(entries, includes, excludes):
    """Test that partitions are correctly applied to fileset include and excludes."""
    fs = filesets.Fileset(entries)

    actual_includes, actual_excludes = filesets._get_file_list(fs)

    assert includes == actual_includes
    assert excludes == actual_excludes
