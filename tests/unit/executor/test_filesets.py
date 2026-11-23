# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.executor import Fileset, filesets


@pytest.mark.parametrize(
    ("tc_data", "tc_entries", "tc_includes", "tc_excludes"),
    [
        ([], [], [], []),
        (["a", "b"], ["a", "b"], ["a", "b"], []),
        (["a", "-b"], ["a", "-b"], ["a"], ["b"]),
    ],
)
def test_fileset(tc_data, tc_entries, tc_includes, tc_excludes):
    fs = Fileset(tc_data)
    assert fs.entries == [
        filesets.normalize_entry(entry, "default") for entry in tc_entries
    ]
    assert fs.includes == [
        filesets.normalize_entry(entry, "default") for entry in tc_includes
    ]
    assert fs.excludes == [
        filesets.normalize_entry(f"-{entry}", "default")[1:] for entry in tc_excludes
    ]


def test_representation():
    fs = Fileset(["foo", "bar"], name="foobar")
    assert f"{fs!r}" == "Fileset(['(default)/foo', '(default)/bar'], name='foobar')"


def test_entries():
    fs = Fileset(["foo", "bar"])
    fs.entries.append("baz")
    assert fs.entries == ["(default)/foo", "(default)/bar"]


def test_remove():
    fs = Fileset(["foo", "bar", "baz"])
    fs.remove("bar")
    assert fs.entries == ["(default)/foo", "(default)/baz"]


def test_remove_parenthesised_path_when_partitions_disabled():
    fs = Fileset(["(etc)/foo"])
    fs.remove("(etc)/foo")
    assert fs.entries == []


@pytest.mark.parametrize(
    ("tc_fs1", "tc_fs2", "tc_result"),
    [
        ([], [], []),
        (["foo"], ["bar"], ["bar"]),
        (["foo"], ["bar", "baz"], ["bar", "baz"]),
        # combine if fs2 has a wildcard
        (["foo"], ["bar", "*"], ["foo", "bar"]),
        (["foo", "bar"], ["*"], ["foo", "bar"]),
        (["*"], ["foo", "bar"], ["foo", "bar"]),
        # combine if fs2 is only excludes
        (["foo"], ["-bar"], ["foo", "-bar"]),
        (["foo", "*"], ["bar"], ["bar"]),
        (["-foo"], ["-bar"], ["-foo", "-bar"]),
        (["-foo"], ["bar"], ["bar"]),
        (["-foo"], ["bar", "baz"], ["bar", "baz"]),
        (["foo"], ["-bar", "baz"], ["-bar", "baz"]),
        (["foo", "bar"], ["-baz"], ["bar", "-baz", "foo"]),
        (["-foo", "bar"], ["bar"], ["bar"]),
        # all files removed in prime
        (["foo"], ["-*"], ["foo", "-*"]),
        # combine wildcards
        (["-*"], ["*"], ["-*"]),
        (["-*"], ["somefile", "*"], ["-*", "somefile"]),
    ],
)
def test_combine(tc_fs1, tc_fs2, tc_result):
    stage_set = Fileset(tc_fs1)
    prime_set = Fileset(tc_fs2)
    prime_set.combine(stage_set)
    assert sorted(prime_set.entries) == sorted(
        [filesets.normalize_entry(entry, "default") for entry in tc_result]
    )


def test_fileset_combine_conflicts():
    stage_set = Fileset(["thisfile", "-otherfile"])
    prime_set = Fileset(["otherfile"])

    # raise conflict if prime includes a file excluded in stage
    with pytest.raises(errors.FilesetConflict) as raised:
        prime_set.combine(stage_set)
    assert raised.value.conflicting_files == {"(default)/otherfile"}


def test_fileset_empty():
    """Fileset filtering now requires an explicit partition."""
    stage_set = Fileset([])

    include, exclude = filesets._get_file_list(
        stage_set, partition="default", default_partition="default"
    )

    assert include == ["*"]
    assert exclude == []


def test_fileset_only_includes():
    stage_set = Fileset(["opt/something", "usr/bin"])

    include, exclude = filesets._get_file_list(
        stage_set, partition="default", default_partition="default"
    )

    assert include == ["opt/something", "usr/bin"]
    assert exclude == []


def test_fileset_only_excludes():
    stage_set = Fileset(["-etc", "-usr/lib/*.a"])

    include, exclude = filesets._get_file_list(
        stage_set, partition="default", default_partition="default"
    )

    assert include == ["*"]
    assert exclude == ["etc", "usr/lib/*.a"]


def test_filesets_includes_without_relative_paths():
    with pytest.raises(errors.FilesetError) as raised:
        filesets._get_file_list(
            Fileset(["rel", "/abs/include"], name="test"),
            partition="default",
            default_partition="default",
        )
    assert raised.value.name == "test"
    assert raised.value.message == "path '/abs/include' must be relative."


def test_filesets_excludes_without_relative_paths():
    with pytest.raises(errors.FilesetError) as raised:
        filesets._get_file_list(
            Fileset(["rel", "-/abs/exclude"], name="test"),
            partition="default",
            default_partition="default",
        )
    assert raised.value.name == "test"
    assert raised.value.message == "path '/abs/exclude' must be relative."


def test_fileset_parenthesised_paths_literal(new_dir):
    """Parenthesised names are regular paths if partitions are not enabled."""
    fs = Fileset(["(etc)/foo", "(default)/bar", "-(default)/bar/baz"])
    assert fs.entries == [
        "(default)/(etc)/foo",
        "(default)/(default)/bar",
        "-(default)/(default)/bar/baz",
    ]

    install_dir = Path("install")
    for path in ["(etc)/foo", "(default)/bar/baz", "(default)/bar/qux", "other"]:
        (install_dir / path).parent.mkdir(parents=True, exist_ok=True)
        (install_dir / path).touch()

    files, _ = filesets.migratable_filesets(fs, install_dir, "default", "default")
    assert files == {Path("(etc)/foo"), Path("(default)/bar/qux")}


@pytest.mark.usefixtures("enable_partitions_feature")
def test_fileset_parenthesised_paths_partitions_enabled():
    """Parenthesised names are partitions if partitions are enabled."""
    fs = Fileset(["(etc)/foo", "(default)/bar"])
    assert fs.entries == ["(etc)/foo", "(default)/bar"]


# migratable_filesets tested in tests/unit/executor/test_step_handler.py
