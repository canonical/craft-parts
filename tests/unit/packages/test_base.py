# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

from craft_parts.packages import base
from craft_parts.packages.base import BaseRepository, DummyRepository


class TestBaseRepository:
    """Verify the base repository class."""

    def test_abstract_methods(self):
        assert BaseRepository.__abstractmethods__ == {  # type: ignore
            "configure",
            "get_installed_packages",
            "get_package_libraries",
            "is_package_installed",
            "get_packages_for_source_type",
            "install_build_packages",
            "fetch_stage_packages",
            "refresh_build_packages_list",
            "unpack_stage_packages",
        }


class TestDummyRepository:
    """Verify the dummy repository implementation."""

    def test_methods_implemented(self):
        DummyRepository()

    def test_methods(self):
        assert DummyRepository.get_package_libraries("foo") == set()
        assert DummyRepository.get_packages_for_source_type("bar") == set()
        assert DummyRepository.install_build_packages([]) == []
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


# TODO: add tests for mark_origin_stage_package()
