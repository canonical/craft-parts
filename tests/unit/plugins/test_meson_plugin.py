# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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
from craft_parts.plugins.meson_plugin import MesonPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)
    meson = dependency_fixture("meson")
    ninja = dependency_fixture("ninja")

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(meson.parent)}:{str(ninja.parent)}",
        properties=properties,
    )
    validator.validate_environment()


def test_validate_environment_missing_meson(dependency_fixture, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)
    ninja = dependency_fixture("ninja")

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(ninja.parent)}",
        properties=properties,
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'meson' not found"


def test_validate_environment_missing_ninja(dependency_fixture, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)
    meson = dependency_fixture("meson")

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(meson.parent)}",
        properties=properties,
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ninja' not found"


def test_validate_environment_broken_meson(dependency_fixture, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)
    meson = dependency_fixture("meson", broken=True)
    ninja = dependency_fixture("ninja")

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(ninja.parent)}:{str(meson.parent)}",
        properties=properties,
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'meson' failed with error code 33"


def test_validate_environment_broken_ninja(dependency_fixture, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)
    meson = dependency_fixture("meson")
    ninja = dependency_fixture("ninja", broken=True)

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(meson.parent)}:{str(ninja.parent)}",
        properties=properties,
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ninja' failed with error code 33"


def test_validate_environment_with_meson_deps_part(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["meson-deps"])


def test_validate_environment_without_meson_part(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=["ninja"])

    assert raised.value.reason == (
        "'meson' not found and part 'my-part' does not depend on a part named "
        "'meson-deps' that would satisfy the dependency"
    )


def test_validate_environment_without_ninja_part(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=["meson"])

    assert raised.value.reason == (
        "'meson' not found and part 'my-part' does not depend on a part named "
        "'meson-deps' that would satisfy the dependency"
    )


def test_get_out_of_source_build(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is True


def test_get_build_snaps(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


def test_get_build_environment(new_dir, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


def test_get_build_commands(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        f"meson {plugin._part_info.part_src_dir}",
        "ninja",
        f"DESTDIR={plugin._part_info.part_install_dir} ninja install",
    ]


def test_get_build_commands_with_parameters(part_info):
    properties = MesonPlugin.properties_class.unmarshal(
        {"source": ".", "meson-parameters": ["--debug", "--prefix=foo bar"]}
    )
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        f"meson {plugin._part_info.part_src_dir} --debug '--prefix=foo bar'",
        "ninja",
        f"DESTDIR={plugin._part_info.part_install_dir} ninja install",
    ]


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        MesonPlugin.properties_class.unmarshal({"source": ".", "meson-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("meson-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        MesonPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"
