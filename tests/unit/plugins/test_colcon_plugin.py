# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
from craft_parts.plugins.colcon_plugin import ColconPlugin


@pytest.fixture
def setup_method_fixture():
    def _setup_method_fixture(new_dir, properties=None):
        if properties is None:
            properties = {}
        properties["source"] = "."
        plugin_properties = ColconPlugin.properties_class.unmarshal(properties)
        part = Part("foo", {})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        project_info._parallel_build_count = 42

        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("install/dir")

        return ColconPlugin(properties=plugin_properties, part_info=part_info)

    return _setup_method_fixture


class TestPluginColconPlugin:
    """Colcon plugin tests."""

    def test_get_build_snaps(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)
        assert plugin.get_build_snaps() == set()

    def test_get_build_packages(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)
        assert plugin.get_build_packages() == {
            "gcc",
            "g++",
            "cmake",
            "python3-colcon-core",
            "python3-colcon-cmake",
            "python3-colcon-package-selection",
            "python3-colcon-python-setup-py",
            "python3-colcon-parallel-executor",
        }

    def test_get_build_environment_default(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_build_environment() == {
            "AMENT_PYTHON_EXECUTABLE": "/usr/bin/python3",
            "COLCON_PYTHON_EXECUTABLE": "/usr/bin/python3",
        }

    @pytest.mark.parametrize(
        (
            "properties",
            "colcon_packages_ignore",
            "colcon_packages_select",
            "colcon_cmake_args",
        ),
        [
            pytest.param({}, "", "", "", id="no optional properties"),
            pytest.param(
                {"colcon-packages-ignore": ["rlcpy", "example"]},
                "--packages-ignore rlcpy example",
                "",
                "",
                id="packages ignore only",
            ),
            pytest.param(
                {"colcon-packages": ["package1"]},
                "",
                "--packages-select package1",
                "",
                id="packages select only",
            ),
            pytest.param(
                {
                    "colcon-packages-ignore": ["rlcpy", "example"],
                    "colcon-packages": ["package1"],
                },
                "--packages-ignore rlcpy example",
                "--packages-select package1",
                "",
                id="packages ignore and select",
            ),
        ],
    )
    def test_get_build_commands(
        self,
        setup_method_fixture,
        new_dir,
        properties,
        colcon_packages_ignore,
        colcon_packages_select,
        colcon_cmake_args,
    ):
        plugin = setup_method_fixture(new_dir, properties=properties)

        optional_properties = " "
        if plugin._options.colcon_packages_ignore:
            optional_properties += f"{colcon_packages_ignore} "
        if plugin._options.colcon_packages:
            optional_properties += f"{colcon_packages_select} "
        if plugin._options.colcon_cmake_args:
            optional_properties += f"{colcon_cmake_args} "
        assert plugin.get_build_commands() == [
            "##[craft-parts.colcon] Sourcing colcon ws in stage snaps",
            'if [ -n "${ROS_DISTRO:-}" ] && [ -f "${CRAFT_PART_INSTALL}/opt/ros/${ROS_DISTRO:-}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="${{CRAFT_PART_INSTALL}}{wspath}" . "${{CRAFT_PART_INSTALL}}{wspath}/local_setup.sh"'.format(
                wspath="/opt/ros/${ROS_DISTRO:-}"
            ),
            "fi",
            "",
            "##[craft-parts.colcon] Sourcing the colcon workspace",
            'if [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/${ROS_DISTRO:-}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="{wspath}" . "{wspath}/local_setup.sh"'.format(
                wspath="/opt/ros/${ROS_DISTRO:-}"
            ),
            "fi",
            "",
            f'colcon build --base-paths "{plugin._part_info.part_src_dir}" '
            f'--build-base "{plugin._part_info.part_build_dir}" '
            f"--merge-install --install-base {plugin._part_info.part_install_dir}"
            f"{optional_properties}"
            f"--cmake-args -DCMAKE_BUILD_TYPE=Release "
            f"--parallel-workers {plugin._part_info.parallel_build_count}",
        ]

    @pytest.mark.parametrize(
        ("properties", "colcon_cmake_args"),
        [
            pytest.param({}, "", id="no cmake args"),
            pytest.param(
                {"colcon-cmake-args": ['-DCMAKE_CXX_FLAGS="-Wall -Wextra"']},
                '-DCMAKE_CXX_FLAGS="-Wall -Wextra"',
                id="cmake args with flags",
            ),
        ],
    )
    def test_get_build_commands_cmake_options(
        self,
        setup_method_fixture,
        new_dir,
        properties,
        colcon_cmake_args,
    ):
        plugin = setup_method_fixture(new_dir, properties=properties)
        if plugin._options.colcon_cmake_args:
            cmake_args = f"--cmake-args -DCMAKE_BUILD_TYPE=Release {colcon_cmake_args} "
        else:
            cmake_args = "--cmake-args -DCMAKE_BUILD_TYPE=Release "
        assert plugin.get_build_commands() == [
            "##[craft-parts.colcon] Sourcing colcon ws in stage snaps",
            'if [ -n "${ROS_DISTRO:-}" ] && [ -f "${CRAFT_PART_INSTALL}/opt/ros/${ROS_DISTRO:-}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="${{CRAFT_PART_INSTALL}}{wspath}" . "${{CRAFT_PART_INSTALL}}{wspath}/local_setup.sh"'.format(
                wspath="/opt/ros/${ROS_DISTRO:-}"
            ),
            "fi",
            "",
            "##[craft-parts.colcon] Sourcing the colcon workspace",
            'if [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/${ROS_DISTRO:-}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="{wspath}" . "{wspath}/local_setup.sh"'.format(
                wspath="/opt/ros/${ROS_DISTRO:-}"
            ),
            "fi",
            "",
            f'colcon build --base-paths "{plugin._part_info.part_src_dir}" '
            f'--build-base "{plugin._part_info.part_build_dir}" '
            f"--merge-install --install-base {plugin._part_info.part_install_dir} "
            f"{cmake_args}"
            f"--parallel-workers {plugin._part_info.parallel_build_count}",
        ]

    def test_get_build_commands_cmake_debug(
        self,
        setup_method_fixture,
        new_dir,
    ):
        plugin = setup_method_fixture(
            new_dir,
            properties={
                "colcon-cmake-args": [
                    "-DCMAKE_BUILD_TYPE=Debug",
                    '-DCMAKE_CXX_FLAGS="-Wall -Wextra"',
                ]
            },
        )
        assert plugin.get_build_commands() == [
            "##[craft-parts.colcon] Sourcing colcon ws in stage snaps",
            'if [ -n "${ROS_DISTRO:-}" ] && [ -f "${CRAFT_PART_INSTALL}/opt/ros/${ROS_DISTRO:-}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="${{CRAFT_PART_INSTALL}}{wspath}" . "${{CRAFT_PART_INSTALL}}{wspath}/local_setup.sh"'.format(
                wspath="/opt/ros/${ROS_DISTRO:-}"
            ),
            "fi",
            "",
            "##[craft-parts.colcon] Sourcing the colcon workspace",
            'if [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/${ROS_DISTRO:-}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="{wspath}" . "{wspath}/local_setup.sh"'.format(
                wspath="/opt/ros/${ROS_DISTRO:-}"
            ),
            "fi",
            "",
            f'colcon build --base-paths "{plugin._part_info.part_src_dir}" '
            f'--build-base "{plugin._part_info.part_build_dir}" '
            f"--merge-install --install-base {plugin._part_info.part_install_dir} "
            f'--cmake-args -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="-Wall -Wextra" '
            f"--parallel-workers {plugin._part_info.parallel_build_count}",
        ]
