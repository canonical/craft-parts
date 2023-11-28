# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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
        os.makedirs("foo/bar/baz")
        open("1", "w").close()
        open(os.path.join("foo", "2"), "w").close()
        open(os.path.join("foo", "bar", "3"), "w").close()
        open(os.path.join("foo", "bar", "baz", "4"), "w").close()

    def test_link_file_to_file_raises(self):
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("1", "qux")
        assert raised.value.message == "'1' is not a directory"

    def test_link_file_into_directory(self):
        os.mkdir("qux")
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("1", "qux")
        assert raised.value.message == "'1' is not a directory"

    def test_link_directory_to_directory(self):
        file_utils.link_or_copy_tree("foo", "qux")
        assert os.path.isfile(os.path.join("qux", "2"))
        assert os.path.isfile(os.path.join("qux", "bar", "3"))
        assert os.path.isfile(os.path.join("qux", "bar", "baz", "4"))

    def test_link_directory_overwrite_file_raises(self):
        open("qux", "w").close()
        with pytest.raises(errors.CopyTreeError) as raised:
            file_utils.link_or_copy_tree("foo", "qux")
        assert raised.value.message == (
            "cannot overwrite non-directory 'qux' with directory 'foo'"
        )

    def test_ignore(self):
        file_utils.link_or_copy_tree("foo/bar", "qux", ignore=lambda x, y: ["3"])
        assert not os.path.isfile(os.path.join("qux", "3"))
        assert os.path.isfile(os.path.join("qux", "baz", "4"))

    def test_link_subtree(self):
        file_utils.link_or_copy_tree("foo/bar", "qux")
        assert os.path.isfile(os.path.join("qux", "3"))
        assert os.path.isfile(os.path.join("qux", "baz", "4"))

    def test_link_symlink_to_file(self):
        # Create a symlink to a file
        os.symlink("2", os.path.join("foo", "2-link"))
        file_utils.link_or_copy_tree("foo", "qux")
        # Verify that the symlink remains a symlink
        link = os.path.join("qux", "2-link")
        assert os.path.islink(link)
        assert os.readlink(link) == "2"

    def test_link_symlink_to_dir(self):
        os.symlink("bar", os.path.join("foo", "bar-link"))
        file_utils.link_or_copy_tree("foo", "qux")

        # Verify that the symlink remains a symlink
        link = os.path.join("qux", "bar-link")
        assert os.path.islink(link)
        assert os.readlink(link) == "bar"


class TestLinkOrCopy:
    """Verify func:`link_or_copy` usage scenarios."""

    def setup_method(self):
        os.makedirs("foo/bar/baz")
        open("1", "w").close()
        open(os.path.join("foo", "2"), "w").close()
        open(os.path.join("foo", "bar", "3"), "w").close()
        open(os.path.join("foo", "bar", "baz", "4"), "w").close()

    def test_link_file_soerror(self, mocker):
        orig_link = os.link

        def link_and_oserror(a, b, **kwargs):  # pylint: disable=unused-argument
            orig_link(a, b)
            raise OSError

        mocker.patch("os.link", side_effect=link_and_oserror)

        file_utils.link_or_copy("1", "foo/1")

    def test_copy_nested_file(self):
        file_utils.link_or_copy("foo/bar/baz/4", "foo2/bar/baz/4")
        assert os.path.isfile("foo2/bar/baz/4")

    def test_destination_exists(self):
        os.mkdir("qux")
        open(os.path.join("qux", "2"), "w").close()
        assert os.stat("foo/2").st_ino != os.stat("qux/2").st_ino

        file_utils.link_or_copy("foo/2", "qux/2")
        assert os.stat("foo/2").st_ino == os.stat("qux/2").st_ino

    def test_with_permissions(self, mock_chown):
        os.chmod("foo/2", mode=0o644)

        permissions = [
            Permissions(path="foo/*", mode="755"),
            Permissions(path="foo/2", owner=1111, group=2222),
        ]

        os.mkdir("qux")
        file_utils.link_or_copy("foo/2", "qux/2", permissions=permissions)

        # Check that the copied file has the correct permission bits and ownership
        assert stat.S_IMODE(os.stat("qux/2").st_mode) == 0o755
        mock_call = mock_chown["qux/2"]
        assert mock_call.owner == 1111
        assert mock_call.group == 2222

        # Check that the copied file is *not* a link
        assert os.stat("foo/2").st_ino != os.stat("qux/2").st_ino
        assert os.stat("qux/2").st_nlink == 1


class TestCopy:
    """Verify func:`copy` usage scenarios."""

    def setup_method(self):
        open("1", "w").close()

    def test_copy(self):
        file_utils.copy("1", "3")
        assert os.path.isfile("3")

    def test_file_not_found(self):
        with pytest.raises(errors.CopyFileNotFound) as raised:
            file_utils.copy("2", "3")
        assert raised.value.name == "2"


# TODO: test NonBlockingRWFifo


def test_create_similar_directory_permissions(tmp_path, mock_chown):
    source = tmp_path / "source"
    source.mkdir()
    os.chmod(source, 0o644)
    target = tmp_path / "target"

    permissions = [Permissions(mode="755", owner=1111, group=2222)]

    file_utils.create_similar_directory(source, target, permissions=permissions)

    assert stat.S_IMODE(os.stat(target).st_mode) == 0o755
    mock_call = mock_chown[target]
    assert mock_call.owner == 1111
    assert mock_call.group == 2222
