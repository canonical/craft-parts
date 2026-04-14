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

import glob
import os
import random
import re
from pathlib import Path
from typing import Any, cast

import pytest
from craft_parts import errors
from craft_parts.executor import organize
from craft_parts.executor.organize import organize_files


@pytest.fixture(autouse=True, params=range(3))
def randomize_iglob(monkeypatch, request: pytest.FixtureRequest):
    """Replace the system's iglob function with a function that randomizes the glob.

    It also runs each test case 3 times to increase the chance of a test failing due
    to the random glob order.

    This will catch issues that occur due to order being important.
    """
    _ = request

    def random_glob(pathname: str, recursive: bool = False):
        result = glob.glob(pathname, recursive=recursive)  # noqa: PTH207
        random.shuffle(result)
        return result

    monkeypatch.setattr(organize, "iglob", random_glob)


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
        # trailing_slash_in_value
        {
            "setup_files": ["foo"],
            "organize_map": {"foo": "dir/"},
            "expected": [(["foo"], "dir")],
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
            id="glob-source-directories",
        ),
        # combined_*_with_file
        pytest.param(
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
            id="glob-source-directories-with-file",
        ),
        # *_into_dir
        pytest.param(
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
            id="glob-file-into-new-dir",
        ),
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
        build_files=data.get("build_files", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        check_copy=False,
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
    )

    # Verify that it can be organized again by overwriting
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        build_files=data.get("build_files", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        check_copy=False,
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
                os.path.join("dir1", "foo"),  # noqa: PTH118
                os.path.join("dir2", "foo"),  # noqa: PTH118
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
                os.path.join("dir1", "foo"),  # noqa: PTH118
                os.path.join("dir2", "foo"),  # noqa: PTH118
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
        build_files=data.get("build_files", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        check_copy=False,
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
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
    ],
)
def test_organize_no_overwrite_idempotent(new_dir, data):
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        build_files=data.get("build_files", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        check_copy=False,
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
    )

    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        build_files=data.get("build_files", []),
        organize_map=data["organize_map"],
        expected=data.get("expected_2", data["expected"]),
        expected_message=data.get("expected_message_2", data.get("expected_message")),
        expected_overwrite=data.get("expected_overwrite"),
        check_copy=False,
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
    )


def organize_and_assert(
    *,
    tmp_path: Path,
    setup_dirs,
    setup_files,
    setup_symlinks: list[tuple[str, str]],
    build_files,
    organize_map,
    expected: list[Any],
    expected_message,
    expected_overwrite,
    check_copy,
    overwrite,
    install_dirs,
):
    install_dir = Path(tmp_path / "install")
    install_dir.mkdir(parents=True, exist_ok=True)

    for directory in setup_dirs:
        (install_dir / directory).mkdir(exist_ok=True)

    paths_to_check: list[Path] = []

    for file_entry in setup_files:
        path = install_dir / file_entry
        paths_to_check.append(path)
        path.touch()

    if build_files:
        build_dir = Path(tmp_path / "build")
        build_dir.mkdir(parents=True, exist_ok=True)

        for file_entry in build_files:
            path = build_dir / file_entry
            paths_to_check.append(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

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
            dir_path = (install_dir / expect[1]).as_posix()
            dir_contents = os.listdir(dir_path)  # noqa: PTH208
            dir_contents.sort()
            assert dir_contents == expect[0]

        if check_copy:
            for path in paths_to_check:
                assert path.exists()
