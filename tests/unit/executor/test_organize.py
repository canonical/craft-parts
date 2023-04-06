# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
from typing import Any, List, Tuple, cast

import pytest

from craft_parts import errors
from craft_parts.executor.organize import organize_files


@pytest.mark.parametrize(
    "data",
    [
        # simple_file
        {
            "setup_dirs": [],
            "setup_files": ["foo"],
            "organize_map": {"foo": "bar"},
            "expected": [(["bar"], "")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # simple_dir_with_file
        {
            "setup_dirs": ["foodir"],
            "setup_files": [os.path.join("foodir", "foo")],
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
            "expected_message": None,
            "expected_overwrite": None,
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
            "expected_message": None,
            "expected_overwrite": None,
        },
        # leading_slash_in_value
        {
            "setup_dirs": [],
            "setup_files": ["foo"],
            "organize_map": {"foo": "/bar"},
            "expected": [(["bar"], "")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # overwrite_existing_file
        {
            "setup_dirs": [],
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
            "setup_dirs": [],
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir/"},
            "expected": [(["dir"], ""), (["bar.conf", "foo.conf"], "dir")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # *_for_files_with_non_dir_dst
        {
            "setup_dirs": [],
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir"},
            "expected": errors.FileOrganizeError,
            "expected_message": r".*multiple files to be organized into 'dir'.*",
            "expected_overwrite": None,
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
            "expected_message": None,
            "expected_overwrite": None,
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
            "expected_message": None,
            "expected_overwrite": None,
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
            "expected_message": None,
            "expected_overwrite": None,
        },
    ],
)
def test_organize(new_dir, data):
    _organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data["setup_dirs"],
        setup_files=data["setup_files"],
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data["expected_message"],
        expected_overwrite=data["expected_overwrite"],
        overwrite=False,
    )

    # Verify that it can be organized again by overwriting
    _organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data["setup_dirs"],
        setup_files=data["setup_files"],
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data["expected_message"],
        expected_overwrite=data["expected_overwrite"],
        overwrite=True,
    )


def _organize_and_assert(
    *,
    tmp_path: Path,
    setup_dirs,
    setup_files,
    organize_map,
    expected: List[Any],
    expected_message,
    expected_overwrite,
    overwrite,
):
    base_dir = Path(tmp_path / "install")
    base_dir.mkdir(parents=True, exist_ok=True)

    for directory in setup_dirs:
        (base_dir / directory).mkdir(exist_ok=True)

    for file_entry in setup_files:
        (base_dir / file_entry).touch()

    if overwrite and expected_overwrite is not None:
        expected = expected_overwrite

    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected) as raised:  # type: ignore
            organize_files(
                part_name="part-name",
                mapping=organize_map,
                base_dir=base_dir,
                overwrite=overwrite,
            )
        assert re.match(expected_message, str(raised.value)) is not None

    else:
        organize_files(
            part_name="part-name",
            mapping=organize_map,
            base_dir=base_dir,
            overwrite=overwrite,
        )
        expected = cast(List[Tuple[List[str], str]], expected)
        for expect in expected:
            dir_path = (base_dir / expect[1]).as_posix()
            dir_contents = os.listdir(dir_path)
            dir_contents.sort()
            assert dir_contents == expect[0]
