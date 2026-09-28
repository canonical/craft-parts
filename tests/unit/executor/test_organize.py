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

import os
import pathlib
import random
import re
from pathlib import Path
from typing import Any, cast

import pytest
from craft_parts import errors
from craft_parts.executor.organize import organize_files
from craft_parts.utils.partition_utils import BUILD_PARTITION


@pytest.fixture(autouse=True, params=range(6))
def randomize_globs(monkeypatch, request: pytest.FixtureRequest):
    """Replace the system's iglob function with a function that randomizes the glob.

    It also runs each test case multiple  times to increase the chance of a test failing
    due to the random glob order.

    This will catch issues that occur due to order being important.
    """

    rglob_old = Path.rglob
    glob_old = Path.glob

    def rglob(slf, pat: str, **_kwargs):
        result = list(rglob_old(slf, pat))
        random.shuffle(result)
        return result

    def glob(slf, pat: str, **_kwargs):
        result = list(glob_old(slf, pat))
        random.shuffle(result)
        return result

    if request.param != 0:  # In one case we use the real iglob.
        monkeypatch.setattr(pathlib.Path, "glob", glob)
        monkeypatch.setattr(pathlib.Path, "rglob", rglob)


@pytest.mark.parametrize(
    "data",
    [
        # simple_file
        {
            "setup_files": [Path("foo")],
            "organize_map": {"foo": "bar"},
            "expected": [(["bar"], "")],
        },
        # simple_dir_with_file
        {
            "setup_dirs": [Path("foodir")],
            "setup_files": [Path("foodir", "foo")],
            "organize_map": {"foodir": "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize_to_the_same_directory
        {
            "setup_dirs": [Path("bardir"), Path("foodir")],
            "setup_files": [
                Path("foodir", "foo"),
                Path("bardir", "bar"),
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
            "setup_files": [Path("foo")],
            "organize_map": {"foo": "/bar"},
            "expected": [(["bar"], "")],
        },
        # overwrite_existing_file
        {
            "setup_files": [Path("foo"), Path("bar")],
            "organize_map": {"foo": "bar"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo' to 'bar', but 'bar' already exists.*"
            ),
            "expected_overwrite": [(["bar"], "")],
        },
        # *_for_files
        {
            "setup_files": [Path("foo.conf"), Path("bar.conf")],
            "organize_map": {"*.conf": "dir/"},
            "expected": [(["dir"], ""), (["bar.conf", "foo.conf"], "dir")],
        },
        # *_for_files_with_non_dir_dst
        {
            "setup_files": [Path("foo.conf"), Path("bar.conf")],
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
            "setup_files": [Path("foo")],
            "organize_map": {"foo": "foo"},
            "expected": [(["foo"], "")],
        },
        # organize a file to itself with different path
        {
            "setup_dirs": [Path("bardir")],
            "setup_files": [Path("foo")],
            "organize_map": {"bardir/../foo": "foo"},
            "expected": [(["bardir", "foo"], "")],
        },
        # absolute source paths are rejected
        {
            "setup_files": ["foo"],
            "organize_map": {"/etc/apt": ""},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize from '/etc/apt', but source paths must stay within "
                r"the install directory.*"
            ),
        },
        # traversal outside install dir is rejected
        {
            "setup_files": ["foo"],
            "organize_map": {"../foo": "foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize from '\.\./foo', but source paths must stay within "
                r"the install directory.*"
            ),
        },
        # normalized traversal that stays within install dir is allowed
        {
            "setup_dirs": ["dir"],
            "setup_files": ["foo"],
            "organize_map": {"dir/../foo": "bar"},
            "expected": [(["bar", "dir"], "")],
        },
        # organize a set with a file to itself
        {
            "setup_dirs": [Path("bardir")],
            "setup_files": [Path("bardir/foo")],
            "organize_map": {"bardir/*": "bardir/"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize from subdirs to itself
        {
            "setup_dirs": [Path("foodir"), Path("foodir/bardir")],
            "setup_files": [Path("foodir/bardir/foo")],
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
            "setup_files": [Path("foo")],
            "setup_symlinks": [("foo-link", "foo")],
            "organize_map": {"foo-link": "foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo-link' to 'foo', but 'foo' already exists.*"
            ),
        },
        # organize a file under a symlinked directory to the symlink target
        {
            "setup_files": [Path("foo")],
            "setup_symlinks": [("bardir", ".")],
            "organize_map": {"bardir/foo": "foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'bardir/foo' to 'foo', but 'foo' already exists.*"
            ),
        },
        # organize a file under a symlinked directory to the symlink target
        {
            "setup_files": [Path("foo")],
            "setup_symlinks": [("bardir", ".")],
            "organize_map": {"foo": "bardir/foo"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize file 'foo' to 'bardir/foo', but 'bardir/foo' already exists.*"
            ),
        },
        # Organize 2 files to the same destination, one with a dir as a destination
        {
            "setup_dirs": [Path("dir1"), Path("dir2")],
            "setup_files": [
                Path("dir1", "foo"),
                Path("dir2", "foo"),
            ],
            "organize_map": {"dir1/foo": "dir/foo", "dir2/foo": "dir/"},
            "expected": errors.FileOrganizeError,
            "expected_message": (
                r".*trying to organize 'dir2/foo' to 'dir/', but 'dir/foo' already exists.*"
            ),
        },
        # Organize 2 files to the same destination, one referenced with a wildcard
        {
            "setup_dirs": [Path("dir1"), Path("dir2")],
            "setup_files": [
                Path("dir1", "foo"),
                Path("dir2", "foo"),
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
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={None: Path(new_dir / "install")},
    )

    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data.get("expected_2", data["expected"]),
        expected_message=data.get("expected_message_2", data.get("expected_message")),
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
    setup_build_dirs=None,
    setup_build_files=None,
    organize_map: dict[str, str],
    expected: list[Any],
    expected_message,
    expected_overwrite,
    overwrite,
    install_dirs,
):
    for dest_install_dir in install_dirs.values():
        Path(dest_install_dir).mkdir(parents=True, exist_ok=True)
    install_dir = Path(tmp_path / "install")
    install_dir.mkdir(parents=True, exist_ok=True)
    build_dir = Path(install_dirs.get(BUILD_PARTITION, tmp_path / "build_dir"))
    setup_build_dirs = setup_build_dirs or []
    setup_build_files = setup_build_files or []

    for directory in setup_dirs:
        (install_dir / directory).mkdir(parents=True, exist_ok=True)

    for file_entry in setup_files:
        file_path = install_dir / file_entry
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

    for directory in setup_build_dirs:
        (build_dir / directory).mkdir(parents=True, exist_ok=True)

    for file_entry in setup_build_files:
        file_path = build_dir / file_entry
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

    for symlink_entry, symlink_target in setup_symlinks:
        symlink_path = install_dir / symlink_entry
        if not symlink_path.is_symlink():
            symlink_path.symlink_to(symlink_target)

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


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {
                "setup_build_files": ["generated.txt"],
                "organize_map": {"(build)/generated.txt": "generated/generated.txt"},
                "expected": [
                    (["generated"], ""),
                    (["generated.txt"], "generated"),
                    (["generated.txt"], "../build_dir"),
                ],
            },
            id="build-file-creates-destination-directory",
        ),
        pytest.param(
            {
                "setup_dirs": ["target"],
                "setup_files": ["target/existing.txt"],
                "setup_build_dirs": ["generated"],
                "setup_build_files": ["generated/new.txt"],
                "organize_map": {"(build)/generated": "target"},
                "expected": [
                    (["target"], ""),
                    (["existing.txt", "new.txt"], "target"),
                    (["generated"], "../build_dir"),
                    (["new.txt"], "../build_dir/generated"),
                ],
            },
            id="build-explicit-directory-merges-into-target",
        ),
        pytest.param(
            {
                "setup_dirs": ["target"],
                "setup_build_dirs": ["generated-a", "generated-b"],
                "setup_build_files": [
                    "generated-a/a.txt",
                    "generated-b/b.txt",
                ],
                "organize_map": {"(build)/generated-*": "target"},
                "expected": [
                    (["target"], ""),
                    (["generated-a", "generated-b"], "target"),
                    (["a.txt"], "target/generated-a"),
                    (["b.txt"], "target/generated-b"),
                    (["generated-a", "generated-b"], "../build_dir"),
                    (["a.txt"], "../build_dir/generated-a"),
                    (["b.txt"], "../build_dir/generated-b"),
                ],
            },
            id="build-glob-directories-nest-in-existing-target",
        ),
    ],
)
def test_organize_from_build(data, new_dir):
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=[],
        setup_build_dirs=data.get("setup_build_dirs", []),
        setup_build_files=data.get("setup_build_files", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=None,
        expected_overwrite=None,
        overwrite=False,
        install_dirs={
            None: Path(new_dir / "install"),
            BUILD_PARTITION: Path(new_dir / "build_dir"),
        },
    )
