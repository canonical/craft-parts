# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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

import pytest
from craft_parts import errors

from tests.unit.executor.test_organize import organize_and_assert


@pytest.mark.parametrize(
    "data",
    [
        # Files in the default partition
        {
            "setup_dirs": [],
            "setup_files": ["foo", "bar", "baz", "qux1"],
            "organize_map": {
                "foo": "foo1",
                "qux": "(default)/qux1",
                "(default)/bar": "bar1",
                "(default)/baz": "(default)/baz1",
            },
            "expected": [(["bar1", "baz1", "foo1", "qux1"], "")],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # Raise an error for files sourced from a non-default partition
        {
            "setup_dirs": [],
            "setup_files": [],
            "organize_map": {
                "(mypart)/foo": "(our/special-part)/foo1",
            },
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*Cannot organize files from 'mypart' partition. "
                r"Files can only be organized from the 'default' partition.*"
            ),
            "expected_overwrite": None,
        },
        # Files that should have the same name in two different partitions
        {
            "setup_dirs": [],
            "setup_files": ["foo", "bar"],
            "organize_map": {"foo": "baz", "bar": "(mypart)/baz"},
            "expected": [
                (["baz"], ""),
                (["baz"], "../partitions/mypart/parts/part-name/install"),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
        # Files that should have the same name in two different partitions where one is
        # a namespaced partition
        {
            "setup_dirs": [],
            "setup_files": ["foo", "bar"],
            "organize_map": {
                "foo": "baz",
                "bar": "(our/special-part)/baz",
            },
            "expected": [
                (["baz"], ""),
                (["baz"], "../partitions/our/special-part/parts/part-name/install"),
            ],
            "expected_message": None,
            "expected_overwrite": None,
        },
        ## simple_dir_with_file
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
            "expected": [
                (["bin"], ""),
                (["bar", "basefoo", "foo"], "bin"),
            ],
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
        # overwrite_existing_file with partitions
        {
            "setup_dirs": [],
            "setup_files": ["foo", "bar"],
            "organize_map": {
                "(default)/foo": "(our/special-part)/bar",
                "(default)/bar": "(our/special-part)/bar",
            },
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file '\(default\)/foo' to '\(our/special-part\)/bar', "
                r"but 'partitions/our/special-part/parts/part-name/install/bar' already exists."
            ),
            "expected_overwrite": [
                (["bar"], "../partitions/our/special-part/parts/part-name/install")
            ],
        },
        # *_for_files
        {
            "setup_dirs": [],
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir/"},
            "expected": [
                (["dir"], ""),
                (["bar.conf", "foo.conf"], "dir"),
            ],
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
        # *_for_files_with_non_dir_dst with partitions
        {
            "setup_dirs": [],
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "(our/special-part)/dir"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*multiple files to be organized into "
                r"'partitions/our/special-part/parts/part-name/install/dir'.*"
            ),
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
