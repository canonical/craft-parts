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
from craft_parts.plugins.fpc_use_plugin import FpcUsePlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("greetlib", {}),
    )


@pytest.fixture
def plugin(part_info):
    properties = FpcUsePlugin.properties_class.unmarshal({"source": "."})
    return FpcUsePlugin(properties=properties, part_info=part_info)


def test_get_build_snaps(plugin):
    assert plugin.get_build_snaps() == set()


def test_get_build_packages(plugin):
    assert plugin.get_build_packages() == set()


def test_get_build_environment(plugin):
    assert plugin.get_build_environment() == {}


def test_get_out_of_source_build(plugin):
    assert plugin.get_out_of_source_build() is True


def test_get_build_commands(part_info, plugin):
    export_dir = part_info.part_export_dir / "fpc-use" / "greetlib"

    assert plugin.get_build_commands() == [
        f"ln -sfn {part_info.part_src_subdir} {export_dir}/source",
    ]
    assert (export_dir / "unit-paths").read_text() == ".\n"
    assert (export_dir / "include-paths").read_text() == ""


def test_get_build_commands_with_paths(part_info):
    properties = FpcUsePlugin.properties_class.unmarshal(
        {
            "source": ".",
            "fpc-use-unit-paths": ["units", "lib/*"],
            "fpc-use-include-paths": ["include"],
        }
    )
    plugin = FpcUsePlugin(properties=properties, part_info=part_info)
    export_dir = part_info.part_export_dir / "fpc-use" / "greetlib"

    assert plugin.get_build_commands() == [
        f"ln -sfn {part_info.part_src_subdir} {export_dir}/source",
    ]
    assert (export_dir / "unit-paths").read_text() == "units\nlib/*\n"
    assert (export_dir / "include-paths").read_text() == "include\n"


def test_get_build_commands_source_subdir(new_dir):
    part_info = PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part(
            "greetlib", {"plugin": "fpc-use", "source": ".", "source-subdir": "lib"}
        ),
    )
    properties = FpcUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = FpcUsePlugin(properties=properties, part_info=part_info)
    export_dir = part_info.part_export_dir / "fpc-use" / "greetlib"

    assert plugin.get_build_commands() == [
        f"ln -sfn {part_info.part_src_dir}/lib {export_dir}/source",
    ]


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        FpcUsePlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        FpcUsePlugin.properties_class.unmarshal(
            {"source": ".", "fpc-use-invalid": True}
        )
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("fpc-use-invalid",)
    assert err[0]["type"] == "extra_forbidden"
