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
            "setup_files": [os.path.join("foodir", "foo")],  # noqa: PTH118
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize_to_the_same_directory
        {
            "setup_dirs": ["bardir", "foodir"],
            "setup_files": [
                os.path.join("foodir", "foo"),  # noqa: PTH118
                os.path.join("bardir", "bar"),  # noqa: PTH118
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
        # overwrite existing (identical) file
        {
            "setup_files": ["foo", "bar"],
            "organize_map": {"foo": "bar"},
            # "expected": errors.FileOrganizeError,
            # "expected_message": (
            #     r".*trying to organize file 'foo' to 'bar', but 'bar' already exists.*"
            # ),
            "expected": [(["bar"], "")],
        },
        # overwrite existing (different) file
        {
            "setup_files": ["foo", "bar"],
            "setup_files_contents": {"bar": "not empty, unlike foo"},
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
        pytest.param(
            {
                "setup_dirs": ["dir1", "dir2"],
                "setup_files": [
                    os.path.join("dir1", "foo"),  # noqa: PTH118
                    os.path.join("dir2", "bar"),  # noqa: PTH118
                ],
                "organize_map": {"dir*": "dir/"},
                "expected": [
                    (["dir"], ""),
                    (["dir1", "dir2"], "dir"),
                    (["foo"], os.path.join("dir", "dir1")),  # noqa: PTH118
                    (["bar"], os.path.join("dir", "dir2")),  # noqa: PTH118
                ],
            },
            id="glob-dir-name",
        ),
        # combined_*_with_file
        {
            "setup_dirs": ["dir1", "dir2"],
            "setup_files": [
                os.path.join("dir1", "foo"),  # noqa: PTH118
                os.path.join("dir1", "bar"),  # noqa: PTH118
                os.path.join("dir2", "bar"),  # noqa: PTH118
            ],
            "organize_map": {"dir*": "dir/", "dir1/bar": "."},
            "expected": [
                (["bar", "dir"], ""),
                (["dir1", "dir2"], "dir"),
                (["foo"], os.path.join("dir", "dir1")),  # noqa: PTH118
                (["bar"], os.path.join("dir", "dir2")),  # noqa: PTH118
            ],
        },
        # *_into_dir
        {
            "setup_dirs": ["dir"],
            "setup_files": [
                os.path.join("dir", "foo"),  # noqa: PTH118
                os.path.join("dir", "bar"),  # noqa: PTH118
            ],
            "organize_map": {"dir/f*": "nested/dir/"},
            "expected": [
                (["dir", "nested"], ""),
                (["bar"], "dir"),
                (["dir"], "nested"),
                (["foo"], os.path.join("nested", "dir")),  # noqa: PTH118
            ],
        },
        # organize a file to itself
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "foo"},
            "expected": [(["foo"], "")],
        },
        # organize a file to itself with different path
        pytest.param(
            {
                "setup_dirs": ["bardir"],
                "setup_files": ["foo"],
                "organize_map": {"bardir/../foo": "foo"},
                "expected": [(["bardir", "foo"], "")],
            },
            id="different-path",
        ),
        # organize a set with a file to itself
        pytest.param(
            {
                "setup_dirs": ["bardir"],
                "setup_files": ["bardir/foo"],
                "organize_map": {"bardir/*": "bardir/"},
                "expected": [(["bardir"], ""), (["foo"], "bardir")],
            },
            id="organize-to-self",
        ),
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
        setup_files_contents=data.get("setup_files_contents", {}),
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
        setup_files_contents=data.get("setup_files_contents", {}),
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_symlinks": [("foo-link", "foo")],
                "organize_map": {"foo-link": "foo"},
                "expected": [(["foo"], "")],
            },
            id="organize-symlink-to-target",
        ),
        pytest.param(
            {
                "setup_files": ["foo"],
                "setup_symlinks": [("foo-link", "foo")],
                "organize_map": {"foo": "foo-link"},
                "expected": [(["foo-link"], "")],
            },
            id="organize-target-to-symlink",
        ),
        # organize a file under a symlinked directory to the symlink target
        {
            "setup_files": ["foo"],
            "setup_symlinks": [("bardir", ".")],
            "organize_map": {"bardir/foo": "foo"},
            "expected": [
                (["bardir", "foo"], ""),
                (["bardir", "foo"], "bardir"),
            ],
        },
        # organize a file under a symlinked directory to the symlink target
        {
            "setup_files": ["foo"],
            "setup_symlinks": [("bardir", ".")],
            "organize_map": {"foo": "bardir/foo"},
            "expected": [
                (["bardir", "foo"], ""),
                (["bardir", "foo"], "bardir"),
            ],
        },
        # Organize 2 files to the same destination, one with a dir as a destination
        # but these files are the same.
        pytest.param(
            {
                "setup_dirs": ["dir1", "dir2"],
                "setup_files": [
                    os.path.join("dir1", "foo"),  # noqa: PTH118
                    os.path.join("dir2", "foo"),  # noqa: PTH118
                ],
                "organize_map": {"dir1/foo": "dir/foo", "dir2/foo": "dir/"},
                "expected": [(["dir", "dir1", "dir2"], ""), (["foo"], "dir")],
            },
            id="identical-files-same-destination",
        ),
        # Organize 2 files to the same destination, one with a dir as a destination
        # but these files differ.
        pytest.param(
            {
                "setup_dirs": ["dir1", "dir2"],
                "setup_files": [
                    os.path.join("dir1", "foo"),  # noqa: PTH118
                    os.path.join("dir2", "foo"),  # noqa: PTH118
                ],
                "setup_files_contents": {"dir1/foo": "I am not empty"},
                "organize_map": {"dir1/foo": "dir/foo", "dir2/foo": "dir/"},
                "expected": errors.FileOrganizeError,
                "expected_message": (
                    r".*trying to organize 'dir2/foo' to 'dir/', but 'dir/foo' already exists.*"
                ),
            },
            id="different-contents-same-destination",
        ),
        # Organize 2 identical files to the same destination, one referenced with a wildcard
        pytest.param(
            {
                "setup_dirs": ["dir1", "dir2"],
                "setup_files": [
                    os.path.join("dir1", "foo"),  # noqa: PTH118
                    os.path.join("dir2", "foo"),  # noqa: PTH118
                ],
                "organize_map": {"dir1/foo": "dir/foo", "dir2/*": "dir/"},
                "expected": [(["dir", "dir1", "dir2"], ""), (["foo"], "dir")],
            },
            id="identical-files-same-destination-wildcard",
        ),
        # Organize 2 different files to the same destination, one referenced with a wildcard
        pytest.param(
            {
                "setup_dirs": ["dir1", "dir2"],
                "setup_files": [
                    os.path.join("dir1", "foo"),  # noqa: PTH118
                    os.path.join("dir2", "foo"),  # noqa: PTH118
                ],
                "setup_files_contents": {"dir1/foo": "I am not empty"},
                "organize_map": {"dir1/foo": "dir/foo", "dir2/*": "dir/"},
                "expected": errors.FileOrganizeError,
                "expected_message_first": (
                    r".*trying to organize 'dir2/\*' to 'dir/', but 'dir/foo' already exists.*"
                ),
                "expected_message_second": (
                    r".*trying to organize file 'dir1/foo' to 'dir/foo', but 'dir/foo' already exists.*"
                ),
            },
            id="different-files-same-destination-wildcard",
        ),
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
        expected_message=data.get(
            "expected_message_first", data.get("expected_message")
        ),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
        setup_files_contents=data.get("setup_files_contents", {}),
    )

    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get(
            "expected_message_second", data.get("expected_message")
        ),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
        setup_files_contents=data.get("setup_files_contents", {}),
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(  # Incorrect but https://github.com/canonical/craft-parts/issues/1488
            {
                "setup_files": ["new_file"],
                "organize_map": {
                    "new_file": "existing_file",
                },
                "expected": errors.FileOrganizeError,
                "expected_message": (
                    r".*trying to organize file 'new_file' to 'existing_file', but 'existing_file' already exists."
                ),
            },
            id="existing-file",
        ),
        pytest.param(
            {
                "setup_dirs": ["new_dir"],
                "organize_map": {
                    "new_dir": "existing_dir",
                },
                "expected": errors.FileOrganizeError,
                "expected_message": (
                    r".*trying to organize directory 'new_dir' to 'existing_dir', but 'existing_dir' already exists and source and destination have different modes \(source: 775, destination: 1411\)."
                ),
            },
            id="existing-dir",
        ),
        pytest.param(
            {
                "setup_symlinks": [("new_link", "existing_file")],
                "organize_map": {
                    "new_link": "existing_link",
                },
                "expected": errors.FileOrganizeError,
                "expected_message": (
                    r".*trying to organize file 'new_link' to 'existing_link', but 'existing_link' already exists."
                ),
            },
            id="existing-link",
        ),
    ],
)
def test_organize_no_overwrite_existing(new_dir, data):
    install_dir = Path(new_dir / "install")
    (install_dir / "existing_dir").mkdir(mode=777, parents=True)
    (install_dir / "existing_file").touch(mode=666)
    (install_dir / "existing_link").symlink_to("existing_file")

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
    setup_files_contents: dict[str, str] = {},
):
    install_dir = Path(tmp_path / "install")
    install_dir.mkdir(parents=True, exist_ok=True)

    for directory in setup_dirs:
        (install_dir / directory).mkdir(exist_ok=True)

    for file_entry in setup_files:
        (install_dir / file_entry).touch()

    for file, contents in setup_files_contents.items():
        (install_dir / file).write_text(contents)

    for symlink_entry, symlink_target in setup_symlinks:
        symlink_path = install_dir / symlink_entry
        if not symlink_path.is_symlink():
            if symlink_path.exists():
                symlink_path.unlink()
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
            dir_path = (install_dir / expect[1]).resolve().as_posix()
            dir_contents = os.listdir(dir_path)  # noqa: PTH208
            dir_contents.sort()
            assert dir_contents == expect[0]
