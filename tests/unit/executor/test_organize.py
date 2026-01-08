# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2025 Canonical Ltd.
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

import re
from pathlib import Path
from typing import Any, cast

import pytest
from craft_parts import errors
from craft_parts.executor.organize import organize_files


@pytest.mark.parametrize(
    "data",
    [
        # simple_file
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "bar"},
            "expected": [(["bar"], "")],
        },
        # simple_dir_with_file
        {
            "setup_dirs": ["foodir"],
            "setup_files": [str(Path("foodir", "foo"))],
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize_to_the_same_directory
        {
            "setup_dirs": ["bardir", "foodir"],
            "setup_files": [
                str(Path("foodir", "foo")),
                str(Path("bardir", "bar")),
                "basefoo",
            ],
            "organize_map": {
                "foodir": "bin",
                "bardir": "bin",
                "basefoo": "bin/basefoo",
            },
            "expected": [(["bin"], ""), (["bar", "basefoo", "foo"], "bin")],
        },
        # leading_slash_in_value
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "/bar"},
            "expected": [(["bar"], "")],
        },
        # overwrite_existing_file
        {
            "setup_files": ["foo", "bar"],
            "organize_map": {"foo": "bar"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo' to 'bar', but 'bar' already exists.*"
            ),
            "expected_overwrite": [(["bar"], "")],
        },
        # *_for_files
        {
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir/"},
            "expected": [(["dir"], ""), (["bar.conf", "foo.conf"], "dir")],
        },
        # *_for_files_with_non_dir_dst
        {
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir"},
            "expected": errors.FileOrganizeError,
            "expected_message": r".*multiple files to be organized into 'dir'.*",
        },
        # *_for_directories
        {
            "setup_dirs": ["dir1", "dir2"],
            "setup_files": [
                str(Path("dir1", "foo")),
                str(Path("dir2", "bar")),
            ],
            "organize_map": {"dir*": "dir/"},
            "expected": [
                (["dir"], ""),
                (["dir1", "dir2"], "dir"),
                (["foo"], str(Path("dir", "dir1"))),
                (["bar"], str(Path("dir", "dir2"))),
            ],
        },
        # combined_*_with_file
        {
            "setup_dirs": ["dir1", "dir2"],
            "setup_files": [
                str(Path("dir1", "foo")),
                str(Path("dir1", "bar")),
                str(Path("dir2", "bar")),
            ],
            "organize_map": {"dir*": "dir/", "dir1/bar": "."},
            "expected": [
                (["bar", "dir"], ""),
                (["dir1", "dir2"], "dir"),
                (["foo"], str(Path("dir", "dir1"))),
                (["bar"], str(Path("dir", "dir2"))),
            ],
        },
        # *_into_dir
        {
            "setup_dirs": ["dir"],
            "setup_files": [
                str(Path("dir", "foo")),
                str(Path("dir", "bar")),
            ],
            "organize_map": {"dir/f*": "nested/dir/"},
            "expected": [
                (["dir", "nested"], ""),
                (["bar"], "dir"),
                (["dir"], "nested"),
                (["foo"], str(Path("nested", "dir"))),
            ],
        },
        # organize a file to itself
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "foo"},
            "expected": [(["foo"], "")],
        },
        # organize a file to itself with different path
        {
            "setup_dirs": ["bardir"],
            "setup_files": ["foo"],
            "organize_map": {"bardir/../foo": "foo"},
            "expected": [(["bardir", "foo"], "")],
        },
        # organize a set with a file to itself
        {
            "setup_dirs": ["bardir"],
            "setup_files": ["bardir/foo"],
            "organize_map": {"bardir/*": "bardir/"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize from subdirs to itself
        {
            "setup_dirs": ["foodir", "foodir/bardir"],
            "setup_files": ["foodir/bardir/foo"],
            "organize_map": {"**/bardir/*": "bardir/"},
            "expected": [(["bardir", "foodir"], ""), (["foo"], "bardir")],
        },
    ],
)
def test_organize(new_dir, data):
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
    )

    # Verify that it can be organized again by overwriting
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=True,
        install_dirs={None: Path(new_dir / "install")},
    )


@pytest.mark.parametrize(
    "data",
    [
        # organize a symlink to its target
        # Running this test with overwrite=True would delete the target
        # and replace it with the symlink, effectively pointing at itself.
        # This is the current behavior but might not be the intended one.
        {
            "setup_files": ["foo"],
            "setup_symlinks": [("foo-link", "foo")],
            "organize_map": {"foo-link": "foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo-link' to 'foo', but 'foo' already exists.*"
            ),
        },
        # organize a file under a symlinked directory to the symlink target
        {
            "setup_files": ["foo"],
            "setup_symlinks": [("bardir", ".")],
            "organize_map": {"bardir/foo": "foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'bardir/foo' to 'foo', but 'foo' already exists.*"
            ),
        },
        # organize a file under a symlinked directory to the symlink target
        {
            "setup_files": ["foo"],
            "setup_symlinks": [("bardir", ".")],
            "organize_map": {"foo": "bardir/foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo' to 'bardir/foo', but 'bardir/foo' already exists.*"
            ),
        },
        # Organize 2 files to the same destination, one with a dir as a destination
        {
            "setup_dirs": ["dir1", "dir2"],
            "setup_files": [
                str(Path("dir1", "foo")),
                str(Path("dir2", "foo")),
            ],
            "organize_map": {"dir1/foo": "dir/foo", "dir2/foo": "dir/"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize 'dir2/foo' to 'dir/', but 'dir/foo' already exists.*"
            ),
        },
        # Organize 2 files to the same destination, one referenced with a wildcard
        {
            "setup_dirs": ["dir1", "dir2"],
            "setup_files": [
                str(Path("dir1", "foo")),
                str(Path("dir2", "foo")),
            ],
            "organize_map": {"dir1/foo": "dir/foo", "dir2/*": "dir/"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize 'dir2/\*' to 'dir/', but 'dir/foo' already exists.*"
            ),
        },
    ],
)
def test_organize_no_overwrite(new_dir, data):
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
    )


def organize_and_assert(
    *,
    tmp_path: Path,
    setup_dirs,
    setup_files,
    setup_symlinks: list[tuple[str, str]],
    organize_map,
    expected: list[Any],
    expected_message,
    expected_overwrite,
    overwrite,
    install_dirs,
):
    install_dir = Path(tmp_path / "install")
    install_dir.mkdir(parents=True, exist_ok=True)

    for directory in setup_dirs:
        (install_dir / directory).mkdir(exist_ok=True)

    for file_entry in setup_files:
        (install_dir / file_entry).touch()

    for symlink_entry, symlink_target in setup_symlinks:
        symlink_path = install_dir / symlink_entry
        if not symlink_path.is_symlink():
            symlink_path.symlink_to(install_dir / symlink_target)

    if overwrite and expected_overwrite is not None:
        expected = expected_overwrite

    if isinstance(expected, type) and issubclass(expected, Exception):
        raised: pytest.ExceptionInfo
        with pytest.raises(expected) as raised:
            organize_files(
                part_name="part-name",
                file_map=organize_map,
                install_dir_map=install_dirs,
                overwrite=overwrite,
                default_partition="default",
            )
        assert re.match(expected_message, str(raised.value)) is not None

    else:
        organize_files(
            part_name="part-name",
            file_map=organize_map,
            install_dir_map=install_dirs,
            overwrite=overwrite,
            default_partition="default",
        )
        expected = cast(list[tuple[list[str], str]], expected)
        for expect in expected:
            dir_path = install_dir / expect[1]
            dir_contents = sorted(path.name for path in dir_path.iterdir())
            assert dir_contents == expect[0]
