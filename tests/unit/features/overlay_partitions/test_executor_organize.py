# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2026 Canonical Ltd.
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

# Although it's not explicitly used, randomize_iglob is used here as it's an auto-use
# fixture that checks that the order of an organize doesn't matter.
from tests.unit.executor.test_organize import (
    organize_and_assert,
    randomize_iglob,  # noqa: F401
)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_dirs": ["foo_dir"],
                "setup_symlinks": [
                    ("foo_link", "foo"),
                ],
                "organize_map": {},
                "expected": [(["foo", "foo_dir", "foo_link"], "")],
            },
            id="no-op",
        ),
        # simple_file
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "bar"},
            "expected": [(["bar"], "")],
        },
        # simple_dir_with_file
        {
            "setup_dirs": ["foodir"],
            "setup_files": [Path("foodir", "foo")],
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize into overlay
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "(overlay)/bar"},
            "expected": [([], ""), (["bar"], "../overlay_dir")],
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
        install_dirs={
            "default": Path(new_dir / "install"),
            "overlay": Path(new_dir / "overlay_dir"),
        },
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
        install_dirs={
            "default": Path(new_dir / "install"),
            "overlay": Path(new_dir / "overlay_dir"),
        },
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_dirs": ["foo_dir"],
                "setup_symlinks": [
                    ("foo_link", "foo"),
                ],
                "organize_map": {},
                "expected": [(["foo", "foo_dir", "foo_link"], "")],
            },
            id="no-op",
        ),
        pytest.param(
            # It's unclear whether this is intended behaviour. This test case was added
            # while working on ensuring organizing to the overlay would not error here
            # (as is needed for imagecraft). This test exists to ensure that we did not
            # change this behaviour without intending to do so, but we should examine
            # whether this behaviour deserves changing. See: ST172
            {
                "setup_files": ["foo"],
                "setup_symlinks": [],
                "organize_map": {"foo": "bar"},
                "expected": [(["bar"], "")],
                "expected_2": errors.FileOrganizeError,
                "expected_message_2": r".*trying to organize file 'foo' to 'bar', but 'bar' already exists.*",
            },
            id="organize-file-clash-with-previous",
        ),
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_symlinks": [],
                "organize_map": {"foo": "(overlay)/bar"},
                "expected": [(["bar"], "../overlay_dir")],
            },
            id="organize-file-to-overlay-rename",
        ),
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_symlinks": [],
                "organize_map": {"foo": "(overlay)/"},
                "expected": [(["foo"], "../overlay_dir")],
            },
            id="organize-file-to-overlay-dir",
        ),
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_dirs": ["bar"],
                "setup_symlinks": [],
                "organize_map": {"bar": "(overlay)/bar", "foo": "(overlay)/bar"},
                "expected": [
                    (["bar"], "../overlay_dir"),
                    (["foo"], "../overlay_dir/bar"),
                ],
            },
            id="organize-file-to-overlay-child",
        ),
        pytest.param(
            {
                "setup_files": ["file"],
                "setup_dirs": ["dir"],
                "setup_symlinks": [("link-to-file", "file"), ("link-to-dir", "dir")],
                "organize_map": {
                    "file": "(overlay)/file",
                    "link-to-file": "(overlay)/file",
                    "dir": "(overlay)/dir",
                    "link-to-dir": "(overlay)/dir",
                },
                "expected": [
                    (["dir", "file"], "../overlay_dir"),
                ],
            },
            id="organize-link-to-destination",
        ),
        pytest.param(
            {
                "setup_files": ["file"],
                "setup_dirs": ["dir"],
                "setup_symlinks": [
                    ("a-link-to-file", "file"),
                    ("a-link-to-dir", "dir"),
                ],
                "organize_map": {
                    "a-link-to-file": "(overlay)/file",
                    "file": "(overlay)/file",
                    "a-link-to-dir": "(overlay)/dir",
                    "dir": "(overlay)/dir",
                },
                "expected": [
                    (["dir", "file"], "../overlay_dir"),
                ],
            },
            id="organize-link-to-destination-link-first",
        ),
        pytest.param(
            {
                "setup_files": ["file", "dir/child-file"],
                "setup_dirs": ["dir"],
                "setup_symlinks": [
                    ("link-to-dir", "dir"),
                    ("link-to-file", "file"),
                    ("link-to-child-file", "dir/child-file"),
                ],
                "organize_map": {
                    "*": "(overlay)/",
                },
                "expected": [
                    (
                        [
                            "dir",
                            "file",
                            "link-to-child-file",
                            "link-to-dir",
                            "link-to-file",
                        ],
                        "../overlay_dir",
                    ),
                    (["child-file"], "../overlay_dir/dir"),
                ],
            },
            id="organize-all-to-overlay",
        ),
        pytest.param(
            {
                "setup_files": ["dir1/child", "dir2/child"],
                "setup_dirs": ["dir1", "dir2"],
                "organize_map": {
                    "dir1": "(overlay)/dir",
                    "dir2": "(overlay)/dir",
                },
                "expected": [
                    (["dir"], "../overlay_dir"),
                    (["child"], "../overlay_dir/dir"),
                ],
            },
            id="merge-dirs-in-overlay-success",
        ),
        pytest.param(
            {
                "setup_files": ["dir1/child", "dir2/child"],
                "setup_dirs": ["dir1", "dir2"],
                "organize_map": {
                    "dir*": "(overlay)/dir",
                },
                "expected": [
                    (["dir"], "../overlay_dir"),
                    (["child"], "../overlay_dir/dir"),
                ],
            },
            id="merge-dir-globs-in-overlay-success",
        ),
        pytest.param(
            {
                "setup_files": ["dir1/child1", "dir2/child2"],
                "setup_dirs": ["dir1", "dir2"],
                "organize_map": {
                    "dir1": "(overlay)/dir",
                    "dir2": "(overlay)/dir",
                },
                "expected": [
                    (["dir"], "../overlay_dir"),
                    (["child1", "child2"], "../overlay_dir/dir"),
                ],
            },
            id="merge-dirs-without-overlay-success",
        ),
    ],
)
def test_organize_no_overwrite_idempotent(tmp_path, data):
    organize_and_assert(
        tmp_path=tmp_path,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={
            "default": Path(tmp_path / "install"),
            "overlay": Path(tmp_path / "overlay_dir"),
            "build": Path(tmp_path / "build"),
        },
    )

    organize_and_assert(
        tmp_path=tmp_path,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data.get("expected_2", data["expected"]),
        expected_message=data.get("expected_message_2", data.get("expected_message")),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={
            "default": Path(tmp_path / "install"),
            "overlay": Path(tmp_path / "overlay_dir"),
            "build": Path(tmp_path / "build"),
        },
    )
