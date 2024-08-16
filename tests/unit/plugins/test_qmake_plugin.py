# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
# Copyright 2023 Scarlett Moore <sgmoore@kde.org>
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
from craft_parts.plugins.qmake_plugin import QmakePlugin


@pytest.fixture
def setup_method_fixture():
    def _setup_method_fixture(new_dir, properties=None):
        if properties is None:
            properties = {}
        properties["source"] = "."
        plugin_properties = QmakePlugin.properties_class.unmarshal(properties)
        part = Part("foo", {})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        project_info._parallel_build_count = 42

        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("install/dir")

        return QmakePlugin(properties=plugin_properties, part_info=part_info)

    return _setup_method_fixture


class TestPluginQMakePlugin:
    """QMake plugin tests."""

    def test_get_build_snaps(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)
        assert plugin.get_build_snaps() == set()

    @pytest.mark.parametrize(
        ("properties", "build_packages"),
        [
            ({}, {"g++", "make", "qt5-qmake"}),
            ({"qmake-major-version": 5}, {"g++", "make", "qt5-qmake"}),
            ({"qmake-major-version": 6}, {"g++", "make", "qmake6"}),
        ],
    )
    def test_get_build_packages(
        self, setup_method_fixture, new_dir, properties, build_packages
    ):
        plugin = setup_method_fixture(new_dir, properties=properties)
        assert plugin.get_build_packages() == build_packages

    def test_get_build_environment_default(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_build_environment() == {
            "QT_SELECT": "qt5",
        }

    def test_get_build_environment_qt6(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir, properties={"qmake-major-version": 6})

        assert plugin.get_build_environment() == {
            "QT_SELECT": "qt6",
        }

    def test_get_build_commands_default(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_build_commands() == [
            f'qmake QMAKE_CFLAGS+="${{CFLAGS:-}}" QMAKE_CXXFLAGS+="${{CXXFLAGS:-}}" QMAKE_LFLAGS+="${{LDFLAGS:-}}" {plugin._part_info.part_src_dir}',
            f"env -u CFLAGS -u CXXFLAGS make -j{plugin._part_info.parallel_build_count}",
            f"make install INSTALL_ROOT={plugin._part_info.part_install_dir}",
        ]

    def test_get_build_commands_qt6(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir, properties={"qmake-major-version": 6})

        assert plugin.get_build_commands() == [
            f'qmake6 QMAKE_CFLAGS+="${{CFLAGS:-}}" QMAKE_CXXFLAGS+="${{CXXFLAGS:-}}" QMAKE_LFLAGS+="${{LDFLAGS:-}}" {plugin._part_info.part_src_dir}',
            f"env -u CFLAGS -u CXXFLAGS make -j{plugin._part_info.parallel_build_count}",
            f"make install INSTALL_ROOT={plugin._part_info.part_install_dir}",
        ]

    def test_get_build_commands_qmake_project_file(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(
            new_dir, properties={"qmake-project-file": "hello.pro"}
        )

        assert plugin.get_build_commands() == [
            'qmake QMAKE_CFLAGS+="${CFLAGS:-}" QMAKE_CXXFLAGS+="${CXXFLAGS:-}" '
            'QMAKE_LFLAGS+="${LDFLAGS:-}" '
            f"{plugin._part_info.part_src_dir}/hello.pro",
            f"env -u CFLAGS -u CXXFLAGS make -j{plugin._part_info.parallel_build_count}",
            f"make install INSTALL_ROOT={plugin._part_info.part_install_dir}",
        ]

    def test_get_build_commands_qmake_parameters(self, setup_method_fixture, new_dir):
        qmake_parameters = [
            "QMAKE_LIBDIR+=/foo",
        ]

        plugin = setup_method_fixture(new_dir, {"qmake-parameters": qmake_parameters})

        assert plugin.get_build_commands() == [
            f'qmake QMAKE_CFLAGS+="${{CFLAGS:-}}" QMAKE_CXXFLAGS+="${{CXXFLAGS:-}}" QMAKE_LFLAGS+="${{LDFLAGS:-}}" QMAKE_LIBDIR+=/foo {plugin._part_info.part_src_dir}',
            f"env -u CFLAGS -u CXXFLAGS make -j{plugin._part_info.parallel_build_count}",
            f"make install INSTALL_ROOT={plugin._part_info.part_install_dir}",
        ]

    def test_get_out_of_source_build(self, setup_method_fixture, new_dir):
        plugin = setup_method_fixture(new_dir)

        assert plugin.get_out_of_source_build() is True
