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
    assert fs.entries == tc_entries
    assert fs.includes == tc_includes
    assert fs.excludes == tc_excludes


def test_representation():
    fs = Fileset(["foo", "bar"], name="foobar")
    assert f"{fs!r}" == "Fileset(['foo', 'bar'], name='foobar')"


def test_entries():
    fs = Fileset(["foo", "bar"])
    fs.entries.append("baz")
    assert fs.entries == ["foo", "bar"]


def test_remove():
    fs = Fileset(["foo", "bar", "baz"])
    fs.remove("bar")
    assert fs.entries == ["foo", "baz"]


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
    assert sorted(prime_set.entries) == sorted(tc_result)


def test_fileset_combine_conflicts():
    stage_set = Fileset(["thisfile", "-otherfile"])
    prime_set = Fileset(["otherfile"])

    # raise conflict if prime includes a file excluded in stage
    with pytest.raises(errors.FilesetConflict) as raised:
        prime_set.combine(stage_set)
    assert raised.value.conflicting_files == {"otherfile"}


def test_fileset_empty():
    """Empty filesets should default to include a wildcard."""
    stage_set = Fileset([])

    include, exclude = filesets._get_file_list(
        stage_set, partition=None, default_partition="default"
    )

    assert include == ["*"]
    assert exclude == []


def test_fileset_only_includes():
    stage_set = Fileset(["opt/something", "usr/bin"])

    include, exclude = filesets._get_file_list(
        stage_set, partition=None, default_partition="default"
    )

    assert include == ["opt/something", "usr/bin"]
    assert exclude == []


def test_fileset_only_excludes():
    stage_set = Fileset(["-etc", "-usr/lib/*.a"])

    include, exclude = filesets._get_file_list(
        stage_set, partition=None, default_partition="default"
    )

    assert include == ["*"]
    assert exclude == ["etc", "usr/lib/*.a"]


def test_filesets_includes_without_relative_paths():
    with pytest.raises(errors.FilesetError) as raised:
        filesets._get_file_list(
            Fileset(["rel", "/abs/include"], name="test"),
            partition=None,
            default_partition="default",
        )
    assert raised.value.name == "test"
    assert raised.value.message == "path '/abs/include' must be relative."


def test_filesets_excludes_without_relative_paths():
    with pytest.raises(errors.FilesetError) as raised:
        filesets._get_file_list(
            Fileset(["rel", "-/abs/exclude"], name="test"),
            partition=None,
            default_partition="default",
        )
    assert raised.value.name == "test"
    assert raised.value.message == "path '/abs/exclude' must be relative."


def test_migratable_filesets_resolves_symlink_parent_but_not_final_symlink(tmp_path):
    source = tmp_path / "install"
    real_directory = source / "real/nested"
    real_directory.mkdir(parents=True)
    (real_directory / "file").write_text("contents")
    (real_directory / "final-link").symlink_to("file")
    (source / "linked").symlink_to("real", target_is_directory=True)

    files, directories = filesets.migratable_filesets(
        Fileset(["linked/nested/file", "linked/nested/final-link"]),
        source,
        default_partition="default",
    )

    assert files == {Path("real/nested/file"), Path("real/nested/final-link")}
    assert directories == {Path("real"), Path("real/nested")}
    assert (real_directory / "final-link").is_symlink()


def test_migratable_filesets_resolves_shared_parent_once(tmp_path, mocker):
    source = tmp_path / "install"
    directory = source / "shared"
    directory.mkdir(parents=True)
    entries = []
    for index in range(8):
        filename = f"file-{index}"
        (directory / filename).write_text(filename)
        entries.append(f"shared/{filename}")

    original_resolve = Path.resolve
    resolve_calls = 0

    def count_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal resolve_calls
        resolve_calls += 1
        return original_resolve(path, strict=strict)

    mocker.patch.object(Path, "resolve", count_resolve)
    files, directories = filesets.migratable_filesets(
        Fileset(entries),
        source,
        default_partition="default",
    )

    assert files == {Path(entry) for entry in entries}
    assert directories == {Path("shared")}
    assert resolve_calls == 2


def test_migratable_filesets_expands_included_directory(tmp_path):
    source = tmp_path / "install"
    directory = source / "usr/lib/nested"
    directory.mkdir(parents=True)
    (directory / "file").write_text("contents")
    (source / "usr/lib/linked").symlink_to("nested", target_is_directory=True)

    files, directories = filesets.migratable_filesets(
        Fileset(["usr/lib"]),
        source,
        default_partition="default",
    )

    assert files == {Path("usr/lib/nested/file"), Path("usr/lib/linked")}
    assert directories == {
        Path("usr"),
        Path("usr/lib"),
        Path("usr/lib/nested"),
    }
