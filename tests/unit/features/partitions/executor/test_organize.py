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
import os
import pathlib

import pytest

from craft_parts import errors
from tests.unit.executor.test_organize import organize_and_assert


@pytest.mark.parametrize(
    "data",
    [
        # File in the default partition
        {
            "setup_dirs": [],
            "setup_files": ["default/foo"],
            "organize_map": {"foo": "bar"},
            "expected": [(["bar"], "default")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # Files that should have the same name in two different partitions
        {
            "setup_dirs": [],
            "setup_files": ["default/foo", "mypart/bar"],
            "organize_map": {"foo": "baz", "(mypart)/bar": "(mypart)/baz"},
            "expected": [(["baz"], "default"), (["baz"], "mypart")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # simple_dir_with_file
        {
            "setup_dirs": ["default/foodir"],
            "setup_files": [os.path.join("default", "foodir", "foo")],
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], "default"), (["foo"], "default/bardir")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # organize_to_the_same_directory
        {
            "setup_dirs": ["default/bardir", "default/foodir"],
            "setup_files": [
                os.path.join("default", "foodir", "foo"),
                os.path.join("default", "bardir", "bar"),
                os.path.join(
                    "default",
                    "basefoo",
                ),
            ],
            "organize_map": {
                "foodir": "bin",
                "bardir": "bin",
                "basefoo": "bin/basefoo",
            },
            "expected": [
                (["bin"], "default"),
                (["bar", "basefoo", "foo"], "default/bin"),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # leading_slash_in_value
        {
            "setup_dirs": [],
            "setup_files": ["default/foo"],
            "organize_map": {"foo": "/bar"},
            "expected": [(["bar"], "default")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # overwrite_existing_file
        {
            "setup_dirs": [],
            "setup_files": ["default/foo", "default/bar"],
            "organize_map": {"foo": "bar"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo' to 'bar', but '\(default\)/bar' already exists.*"
            ),
            "expected_overwrite": [(["bar"], "default")],
        },
        # *_for_files
        {
            "setup_dirs": [],
            "setup_files": ["default/foo.conf", "default/bar.conf"],
            "organize_map": {"*.conf": "dir/"},
            "expected": [
                (["dir"], "default"),
                (["bar.conf", "foo.conf"], "default/dir"),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # *_for_files_with_non_dir_dst
        {
            "setup_dirs": [],
            "setup_files": ["default/foo.conf", "default/bar.conf"],
            "organize_map": {"*.conf": "dir"},
            "expected": errors.FileOrganizeError,
            "expected_message": r".*multiple files to be organized into '\(default\)/dir'.*",
            "expected_overwrite": None,
        },
        # *_for_directories
        {
            "setup_dirs": ["default/dir1", "default/dir2"],
            "setup_files": [
                os.path.join("default", "dir1", "foo"),
                os.path.join("default", "dir2", "bar"),
            ],
            "organize_map": {"dir*": "dir/"},
            "expected": [
                (["dir"], "default"),
                (["dir1", "dir2"], "default/dir"),
                (["foo"], os.path.join("default", "dir", "dir1")),
                (["bar"], os.path.join("default", "dir", "dir2")),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # combined_*_with_file
        {
            "setup_dirs": ["default/dir1", "default/dir2"],
            "setup_files": [
                os.path.join("default", "dir1", "foo"),
                os.path.join("default", "dir1", "bar"),
                os.path.join("default", "dir2", "bar"),
            ],
            "organize_map": {"dir*": "dir/", "dir1/bar": "."},
            "expected": [
                (["bar", "dir"], "default"),
                (["dir1", "dir2"], "default/dir"),
                (["foo"], os.path.join("default", "dir", "dir1")),
                (["bar"], os.path.join("default", "dir", "dir2")),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # *_into_dir
        {
            "setup_dirs": ["default/dir"],
            "setup_files": [
                os.path.join("default", "dir", "foo"),
                os.path.join("default", "dir", "bar"),
            ],
            "organize_map": {"dir/f*": "nested/dir/"},
            "expected": [
                (["dir", "nested"], "default"),
                (["bar"], "default/dir"),
                (["dir"], "default/nested"),
                (["foo"], os.path.join("default", "nested", "dir")),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
    ],
)
def test_organize(new_dir, data):
    base_dir = pathlib.Path(new_dir, "install")
    for partition in ["default", "mypart", "yourpart"]:
        (base_dir / partition).mkdir(parents=True, exist_ok=True)

    organize_and_assert(
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
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data["setup_dirs"],
        setup_files=data["setup_files"],
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data["expected_message"],
        expected_overwrite=data["expected_overwrite"],
        overwrite=True,
    )
