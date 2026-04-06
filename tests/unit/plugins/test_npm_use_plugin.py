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

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.npm_use_plugin import NpmUsePlugin


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture
def self_contained_part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"build-attributes": ["self-contained"]}),
    )


class TestPluginNpmUsePlugin:
    """Npm-Use plugin tests."""

    def test_get_build_commands(self, part_info):
        properties = NpmUsePlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmUsePlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            f'mv "$(npm pack . | tail -1)" "{part_info.part_export_dir}/npm-cache/"'
        ]

    def test_get_self_contained_build_commands(self, self_contained_part_info, mocker):
        mocker.patch(
            "craft_parts.plugins.npm_use_plugin.get_install_from_local_tarballs_commands",
            return_value=[],
        )
        properties = NpmUsePlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmUsePlugin(properties=properties, part_info=self_contained_part_info)

        assert plugin.get_build_commands() == [
            f'mv "$(npm pack . | tail -1)" "{self_contained_part_info.part_export_dir}/npm-cache/"'
        ]
