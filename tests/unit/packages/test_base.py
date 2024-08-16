# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2023 Canonical Ltd.
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
import sys
from pathlib import Path

import pytest
from craft_parts.packages import base
from craft_parts.packages.base import BaseRepository, DummyRepository


class TestBaseRepository:
    """Verify the base repository class."""

    def test_abstract_methods(self):
        assert BaseRepository.__abstractmethods__ == {
            "configure",
            "get_installed_packages",
            "get_package_libraries",
            "is_package_installed",
            "get_packages_for_source_type",
            "download_packages",
            "install_packages",
            "fetch_stage_packages",
            "refresh_packages_list",
            "unpack_stage_packages",
        }


class TestDummyRepository:
    """Verify the dummy repository implementation."""

    def test_methods_implemented(self):
        DummyRepository()

    def test_methods(self):
        assert DummyRepository.get_package_libraries("foo") == set()
        assert DummyRepository.get_packages_for_source_type("bar") == set()
        assert DummyRepository.install_packages([]) == []
        assert DummyRepository.is_package_installed("baz") is False
        assert DummyRepository.get_installed_packages() == []
        assert DummyRepository.fetch_stage_packages() == []


class TestPkgNameParts:
    """Check the extraction of package name parts."""

    def test_get_pkg_name_parts_name_only(self):
        name, version = base.get_pkg_name_parts("hello")
        assert name == "hello"
        assert version is None

    def test_get_pkg_name_parts_all(self):
        name, version = base.get_pkg_name_parts("hello:i386=2.10-1")
        assert name == "hello:i386"
        assert version == "2.10-1"

    def test_get_pkg_name_parts_no_arch(self):
        name, version = base.get_pkg_name_parts("hello=2.10-1")
        assert name == "hello"
        assert version == "2.10-1"


class TestOriginStagePackage:
    """Check extended attribute setting."""

    @pytest.fixture
    def test_file(self, new_homedir_path):
        # These tests don't work on tmpfs
        file_path = new_homedir_path / ".tests-xattr-test-file"
        file_path.touch()

        yield str(file_path)

        file_path.unlink()

    def test_read_origin_stage_package(self, test_file):
        if sys.platform == "linux":
            result = base.read_origin_stage_package(test_file)
            assert result is None
        else:
            with pytest.raises(RuntimeError):
                base.read_origin_stage_package(test_file)

    def test_write_origin_stage_package(self, test_file):
        package = "foo-1.0"
        if sys.platform == "linux":
            result = base.read_origin_stage_package(test_file)
            assert result is None

            base.write_origin_stage_package(test_file, package)
            result = base.read_origin_stage_package(test_file)
            assert result == package
        else:
            with pytest.raises(RuntimeError):
                base.write_origin_stage_package(test_file, package)

    @pytest.mark.usefixtures("new_homedir_path")
    def test_mark_origin_stage_package(self):
        test_dir = Path(".tests-xattr-test-dir")
        test_dir.mkdir()

        Path(test_dir / "foo").touch()
        Path(test_dir / "bar").touch()

        base.mark_origin_stage_package(str(test_dir), "package")
        assert base.read_origin_stage_package(str(test_dir / "foo")) == "package"
        assert base.read_origin_stage_package(str(test_dir / "bar")) == "package"
