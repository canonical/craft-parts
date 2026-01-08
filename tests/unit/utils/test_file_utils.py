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
from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.permissions import Permissions
from craft_parts.utils import file_utils


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
        Path("foo/bar/baz").mkdir(parents=True)
        Path("1").touch()
        Path("foo", "2").touch()
        Path("foo", "bar", "3").touch()
        Path("foo", "bar", "baz", "4").touch()

    def test_link_file_to_file_raises(self):
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("1", "qux")
        assert raised.value.message == "'1' is not a directory"

    def test_link_file_into_directory(self):
        Path("qux").mkdir()
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("1", "qux")
        assert raised.value.message == "'1' is not a directory"

    def test_link_directory_to_directory(self):
        file_utils.link_or_copy_tree("foo", "qux")
        assert Path("qux", "2").is_file()
        assert Path("qux", "bar", "3").is_file()
        assert Path("qux", "bar", "baz", "4").is_file()

    def test_link_directory_overwrite_file_raises(self):
        Path("qux").touch()
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("foo", "qux")
        assert raised.value.message == (
            "cannot overwrite non-directory 'qux' with directory 'foo'"
        )

    def test_ignore(self):
        file_utils.link_or_copy_tree("foo/bar", "qux", ignore=lambda x, y: ["3"])
        assert not Path("qux", "3").is_file()
        assert Path("qux", "baz", "4").is_file()

    def test_link_subtree(self):
        file_utils.link_or_copy_tree("foo/bar", "qux")
        assert Path("qux", "3").is_file()
        assert Path("qux", "baz", "4").is_file()

    def test_link_symlink_to_file(self):
        # Create a symlink to a file
        Path("foo", "2-link").symlink_to("2")
        file_utils.link_or_copy_tree("foo", "qux")
        # Verify that the symlink remains a symlink
        link = Path("qux", "2-link")
        assert link.is_symlink()
        assert link.readlink() == Path("2")

    def test_link_symlink_to_dir(self):
        Path("foo", "bar-link").symlink_to("bar")
        file_utils.link_or_copy_tree("foo", "qux")

        # Verify that the symlink remains a symlink
        link = Path("qux", "bar-link")
        assert link.is_symlink()
        assert link.readlink() == Path("bar")


class TestLinkOrCopy:
    """Verify func:`link_or_copy` usage scenarios."""

    def setup_method(self):
        Path("foo/bar/baz").mkdir(parents=True)
        Path("1").touch()
        Path("foo", "2").touch()
        Path("foo", "bar", "3").touch()
        Path("foo", "bar", "baz", "4").touch()

    def test_link_file_soerror(self, mocker):
        orig_link = os.link

        def link_and_oserror(a, b, **kwargs):  # pylint: disable=unused-argument
            orig_link(a, b)
            raise OSError

        mocker.patch("os.link", side_effect=link_and_oserror)

        file_utils.link_or_copy("1", "foo/1")

    def test_copy_nested_file(self):
        file_utils.link_or_copy("foo/bar/baz/4", "foo2/bar/baz/4")
        assert Path("foo2/bar/baz/4").is_file()

    def test_destination_exists(self):
        Path("qux").mkdir()
        Path("qux", "2").touch()
        assert Path("foo/2").stat().st_ino != Path("qux/2").stat().st_ino

        file_utils.link_or_copy("foo/2", "qux/2")
        assert Path("foo/2").stat().st_ino == Path("qux/2").stat().st_ino

    def test_with_permissions(self, mock_chown):
        Path("foo/2").chmod(mode=0o644)

        permissions = [
            Permissions(path="foo/*", mode="755"),
            Permissions(path="foo/2", owner=1111, group=2222),
        ]

        Path("qux").mkdir()
        file_utils.link_or_copy("foo/2", "qux/2", permissions=permissions)

        # Check that the copied file has the correct permission bits and ownership
        assert stat.S_IMODE(Path("qux/2").stat().st_mode) == 0o755
        mock_call = mock_chown[Path("qux/2")]
        assert mock_call.owner == 1111
        assert mock_call.group == 2222

        # Check that the copied file is *not* a link
        assert Path("foo/2").stat().st_ino != Path("qux/2").stat().st_ino
        assert Path("qux/2").stat().st_nlink == 1


class TestCopy:
    """Verify func:`copy` usage scenarios."""

    def setup_method(self):
        Path("1").touch()

    def test_copy(self):
        file_utils.copy("1", "3")
        assert Path("3").is_file()

    def test_file_not_found(self):
        with pytest.raises(errors.CopyFileNotFound) as raised:
            file_utils.copy("2", "3")
        assert raised.value.name == "2"


class TestMove:
    """Verify func:`move` usage scenarios."""

    def test_move_simple(self):
        Path("foo").touch()
        foo_stat = Path("foo").stat()
        file_utils.move("foo", "bar")
        bar_stat = Path("bar").stat()

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

    @pytest.mark.skipif(os.geteuid() != 0, reason="requires root permissions")
    def test_move_chardev(self):
        os.mknod("foo", 0o750 | stat.S_IFCHR, os.makedev(1, 5))
        foo_stat = Path("foo").stat()
        file_utils.move("foo", "bar")
        bar_stat = Path("bar").stat()

        assert Path("foo").exists() is False
        assert Path("bar").exists()
        assert stat.S_ISCHR(bar_stat.st_mode)
        assert os.major(bar_stat.st_rdev) == 1
        assert os.minor(bar_stat.st_rdev) == 5
        assert TestMove._has_same_attributes(foo_stat, bar_stat)

    @pytest.mark.skipif(os.geteuid() != 0, reason="requires root permissions")
    def test_move_blockdev(self):
        os.mknod("foo", 0o750 | stat.S_IFBLK, os.makedev(7, 99))
        foo_stat = Path("foo").stat()
        file_utils.move("foo", "bar")
        bar_stat = Path("bar").stat()

        assert Path("foo").exists() is False
        assert Path("bar").exists()
        assert stat.S_ISBLK(bar_stat.st_mode)
        assert os.major(bar_stat.st_rdev) == 7
        assert os.minor(bar_stat.st_rdev) == 99
        assert TestMove._has_same_attributes(foo_stat, bar_stat)

    def test_move_fifo(self):
        os.mkfifo("foo")
        foo_stat = Path("foo").stat()
        file_utils.move("foo", "bar")
        bar_stat = Path("bar").stat()

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


def test_create_similar_directory_permissions(tmp_path, mock_chown):
    source = tmp_path / "source"
    source.mkdir()
    source.chmod(0o644)
    target = tmp_path / "target"

    permissions = [Permissions(mode="755", owner=1111, group=2222)]

    file_utils.create_similar_directory(source, target, permissions=permissions)

    assert stat.S_IMODE(Path(target).stat().st_mode) == 0o755
    mock_call = mock_chown[target]
    assert mock_call.owner == 1111
    assert mock_call.group == 2222
