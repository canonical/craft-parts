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
            "setup_files": ["foo", "bar", "baz", "qux1"],
            "organize_map": {
                "foo": "foo1",
                "qux": "(default)/qux1",
                "(default)/bar": "bar1",
                "(default)/baz": "(default)/baz1",
            },
            "expected": [(["bar1", "baz1", "foo1", "qux1"], "")],
        },
        # Raise an error for files sourced from a non-default partition
        {
            "organize_map": {
                "(mypart)/foo": "(our/special-part)/foo1",
            },
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*Cannot organize files from 'mypart' partition. "
                r"Files can only be organized from the 'default' partition.*"
            ),
        },
        # Files that should have the same name in two different partitions
        {
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
            "setup_files": ["foo", "bar"],
            "organize_map": {
                "foo": "baz",
                "bar": "(our/special-part)/baz",
            },
            "expected": [
                (["baz"], ""),
                (["baz"], "../partitions/our/special-part/parts/part-name/install"),
            ],
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
            "expected": [
                (["bin"], ""),
                (["bar", "basefoo", "foo"], "bin"),
            ],
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
        # overwrite_existing_file with partitions
        {
            "setup_files": ["foo", "bar"],
            "organize_map": {
                "(default)/foo": "(our/special-part)/bar",
                "(default)/bar": "(our/special-part)/bar",
            },
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file '\(default\)/foo' to '\(our/special-part\)/bar', "
                r"but '\(our/special-part\)/bar' already exists."
            ),
            "expected_overwrite": [
                (["bar"], "../partitions/our/special-part/parts/part-name/install")
            ],
        },
        # *_for_files
        {
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir/"},
            "expected": [
                (["dir"], ""),
                (["bar.conf", "foo.conf"], "dir"),
            ],
        },
        # *_for_files_with_non_dir_dst
        {
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "dir"},
            "expected": errors.FileOrganizeError,
            "expected_message": r".*multiple files to be organized into 'dir'.*",
        },
        # *_for_files_with_non_dir_dst with partitions
        {
            "setup_files": ["foo.conf", "bar.conf"],
            "organize_map": {"*.conf": "(our/special-part)/dir"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*multiple files to be organized into '\(our/special-part\)/dir'.*"
            ),
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
    install_dirs = {
        "default": new_dir / "install",
        "mypart": new_dir / "partitions/mypart/parts/part-name/install",
        "yourpart": new_dir / "partitions/yourpart/parts/part-name/install",
        "our/special-part": new_dir
        / "partitions/our/special-part/parts/part-name/install",
    }

    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs=install_dirs,
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
        install_dirs=install_dirs,
    )
