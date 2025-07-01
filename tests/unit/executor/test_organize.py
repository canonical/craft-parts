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

import os
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
            "setup_files": [os.path.join("foodir", "foo")],
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize_to_the_same_directory
        {
            "setup_dirs": ["bardir", "foodir"],
            "setup_files": [
                os.path.join("foodir", "foo"),
                os.path.join("bardir", "bar"),
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
                os.path.join("dir1", "foo"),
                os.path.join("dir2", "bar"),
            ],
            "organize_map": {"dir*": "dir/"},
            "expected": [
                (["dir"], ""),
                (["dir1", "dir2"], "dir"),
                (["foo"], os.path.join("dir", "dir1")),
                (["bar"], os.path.join("dir", "dir2")),
            ],
        },
        # combined_*_with_file
        {
            "setup_dirs": ["dir1", "dir2"],
            "setup_files": [
                os.path.join("dir1", "foo"),
                os.path.join("dir1", "bar"),
                os.path.join("dir2", "bar"),
            ],
            "organize_map": {"dir*": "dir/", "dir1/bar": "."},
            "expected": [
                (["bar", "dir"], ""),
                (["dir1", "dir2"], "dir"),
                (["foo"], os.path.join("dir", "dir1")),
                (["bar"], os.path.join("dir", "dir2")),
            ],
        },
        # *_into_dir
        {
            "setup_dirs": ["dir"],
            "setup_files": [
                os.path.join("dir", "foo"),
                os.path.join("dir", "bar"),
            ],
            "organize_map": {"dir/f*": "nested/dir/"},
            "expected": [
                (["dir", "nested"], ""),
                (["bar"], "dir"),
                (["dir"], "nested"),
                (["foo"], os.path.join("nested", "dir")),
            ],
        },
    ],
)
def test_organize(new_dir, data):
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
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
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=True,
        install_dirs={None: Path(new_dir / "install")},
    )


def organize_and_assert(
    *,
    tmp_path: Path,
    setup_dirs,
    setup_files,
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
            dir_path = (install_dir / expect[1]).as_posix()
            dir_contents = os.listdir(dir_path)
            dir_contents.sort()
            assert dir_contents == expect[0]
