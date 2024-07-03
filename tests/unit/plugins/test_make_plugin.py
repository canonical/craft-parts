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
from craft_parts.plugins.make_plugin import MakePlugin
from pydantic import ValidationError

# pylint: disable=attribute-defined-outside-init


class TestPluginMake:
    """Make plugin tests."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        properties = MakePlugin.properties_class.unmarshal({"source": "."})
        part = Part("foo", {})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
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
        assert not self._plugin.get_build_environment()

    def test_get_build_commands(self):
        assert self._plugin.get_build_commands() == [
            'make -j"42"',
            'make -j"42" install DESTDIR="install/dir"',
        ]

    def test_get_build_commands_with_parameters(self, new_dir):
        props = MakePlugin.properties_class.unmarshal(
            {"source": ".", "make-parameters": ["FLAVOR=gtk3"]}
        )
        part = Part("foo", {})

        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        project_info._parallel_build_count = 8

        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("/tmp")

        plugin = MakePlugin(properties=props, part_info=part_info)

        assert plugin.get_build_commands() == [
            'make -j"8" FLAVOR=gtk3',
            'make -j"8" install FLAVOR=gtk3 DESTDIR="/tmp"',
        ]

    def test_invalid_properties(self):
        with pytest.raises(ValidationError) as raised:
            MakePlugin.properties_class.unmarshal({"source": ".", "make-invalid": True})
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("make-invalid",)
        assert err[0]["type"] == "extra_forbidden"

    def test_missing_properties(self):
        with pytest.raises(ValidationError) as raised:
            MakePlugin.properties_class.unmarshal({})
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("source",)
        assert err[0]["type"] == "missing"

    def test_get_out_of_source_build(self):
        assert self._plugin.get_out_of_source_build() is False
