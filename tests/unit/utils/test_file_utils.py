# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pyfakefs.helpers
import pytest
from craft_parts import errors
from craft_parts.permissions import Permissions
from craft_parts.utils import file_utils
from craft_parts.utils.file_utils import get_path_differences
from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_pathlib import FakePathlibModule


@pytest.fixture(autouse=True)
def setup_module_fixture(new_dir):  # pylint: disable=unused-argument
    pass


@pytest.mark.parametrize(
    ("algo", "digest"),
    [
        ("md5", "9a0364b9e99bb480dd25e1f0284c8555"),
        ("sha1", "040f06fd774092478d450774f5ba30c5da78acc8"),
    ],
)
def test_calculate_hash(algo, digest):
    test_file = Path("test_file")
    test_file.write_text("content")
    assert file_utils.calculate_hash(test_file, algorithm=algo) == digest


def test_file_reader_iter():
    test_file = Path("test_file")
    test_file.write_text("content")
    gen = file_utils._file_reader_iter(test_file, block_size=4)
    assert list(gen) == [b"cont", b"ent"]


class TestLinkOrCopyTree:
    """Verify func:`link_or_copy_tree` usage scenarios."""

    def setup_method(self):
        os.makedirs("foo/bar/baz")  # noqa: PTH103
        open("1", "w").close()  # noqa: PTH123
        open(os.path.join("foo", "2"), "w").close()  # noqa: PTH118, PTH123
        open(os.path.join("foo", "bar", "3"), "w").close()  # noqa: PTH118, PTH123
        open(os.path.join("foo", "bar", "baz", "4"), "w").close()  # noqa: PTH118, PTH123

    def test_link_file_to_file_raises(self):
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("1", "qux")
        assert raised.value.message == "'1' is not a directory"

    def test_link_file_into_directory(self):
        os.mkdir("qux")  # noqa: PTH102
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("1", "qux")
        assert raised.value.message == "'1' is not a directory"

    def test_link_directory_to_directory(self):
        file_utils.link_or_copy_tree("foo", "qux")
        assert os.path.isfile(os.path.join("qux", "2"))  # noqa: PTH113, PTH118
        assert os.path.isfile(os.path.join("qux", "bar", "3"))  # noqa: PTH113, PTH118
        assert os.path.isfile(os.path.join("qux", "bar", "baz", "4"))  # noqa: PTH113, PTH118

    def test_link_directory_overwrite_file_raises(self):
        open("qux", "w").close()  # noqa: PTH123
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("foo", "qux")
        assert raised.value.message == (
            "cannot overwrite non-directory 'qux' with directory 'foo'"
        )

    def test_ignore(self):
        file_utils.link_or_copy_tree("foo/bar", "qux", ignore=lambda x, y: ["3"])
        assert not os.path.isfile(os.path.join("qux", "3"))  # noqa: PTH113, PTH118
        assert os.path.isfile(os.path.join("qux", "baz", "4"))  # noqa: PTH113, PTH118

    def test_link_subtree(self):
        file_utils.link_or_copy_tree("foo/bar", "qux")
        assert os.path.isfile(os.path.join("qux", "3"))  # noqa: PTH113, PTH118
        assert os.path.isfile(os.path.join("qux", "baz", "4"))  # noqa: PTH113, PTH118

    def test_link_symlink_to_file(self):
        # Create a symlink to a file
        pathlib.Path("foo", "2-link").symlink_to("2")
        file_utils.link_or_copy_tree("foo", "qux")
        # Verify that the symlink remains a symlink
        link = os.path.join("qux", "2-link")  # noqa: PTH118
        assert os.path.islink(link)  # noqa: PTH114
        assert os.readlink(link) == "2"  # noqa: PTH115

    def test_link_symlink_to_dir(self):
        pathlib.Path("foo", "bar-link").symlink_to("bar")
        file_utils.link_or_copy_tree("foo", "qux")

        # Verify that the symlink remains a symlink
        link = os.path.join("qux", "bar-link")  # noqa: PTH118
        assert os.path.islink(link)  # noqa: PTH114
        assert os.readlink(link) == "bar"  # noqa: PTH115


class TestLinkOrCopy:
    """Verify func:`link_or_copy` usage scenarios."""

    def setup_method(self):
        os.makedirs("foo/bar/baz")  # noqa: PTH103
        open("1", "w").close()  # noqa: PTH123
        open(os.path.join("foo", "2"), "w").close()  # noqa: PTH118, PTH123
        open(os.path.join("foo", "bar", "3"), "w").close()  # noqa: PTH118, PTH123
        open(os.path.join("foo", "bar", "baz", "4"), "w").close()  # noqa: PTH118, PTH123

    def test_link_file_soerror(self, mocker):
        orig_link = os.link

        def link_and_oserror(a, b, **kwargs):  # pylint: disable=unused-argument
            orig_link(a, b)
            raise OSError

        mocker.patch("os.link", side_effect=link_and_oserror)

        file_utils.link_or_copy("1", "foo/1")

    def test_copy_nested_file(self):
        file_utils.link_or_copy("foo/bar/baz/4", "foo2/bar/baz/4")
        assert os.path.isfile("foo2/bar/baz/4")  # noqa: PTH113

    def test_destination_exists(self):
        os.mkdir("qux")  # noqa: PTH102
        open(os.path.join("qux", "2"), "w").close()  # noqa: PTH118, PTH123
        assert os.stat("foo/2").st_ino != os.stat("qux/2").st_ino  # noqa: PTH116

        file_utils.link_or_copy("foo/2", "qux/2")
        assert os.stat("foo/2").st_ino == os.stat("qux/2").st_ino  # noqa: PTH116

    def test_with_permissions(self, mock_chown):
        os.chmod("foo/2", mode=0o644)  # noqa: PTH101

        permissions = [
            Permissions(path="foo/*", mode="755"),
            Permissions(path="foo/2", owner=1111, group=2222),
        ]

        os.mkdir("qux")  # noqa: PTH102
        file_utils.link_or_copy("foo/2", "qux/2", permissions=permissions)

        # Check that the copied file has the correct permission bits and ownership
        assert stat.S_IMODE(os.stat("qux/2").st_mode) == 0o755  # noqa: PTH116
        mock_call = mock_chown["qux/2"]
        assert mock_call.owner == 1111
        assert mock_call.group == 2222

        # Check that the copied file is *not* a link
        assert os.stat("foo/2").st_ino != os.stat("qux/2").st_ino  # noqa: PTH116
        assert os.stat("qux/2").st_nlink == 1  # noqa: PTH116


class TestCopy:
    """Verify func:`copy` usage scenarios."""

    def setup_method(self):
        open("1", "w").close()  # noqa: PTH123

    def test_copy(self):
        file_utils.copy("1", "3")
        assert os.path.isfile("3")  # noqa: PTH113

    def test_file_not_found(self):
        with pytest.raises(errors.CopyFileNotFound) as raised:
            file_utils.copy("2", "3")
        assert raised.value.name == "2"


class TestMove:
    """Verify func:`move` usage scenarios."""

    def test_move_simple(self):
        Path("foo").touch()
        foo_stat = os.stat("foo")  # noqa: PTH116
        file_utils.move("foo", "bar")
        bar_stat = os.stat("bar")  # noqa: PTH116

        assert Path("foo").exists() is False
        assert Path("bar").is_file()
        assert TestMove._has_same_attributes(foo_stat, bar_stat)
        assert foo_stat.st_ino == bar_stat.st_ino

    def test_move_symlink(self):
        Path("foo").symlink_to("baz")
        foo_stat = os.lstat("foo")
        file_utils.move("foo", "bar")
        bar_stat = os.lstat("bar")

        assert Path("foo").exists() is False
        assert Path("bar").is_symlink()
        assert Path("bar").readlink() == Path("baz")
        assert TestMove._has_same_attributes(foo_stat, bar_stat)

    @pytest.mark.requires_root
    def test_move_chardev(self):
        os.mknod("foo", 0o750 | stat.S_IFCHR, os.makedev(1, 5))
        foo_stat = os.stat("foo")  # noqa: PTH116
        file_utils.move("foo", "bar")
        bar_stat = os.stat("bar")  # noqa: PTH116

        assert Path("foo").exists() is False
        assert Path("bar").exists()
        assert stat.S_ISCHR(bar_stat.st_mode)
        assert os.major(bar_stat.st_rdev) == 1
        assert os.minor(bar_stat.st_rdev) == 5
        assert TestMove._has_same_attributes(foo_stat, bar_stat)

    @pytest.mark.requires_root
    def test_move_blockdev(self):
        os.mknod("foo", 0o750 | stat.S_IFBLK, os.makedev(7, 99))
        foo_stat = os.stat("foo")  # noqa: PTH116
        file_utils.move("foo", "bar")
        bar_stat = os.stat("bar")  # noqa: PTH116

        assert Path("foo").exists() is False
        assert Path("bar").exists()
        assert stat.S_ISBLK(bar_stat.st_mode)
        assert os.major(bar_stat.st_rdev) == 7
        assert os.minor(bar_stat.st_rdev) == 99
        assert TestMove._has_same_attributes(foo_stat, bar_stat)

    def test_move_fifo(self):
        os.mkfifo("foo")
        foo_stat = os.stat("foo")  # noqa: PTH116
        file_utils.move("foo", "bar")
        bar_stat = os.stat("bar")  # noqa: PTH116

        assert Path("foo").exists() is False
        assert Path("bar").exists()
        assert stat.S_ISFIFO(bar_stat.st_mode)
        assert TestMove._has_same_attributes(foo_stat, bar_stat)

    @staticmethod
    def _has_same_attributes(a: os.stat_result, b: os.stat_result) -> bool:
        return (
            a.st_mode == b.st_mode
            and a.st_uid == b.st_uid
            and a.st_gid == b.st_gid
            and a.st_mtime_ns == b.st_mtime_ns
        )


def _create_and_chown(
    path: pathlib.Path, creator: Callable[[], None], uid: int, gid: int
):
    creator()
    os.chown(path, uid, gid, follow_symlinks=False)


@pytest.mark.parametrize(
    ("setup_a", "setup_b", "expected"),
    [
        pytest.param(lambda a: None, lambda b: None, [], id="neither-exist"),
        pytest.param(lambda a: a.mkdir(), lambda b: None, [], id="a-dir"),
        pytest.param(lambda a: None, lambda b: b.touch(), [], id="b-file"),
        pytest.param(
            pathlib.Path.mkdir,
            pathlib.Path.mkdir,
            [],
            id="equivalent-directories",
        ),
        pytest.param(
            pathlib.Path.touch,
            pathlib.Path.touch,
            [],
            id="empty-files",
        ),
        pytest.param(
            lambda a: a.write_text("This file intentionally left blank."),
            lambda b: b.write_text("This file intentionally left blank."),
            [],
            id="texty-files",
        ),
        pytest.param(
            lambda a: a.write_bytes(b"\0" * 2**20),
            lambda b: b.write_bytes(b"\0" * 2**20),
            [],
            id="big-files",
        ),
        pytest.param(
            lambda a: a.symlink_to("/"),
            lambda b: b.symlink_to("/"),
            [],
            id="same-dir-links",
        ),
        pytest.param(
            lambda a: a.symlink_to("c"),
            lambda b: b.symlink_to("c"),
            [],
            id="same-broken-links",
        ),
        pytest.param(
            lambda a: a.symlink_to("a"),
            lambda b: b.symlink_to("a"),
            [],
            id="a-links",
        ),
        pytest.param(
            os.mkfifo,
            os.mkfifo,
            [],
            id="both-fifos",
        ),
        pytest.param(
            lambda a: os.mknod(a, device=stat.S_IFCHR),
            lambda a: os.mknod(a, device=stat.S_IFCHR),
            [],
            id="both-char-devices",
        ),
        pytest.param(
            lambda a: os.mknod(a, device=stat.S_IFCHR),
            lambda a: os.mknod(a, device=stat.S_IFCHR),
            [],
            id="both-block-devices",
        ),
        pytest.param(
            lambda a: a.mkdir(mode=0o700),
            lambda b: b.touch(mode=0o700),
            ["different types"],
            id="different-types",
        ),
        pytest.param(
            lambda a: a.mkdir(mode=0o700),
            lambda b: b.touch(mode=0o600),
            ["different types", "different modes (700 vs. 600)"],
            id="different-types-and-modes",
        ),
        pytest.param(
            lambda a: a.touch(mode=0o755),
            lambda b: b.touch(mode=0o600),
            ["different modes (755 vs. 600)"],
            id="different-modes",
        ),
        pytest.param(
            lambda a: a.write_bytes(b"\0" * 2**20),
            lambda b: b.write_bytes(b"\0" * 2**21),
            ["sizes differ"],
            id="big-files-different",
        ),
        pytest.param(
            lambda a: a.symlink_to("/tmp"),
            lambda b: b.symlink_to("/"),
            ["different link destinations ('/tmp' vs. '/')"],
            id="different-links",
        ),
        pytest.param(
            lambda a: a.symlink_to("b"),
            lambda b: b.symlink_to("a"),
            ["different link destinations ('b' vs. 'a')"],
            id="circular-links",
        ),
        pytest.param(
            lambda a: a.symlink_to("a"),
            lambda b: b.symlink_to("b"),
            ["different link destinations ('a' vs. 'b')"],
            id="self-links",
        ),
        pytest.param(
            lambda a: _create_and_chown(a, a.touch, 0, 0),
            lambda b: _create_and_chown(b, b.touch, 1, 0),
            ["different owners (0 vs. 1)"],
            marks=pytest.mark.requires_root,
            id="different-owners",
        ),
        pytest.param(
            lambda a: _create_and_chown(a, a.touch, 0, 0),
            lambda b: _create_and_chown(b, b.touch, 0, 1),
            ["different groups (0 vs. 1)"],
            marks=pytest.mark.requires_root,
            id="different-groups",
        ),
    ],
)
def test_get_path_differences(tmp_path, setup_a, setup_b, expected):
    a = tmp_path / "a"
    b = tmp_path / "b"
    setup_a(a)
    setup_b(b)

    actual = get_path_differences(a, b)

    assert actual == expected


def _create_tree(root: pathlib.Path, files: dict[pathlib.Path, dict[str, Any]]):
    for path, info in files.items():
        full = root / path
        if info.get("type") == "dir":
            full.mkdir(parents=True, exist_ok=True)
        elif info.get("type") == "chr":
            os.mknod(full, mode=stat.S_IFCHR | info.get("mode", 0o600))
        elif info.get("type") == "blk":
            os.mknod(full, mode=stat.S_IFBLK | info.get("mode", 0o600))
        else:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.touch()
        if "contents" in info:
            full.write_text(info["contents"])
        if "mode" in info:
            full.chmod(info["mode"])
        if "uid" in info or "gid" in info:
            os.chown(
                full, info.get("uid", -1), info.get("gid", -1), follow_symlinks=False
            )


def _check_tree_matches_description(
    root: pathlib.Path, files: dict[pathlib.Path, dict[str, Any]]
):
    for path, info in files.items():
        dest_path = root / path
        if "mode" in info:
            assert dest_path.stat().st_mode & 0o7777 == info["mode"]
        if info.get("type") == "dir":
            assert dest_path.is_dir()
        elif info.get("type") == "blk":
            assert dest_path.is_block_device()
        elif info.get("type") == "chr":
            assert dest_path.is_char_device()
        else:
            assert dest_path.read_text() == info.get("contents", "")


@pytest.mark.parametrize(
    ("source_files", "dest_files", "expected_conflicts"),
    [
        pytest.param({}, {}, {}, id="both-empty"),
        pytest.param(
            {
                "some/file/way/deep/in/a/directory/structure": {
                    "mode": 0o0700,
                    "contents": "This is a text file.",
                }
            },
            {},
            {},
            id="dest-empty",
        ),
        pytest.param(
            {
                "some/file/way/deep/in/a/directory/structure": {
                    "mode": 0o0700,
                    "contents": "This is a text file.",
                }
            },
            {
                "another/file/way/deep/in/a/directory/structure": {
                    "mode": 0o0700,
                    "contents": "This is a text file.",
                }
            },
            {},
            id="disjoint-trees",
        ),
        pytest.param(
            {"parent/child": {"type": "dir"}},
            {"parent": {"type": "dir"}},
            {},
            id="add-child-directory",
        ),
        pytest.param(
            {"parent/child": {}},
            {"parent": {"type": "dir"}},
            {},
            id="add-child-file",
        ),
        pytest.param(
            {"parent/source-child": {"type": "dir", "mode": 0o777}},
            {"parent/dest-child": {"type": "dir", "mode": 0o700}},
            {},
            id="distinct-child-dirs",
        ),
        pytest.param(
            {"parent/source-child": {"mode": 0o777}},
            {"parent/dest-child": {"mode": 0o700}},
            {},
            id="distinct-child-files",
        ),
        pytest.param(
            {"child": {"type": "dir", "mode": 0o777}},
            {"child": {"mode": 0o777}},
            {
                FakePathlibModule.PosixPath("child"): [
                    "source and destination are of different types"
                ]
            },
            id="type-mismatch",
        ),
        pytest.param(
            {
                "my-file": {
                    "mode": 0o0700,
                }
            },
            {
                "my-file": {
                    "mode": 0o0755,
                }
            },
            {
                FakePathlibModule.PosixPath("my-file"): [
                    "source and destination have different modes (source: 700, destination: 755)"
                ]
            },
            id="file-mode-mismatch",
        ),
        pytest.param(
            {
                "my-file": {
                    "contents": "This is a text file.",
                }
            },
            {
                "my-file": {
                    "contents": "This is a different text file.",
                }
            },
            {
                FakePathlibModule.PosixPath("my-file"): [
                    "source and destination file sizes differ"
                ]
            },
            id="file-sizes-mismatch",
        ),
        pytest.param(
            {
                "my-file": {
                    "contents": "This is a text file.",
                }
            },
            {
                "my-file": {
                    "contents": "This is a text file!",
                }
            },
            {
                FakePathlibModule.PosixPath("my-file"): [
                    "source and destination file contents differ"
                ]
            },
            id="file-contents-mismatch",
        ),
        pytest.param(
            {
                "my-dir": {
                    "type": "dir",
                    "mode": 0o0700,
                }
            },
            {
                "my-dir": {
                    "type": "dir",
                    "mode": 0o0755,
                }
            },
            {
                FakePathlibModule.PosixPath("my-dir"): [
                    "source and destination have different modes (source: 700, destination: 755)"
                ]
            },
            id="dir-mode-mismatch",
        ),
        pytest.param(
            {
                "my-dir": {"type": "dir", "uid": 123, "gid": 456},
                "my-file": {"uid": 123, "gid": 456},
            },
            {
                "my-dir": {"type": "dir", "uid": 234, "gid": 567},
                "my-file": {"uid": 234, "gid": 567},
            },
            {
                FakePathlibModule.PosixPath("my-dir"): [
                    "source and destination are owned by different uids (source: 123, destination: 234)",
                    "source and destination are owned by different gids (source: 456, destination: 567)",
                ],
                FakePathlibModule.PosixPath("my-file"): [
                    "source and destination are owned by different uids (source: 123, destination: 234)",
                    "source and destination are owned by different gids (source: 456, destination: 567)",
                ],
            },
            id="owner",
        ),
        pytest.param(
            {"my-chr": {"type": "chr", "mode": 0o600}},
            {"my-chr": {"mode": 0o600}},
            {
                FakePathlibModule.PosixPath("my-chr"): [
                    "source and destination are of different types"
                ]
            },
            id="character-device",
        ),
        pytest.param(
            {"my-blk": {"type": "blk", "mode": 0o600}},
            {"my-blk": {"type": "chr", "mode": 0o600}},
            {
                FakePathlibModule.PosixPath("my-blk"): [
                    "source and destination are of different types"
                ]
            },
            id="block-device",
        ),
    ],
)
def test_find_merge_conflicts(
    fs: FakeFilesystem,
    source_files: dict[pathlib.Path, dict[str, Any]],
    dest_files: dict[pathlib.Path, dict[str, Any]],
    expected_conflicts: dict[pathlib.Path, str],
):
    # Pretend to be root so we can create certain special files like character devices.
    pyfakefs.helpers.set_uid(0)

    source_root = pathlib.Path("/source")
    dest_root = pathlib.Path("/dest")
    source_root.mkdir()
    dest_root.mkdir()

    _create_tree(source_root, source_files)
    _create_tree(dest_root, dest_files)

    assert file_utils.find_merge_conflicts(source_root, dest_root) == expected_conflicts


@pytest.mark.parametrize(
    ("source_files", "dest_files"),
    [
        pytest.param({}, {}, id="both-empty"),
        pytest.param(
            {
                "some/file/way/deep/in/a/directory/structure": {
                    "mode": 0o0700,
                    "contents": "This is a text file.",
                }
            },
            {},
            id="dest-empty",
        ),
        pytest.param(
            {
                "some/file/way/deep/in/a/directory/structure": {
                    "mode": 0o0700,
                    "contents": "This is a text file.",
                }
            },
            {
                "another/file/way/deep/in/a/directory/structure": {
                    "mode": 0o0700,
                    "contents": "This is a text file.",
                }
            },
            id="disjoint-trees",
        ),
        pytest.param(
            {"parent/child": {"type": "dir"}},
            {"parent": {"type": "dir"}},
            id="add-child-directory",
        ),
        pytest.param(
            {"parent/child": {}},
            {"parent": {"type": "dir"}},
            id="add-child-file",
        ),
        pytest.param(
            {"parent/source-child": {"type": "dir", "mode": 0o777}},
            {"parent/dest-child": {"type": "dir", "mode": 0o700}},
            id="distinct-child-dirs",
        ),
        pytest.param(
            {"parent/source-child": {"mode": 0o777}},
            {"parent/dest-child": {"mode": 0o700}},
            id="distinct-child-files",
        ),
        pytest.param(
            {"block": {"type": "blk", "mode": 0o777}},
            {},
            id="block_device",
            marks=pytest.mark.requires_root,
        ),
        pytest.param(
            {"char": {"type": "chr", "mode": 0o777}},
            {},
            id="character_device",
            marks=pytest.mark.requires_root,
        ),
    ],
)
def test_merge_directories_success(
    tmp_path: pathlib.Path,
    source_files: dict[pathlib.Path, dict[str, Any]],
    dest_files: dict[pathlib.Path, dict[str, Any]],
):
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()

    _create_tree(source_root, source_files)
    _create_tree(dest_root, dest_files)

    file_utils.merge_directories(source_root, dest_root)

    _check_tree_matches_description(dest_root, source_files)
    _check_tree_matches_description(dest_root, dest_files)


@pytest.mark.parametrize(
    ("source_files", "dest_files", "match"),
    [
        pytest.param(
            {
                "my-file": {
                    "mode": 0o0700,
                }
            },
            {
                "my-file": {
                    "mode": 0o0755,
                }
            },
            "Could not merge directories. .+ have different types or modes.",
            id="file-mode-mismatch",
        ),
        pytest.param(
            {
                "my-file": {
                    "contents": "This is a text file.",
                }
            },
            {
                "my-file": {
                    "contents": "This is a different text file.",
                }
            },
            "Could not merge directories. .+ have different contents.",
            id="file-contents-mismatch",
        ),
        pytest.param(
            {
                "my-dir": {
                    "type": "dir",
                    "mode": 0o0700,
                }
            },
            {
                "my-dir": {
                    "type": "dir",
                    "mode": 0o0755,
                }
            },
            "Could not merge directories. .+ have different types or modes.",
            id="dir-mode-mismatch",
        ),
    ],
)
def test_merge_directories_error(
    tmp_path: pathlib.Path,
    source_files: dict[pathlib.Path, dict[str, Any]],
    dest_files: dict[pathlib.Path, dict[str, Any]],
    match: str,
):
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()

    _create_tree(source_root, source_files)
    _create_tree(dest_root, dest_files)

    with pytest.raises(OSError, match=match):
        file_utils.merge_directories(source_root, dest_root)


def test_create_similar_directory_permissions(tmp_path, mock_chown):
    source = tmp_path / "source"
    source.mkdir()
    os.chmod(source, 0o644)  # noqa: PTH101
    target = tmp_path / "target"

    permissions = [Permissions(mode="755", owner=1111, group=2222)]

    file_utils.create_similar_directory(source, target, permissions=permissions)

    assert stat.S_IMODE(os.stat(target).st_mode) == 0o755  # noqa: PTH116
    mock_call = mock_chown[target]
    assert mock_call.owner == 1111
    assert mock_call.group == 2222
