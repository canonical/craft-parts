# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2025 Canonical Ltd.
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
from craft_parts.errors import FilesetError
from craft_parts.executor import filesets


@pytest.mark.parametrize(
    ("data", "entries", "includes", "excludes"),
    [
        ([], [], [], []),
        (
            ["a", "(default)/b", "(foo)/c"],
            ["(default)/a", "(default)/b", "(foo)/c"],
            ["(default)/a", "(default)/b", "(foo)/c"],
            [],
        ),
        (
            ["a", "-(default)/b", "-(foo)/c"],
            ["(default)/a", "-(default)/b", "-(foo)/c"],
            ["(default)/a"],
            ["(default)/b", "(foo)/c"],
        ),
    ],
)
def test_fileset(data, entries, includes, excludes):
    fs = filesets.Fileset(data)
    assert fs.entries == entries
    assert fs.includes == includes
    assert fs.excludes == excludes


def test_representation():
    fs = filesets.Fileset(["foo", "bar"], name="foobar")
    assert f"{fs!r}" == "Fileset(['(default)/foo', '(default)/bar'], name='foobar')"


def test_entries():
    """`entries` is a read-only property."""
    fs = filesets.Fileset(["foo", "bar"])
    fs.entries.append("baz")
    assert fs.entries == ["(default)/foo", "(default)/bar"]


@pytest.mark.parametrize(
    ("entries", "remove", "expected"),
    [
        (["foo", "bar"], "bar", ["(default)/foo"]),
        (["(default)/foo", "(default)/bar"], "bar", ["(default)/foo"]),
        (["foo", "(default)/bar"], "(default)/bar", ["(default)/foo"]),
        (["foo", "(mypart)/foo"], "(mypart)/foo", ["(default)/foo"]),
    ],
)
def test_remove(entries, remove, expected):
    """Remove an entry from a fileset."""
    fs = filesets.Fileset(entries)
    fs.remove(remove)
    assert fs.entries == expected


@pytest.mark.xfail(strict=True, reason="combine function is not partition-aware")
@pytest.mark.parametrize(
    ("fs1", "fs2", "result"),
    [
        (["foo"], ["bar", "*"], ["foo", "bar"]),
    ],
)
def test_combine(fs1, fs2, result):
    stage_set = filesets.Fileset(fs1)
    prime_set = filesets.Fileset(fs2)
    prime_set.combine(stage_set)
    assert sorted(prime_set.entries) == sorted(result)


@pytest.mark.parametrize(
    ("partition", "expected_includes"),
    [
        ("default", ["a", "b"]),
        ("foo", ["c"]),
    ],
)
def test_fileset_only_includes(partition, expected_includes):
    stage_set = filesets.Fileset(["a", "(default)/b", "(foo)/c"])

    includes, excludes = filesets._get_file_list(
        stage_set, partition=partition, default_partition="default"
    )

    assert includes == expected_includes
    assert excludes == []


@pytest.mark.parametrize(
    ("partition", "expected_excludes"),
    [
        ("default", ["a", "b"]),
        ("foo", ["c"]),
    ],
)
def test_fileset_only_excludes(partition, expected_excludes):
    stage_set = filesets.Fileset(["-a", "-(default)/b", "-(foo)/c"])

    includes, excludes = filesets._get_file_list(
        stage_set, partition=partition, default_partition="default"
    )

    assert includes == ["*"]
    assert excludes == expected_excludes


@pytest.mark.parametrize(
    ("abs_entry", "abs_filepath"),
    [
        ("/abs/include", "/abs/include"),
        ("-/abs/exclude", "/abs/exclude"),
    ],
)
def test_filesets_excludes_without_relative_paths(abs_entry, abs_filepath):
    with pytest.raises(FilesetError) as raised:
        filesets._get_file_list(
            filesets.Fileset(["rel", abs_entry], name="test"),
            partition="default",
            default_partition="default",
        )
    assert raised.value.name == "test"
    assert raised.value.message == f"path {abs_filepath!r} must be relative."


@pytest.mark.parametrize(
    ("entries", "includes", "excludes"),
    [
        ([], [], []),
        (["*"], ["(default)/*"], []),
        (["foo", "-bar"], ["(default)/foo"], ["(default)/bar"]),
        (["(foo)/bar", "-baz"], ["(foo)/bar"], ["(default)/baz"]),
        (["(foo)/file1", "-file1"], ["(foo)/file1"], ["(default)/file1"]),
    ],
)
def test_partition_filesets(entries, includes, excludes):
    """Test that partitions are correctly applied to fileset include and excludes."""
    fs = filesets.Fileset(entries)

    assert includes == fs.includes
    assert excludes == fs.excludes


@pytest.mark.parametrize(
    ("partition", "entries", "includes", "excludes"),
    [
        # implicit default partition, inclusive
        ("default", ["*"], ["*"], []),
        ("default", ["foo"], ["foo"], []),
        ("mypart", ["*"], ["*"], []),
        ("mypart", ["foo"], ["*"], []),
        # implicit default partition, exclusive
        ("default", ["-*"], ["*"], ["*"]),
        ("default", ["-foo"], ["*"], ["foo"]),
        ("mypart", ["-*"], ["*"], []),
        ("mypart", ["-foo"], ["*"], []),
        # explicit default partition, inclusive
        ("default", ["(default)/*"], ["*"], []),
        ("default", ["(default)/foo"], ["foo"], []),
        ("mypart", ["(default)/*"], ["*"], []),
        ("mypart", ["(default)/foo"], ["*"], []),
        # explicit default partition, exclusive
        ("default", ["-(default)/*"], ["*"], ["*"]),
        ("default", ["-(default)/foo"], ["*"], ["foo"]),
        ("mypart", ["-(default)/*"], ["*"], []),
        ("mypart", ["-(default)/foo"], ["*"], []),
        # non-default partition, inclusive
        ("default", ["(mypart)/*"], ["*"], []),
        ("default", ["(mypart)/foo"], ["*"], []),
        ("mypart", ["(mypart)/*"], ["*"], []),
        ("mypart", ["(mypart)/foo"], ["foo"], []),
        # non-default partition, exclusive
        ("default", ["-(mypart)/*"], ["*"], []),
        ("default", ["-(mypart)/foo"], ["*"], []),
        ("mypart", ["-(mypart)/*"], ["*"], ["*"]),
        ("mypart", ["-(mypart)/foo"], ["*"], ["foo"]),
        # no partitions
        ("default", [], ["*"], []),
        ("mypart", [], ["*"], []),
    ],
)
def test_get_file_list_with_partitions(partition, entries, includes, excludes):
    """Test that partitions are correctly applied to fileset include and excludes."""
    fs = filesets.Fileset(entries)

    actual_includes, actual_excludes = filesets._get_file_list(
        fs, partition=partition, default_partition="default"
    )

    assert includes == actual_includes
    assert excludes == actual_excludes
