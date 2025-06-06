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
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.go_use_plugin import GoUsePlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)
    go = dependency_fixture("go", output="go version go1.17 linux/amd64")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_go(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'go' not found"


def test_validate_environment_broken_go(dependency_fixture, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)
    go = dependency_fixture("go", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'go' failed with error code 33"


def test_validate_environment_invalid_go(dependency_fixture, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)
    go = dependency_fixture("go", invalid=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid go compiler version ''"


def test_validate_environment_with_go_part(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["go-deps"])


def test_validate_environment_without_go_part(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'go' not found and part 'my-part' does not depend on a part named "
        "'go-deps' that would satisfy the dependency"
    )


def test_get_build_snaps(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


def test_get_build_environment(new_dir, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        GoUsePlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_out_of_source_build(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is True


@pytest.mark.parametrize(
    "part_data", [{"source": "."}, {"source": ".", "source-subdir": "my/subdir"}]
)
def test_get_build_commands(mocker, part_info, part_data):
    """Test that go work is created and that work.go is created."""
    properties = GoUsePlugin.properties_class.unmarshal(part_data)
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    dest_dir = part_info.part_export_dir / "go-use" / part_info.part_name

    assert plugin.get_build_commands() == [
        f"mkdir -p '{part_info.part_export_dir}/go-use'",
        f"ln -sf '{part_info.part_src_subdir}' '{dest_dir}'",
    ]
