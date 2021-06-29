# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2019-2021 Canonical Ltd.
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

import contextlib
import os
import sys

import pytest

from craft_parts import errors, xattrs


class TestXattrs:
    """Extended attribute tests."""

    def setup_method(self):
        # These tests don't work on tmpfs
        self._test_file = (  # pylint: disable=attribute-defined-outside-init
            ".tests-xattr-test-file"
        )

        with contextlib.suppress(FileNotFoundError):
            os.remove(self._test_file)

        open(self._test_file, "w").close()

    def teardown_method(self):
        with contextlib.suppress(FileNotFoundError):
            os.remove(self._test_file)
            os.remove(self._test_file + "-symlink")

    def test_read_origin_stage_package(self):
        if sys.platform == "linux":
            result = xattrs.read_origin_stage_package(self._test_file)
            assert result is None
        else:
            with pytest.raises(RuntimeError):
                xattrs.read_origin_stage_package(self._test_file)

    def test_write_origin_stage_package(self):
        package = "foo-1.0"
        if sys.platform == "linux":
            result = xattrs.read_origin_stage_package(self._test_file)
            assert result is None

            xattrs.write_origin_stage_package(self._test_file, package)
            result = xattrs.read_origin_stage_package(self._test_file)
            assert result == package
        else:
            with pytest.raises(RuntimeError):
                xattrs.write_origin_stage_package(self._test_file, package)

    def test_write_origin_stage_package_long(self):
        package = "a" * 100000
        if sys.platform == "linux":
            result = xattrs.read_origin_stage_package(self._test_file)
            assert result is None

            with pytest.raises(errors.XAttributeTooLong) as raised:
                xattrs.write_origin_stage_package(self._test_file, package)
            assert raised.value.key == "user.craft_parts.origin_stage_package"
            assert raised.value.path == self._test_file

            result = xattrs.read_origin_stage_package(self._test_file)
            assert result is None
        else:
            with pytest.raises(RuntimeError) as raised:
                xattrs.write_origin_stage_package(self._test_file, package)
            assert str(raised.value) == "xattr support only available for Linux"

    def test_symlink(self):
        test_symlink = self._test_file + "-symlink"
        os.symlink(self._test_file, test_symlink)

        if sys.platform != "linux":
            return

        result = xattrs._read_xattr(test_symlink, "attr")
        assert result is None

        xattrs._write_xattr(test_symlink, "attr", "value")
        result = xattrs._read_xattr(test_symlink, "attr")
        assert result is None

    def test_read_non_linux(self, mocker):
        mocker.patch("sys.platform", return_value="win32")
        with pytest.raises(RuntimeError):
            xattrs._read_xattr(self._test_file, "attr")

    def test_write_non_linux(self, mocker):
        mocker.patch("sys.platform", return_value="win32")
        with pytest.raises(RuntimeError):
            xattrs._write_xattr(self._test_file, "attr", "value")
