# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2019-2023 Canonical Ltd.
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
import sys
from pathlib import Path

import pytest
from craft_parts import errors, xattrs

from tests import linux_only


class TestXattrs:
    """Extended attribute tests."""

    @pytest.fixture
    def test_file(self):
        # These tests don't work on tmpfs
        file_path = Path(".tests-xattr-test-file")
        file_path.touch()

        yield str(file_path)

        file_path.unlink()

    def test_read_xattr(self, test_file):
        if sys.platform == "linux":
            result = xattrs.read_xattr(test_file, "attr")
            assert result is None
        else:
            with pytest.raises(RuntimeError) as raised:
                xattrs.read_xattr(test_file, "attr")
            assert str(raised.value) == "xattr support only available for Linux"

    def test_read_xattr_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            xattrs.read_xattr("I-DONT-EXIST", "attr")

    def test_write_xattr(self, test_file):
        value = "foo"
        if sys.platform == "linux":
            result = xattrs.read_xattr(test_file, "attr")
            assert result is None

            xattrs.write_xattr(test_file, "attr", value)
            result = xattrs.read_xattr(test_file, "attr")
            assert result == value
        else:
            with pytest.raises(RuntimeError) as raised:
                xattrs.write_xattr(test_file, "attr", value)
            assert str(raised.value) == "xattr support only available for Linux"

    def test_write_xattr_long(self, test_file):
        value = "a" * 100000
        if sys.platform == "linux":
            result = xattrs.read_xattr(test_file, "attr")
            assert result is None

            with pytest.raises(errors.XAttributeTooLong) as raised:
                xattrs.write_xattr(test_file, "attr", value)
            assert raised.value.key == "user.craft_parts.attr"
            assert raised.value.path == test_file

            result = xattrs.read_xattr(test_file, "attr")
            assert result is None
        else:
            with pytest.raises(RuntimeError) as raised:
                xattrs.write_xattr(test_file, "attr", value)
            assert str(raised.value) == "xattr support only available for Linux"

    @linux_only
    def test_symlink(self, test_file):
        test_symlink = test_file + "-symlink"
        try:
            os.symlink(test_file, test_symlink)

            result = xattrs.read_xattr(test_symlink, "attr")
            assert result is None

            xattrs.write_xattr(test_symlink, "attr", "value")
            result = xattrs.read_xattr(test_symlink, "attr")
            assert result is None
        finally:
            os.unlink(test_symlink)

    def test_read_non_linux(self, test_file, mocker):
        mocker.patch("sys.platform", return_value="win32")
        with pytest.raises(RuntimeError) as raised:
            xattrs.read_xattr(test_file, "attr")
        assert str(raised.value) == "xattr support only available for Linux"

    def test_write_non_linux(self, test_file, mocker):
        mocker.patch("sys.platform", return_value="win32")
        with pytest.raises(RuntimeError) as raised:
            xattrs.write_xattr(test_file, "attr", "value")
        assert str(raised.value) == "xattr support only available for Linux"
