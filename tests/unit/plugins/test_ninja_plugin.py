# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.ninja_plugin import NinjaPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)
    ninja = dependency_fixture("ninja")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ninja.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_ninja(part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ninja' not found"


def test_validate_environment_broken_ninja(dependency_fixture, part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)
    ninja = dependency_fixture("ninja", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ninja.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ninja' failed with error code 33"


def test_get_build_snaps_and_packages(part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == {"ninja-build"}


def test_get_build_environment(part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


def test_get_pull_commands(part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == []


def test_get_build_commands_default(part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == ["ninja"]


def test_get_build_commands_with_target_and_parameters(part_info):
    properties = NinjaPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "ninja-target": "all",
            "ninja-parameters": ["-j4"],
            "ninja-build-directory": "build",
        }
    )
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == ["ninja -C build all -j4"]


def test_get_build_commands_with_configure_and_install(part_info):
    properties = NinjaPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "ninja-configure-command": "cmake -S . -B build -G Ninja",
            "ninja-build-directory": "build",
            "ninja-install": True,
        }
    )
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "cmake -S . -B build -G Ninja",
        "ninja -C build",
        f"DESTDIR={plugin._part_info.part_install_dir} ninja -C build install",
    ]


def test_get_out_of_source_build(part_info):
    properties = NinjaPlugin.properties_class.unmarshal({"source": "."})
    plugin = NinjaPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        NinjaPlugin.properties_class.unmarshal({"source": ".", "ninja-bad": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("ninja-bad",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        NinjaPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"
