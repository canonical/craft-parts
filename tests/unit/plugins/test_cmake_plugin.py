# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2022 Canonical Ltd.
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

from pathlib import Path

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.cmake_plugin import CMakePlugin


@pytest.fixture
def setup_method_fixture():
    def _setup_method_fixture(new_dir, properties=None):
        if properties is None:
            properties = {}
        properties["source"] = "."
        plugin_properties = CMakePlugin.properties_class.unmarshal(properties)
        part = Part("foo", {})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        project_info._parallel_build_count = 42

        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("install/dir")

        return CMakePlugin(properties=plugin_properties, part_info=part_info)

    return _setup_method_fixture


class TestPluginCMakePlugin:
    """CMake plugin tests."""

    def test_get_build_snaps(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)
        assert plugin.get_build_snaps() == set()

    def test_get_build_packages_default(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)
        assert plugin.get_build_packages() == {
            "gcc",
            "cmake",
        }

    def test_get_build_packages_ninja(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir, properties={"cmake-generator": "Ninja"})

        assert plugin.get_build_packages() == {
            "gcc",
            "cmake",
            "ninja-build",
        }

    def test_get_build_packages_unix_makefiles(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(
            new_dir, properties={"cmake-generator": "Unix Makefiles"}
        )

        assert plugin.get_build_packages() == {
            "gcc",
            "cmake",
        }

    def test_get_build_environment(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_build_environment() == {
            "CMAKE_PREFIX_PATH": f"{str(new_dir)}/stage"
        }

    def test_get_build_commands_default(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_build_commands() == [
            f'cmake "{plugin._part_info.part_src_dir}" -G "Unix Makefiles"',
            f"cmake --build . -- -j{plugin._part_info.parallel_build_count}",
            (
                f'DESTDIR="{plugin._part_info.part_install_dir}" '
                "cmake --build . --target install"
            ),
        ]

    def test_get_build_commands_ninja(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir, properties={"cmake-generator": "Ninja"})

        assert plugin.get_build_commands() == [
            f'cmake "{plugin._part_info.part_src_dir}" -G "Ninja"',
            f"cmake --build . -- -j{plugin._part_info.parallel_build_count}",
            (
                f'DESTDIR="{plugin._part_info.part_install_dir}" '
                "cmake --build . --target install"
            ),
        ]

    def test_get_build_commands_unix_makefiles(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(
            new_dir, properties={"cmake-generator": "Unix Makefiles"}
        )

        assert plugin.get_build_commands() == [
            f'cmake "{plugin._part_info.part_src_dir}" -G "Unix Makefiles"',
            f"cmake --build . -- -j{plugin._part_info.parallel_build_count}",
            (
                f'DESTDIR="{plugin._part_info.part_install_dir}" '
                "cmake --build . --target install"
            ),
        ]

    def test_get_build_commands_cmake_parameters(self, setup_method_fixture, new_dir):
        cmake_parameters = [
            "-DVERBOSE=1",
            "-DCMAKE_INSTALL_PREFIX=/foo",
            '-DCMAKE_SPACED_ARGS="foo bar"',
            '-DCMAKE_USING_ENV="$SNAPCRAFT_PART_INSTALL"/bar',
        ]

        plugin = setup_method_fixture(new_dir, {"cmake-parameters": cmake_parameters})

        assert plugin.get_build_commands() == [
            (
                f'cmake "{plugin._part_info.part_src_dir}" -G "Unix Makefiles" '
                f"{' '.join(cmake_parameters)}"
            ),
            f"cmake --build . -- -j{plugin._part_info.parallel_build_count}",
            (
                f'DESTDIR="{plugin._part_info.part_install_dir}" '
                "cmake --build . --target install"
            ),
        ]

    def test_get_out_of_source_build(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_out_of_source_build() is True
