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

from pathlib import Path

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.dump_plugin import DumpPlugin

# pylint: disable=attribute-defined-outside-init


class TestPluginDump:
    """Check dump plugin methods and properties."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        properties = DumpPlugin.properties_class.unmarshal({"source": "something"})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)

        part = Part("foo", {})
        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("install/dir")

        self._plugin = DumpPlugin(properties=properties, part_info=part_info)

    def test_unmarshal_error(self):
        with pytest.raises(ValueError, match=r"source\n\s+Field required"):
            DumpPlugin.properties_class.unmarshal({})

    def test_get_build_packages(self):
        assert self._plugin.get_build_packages() == set()
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == {}

    def test_get_build_commands(self):
        assert self._plugin.get_build_commands() == [
            'cp --archive --link --no-dereference . "install/dir"'
        ]

    def test_get_out_of_source_build(self):
        assert self._plugin.get_out_of_source_build() is False
