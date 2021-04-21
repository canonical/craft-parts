# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path

import pytest
from pydantic import ValidationError

from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.make_plugin import MakePlugin

# pylint: disable=attribute-defined-outside-init


class TestPluginMake:
    """Make plugin tests."""

    def setup_method(self):
        properties = MakePlugin.properties_class.unmarshal({})
        part = Part("foo", {})

        project_info = ProjectInfo()
        project_info._parallel_build_count = 42

        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("install/dir")

        self._plugin = MakePlugin(properties=properties, part_info=part_info)

    def test_get_build_packages(self):
        assert self._plugin.get_build_packages() == {
            "gcc",
            "make",
        }
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == dict()

    def test_get_build_commands(self):
        assert self._plugin.get_build_commands() == [
            'make -j"42"',
            'make -j"42" install DESTDIR="install/dir"',
        ]

    def test_get_build_commands_with_parameters(self):
        props = MakePlugin.properties_class.unmarshal(
            {"make-parameters": ["FLAVOR=gtk3"]}
        )
        part = Part("foo", {})

        project_info = ProjectInfo()
        project_info._parallel_build_count = 8

        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("/tmp")

        plugin = MakePlugin(properties=props, part_info=part_info)

        assert plugin.get_build_commands() == [
            'make -j"8" FLAVOR=gtk3',
            'make -j"8" install FLAVOR=gtk3 DESTDIR="/tmp"',
        ]

    def test_invalid_parameters(self):
        with pytest.raises(ValidationError) as raised:
            MakePlugin.properties_class.unmarshal({"make-invalid": True})
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("make-invalid",)
        assert err[0]["type"] == "value_error.extra"
