# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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
from craft_parts.plugins.nil_plugin import NilPlugin

# pylint: disable=attribute-defined-outside-init


class TestPluginNil:
    """Check nil plugin methods and properties."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        properties = NilPlugin.properties_class.unmarshal({})
        part = Part("foo", {})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(project_info=project_info, part=part)

        self._plugin = NilPlugin(properties=properties, part_info=part_info)

    def test_get_build_packages(self):
        assert self._plugin.get_build_packages() == set()
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == {}

    def test_get_build_commands(self):
        assert self._plugin.get_build_commands() == []

    def test_get_out_of_source_build(self):
        assert self._plugin.get_out_of_source_build() is False
