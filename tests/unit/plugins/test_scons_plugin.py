import pytest
from craft_parts import Part, PartInfo, ProjectInfo, errors
from craft_parts.plugins.scons_plugin import SConsPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)
    scons = dependency_fixture("scons", output="SCons by Steven Knight et al.")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(scons.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_scons(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'scons' not found"


def test_validate_environment_broken_scons(dependency_fixture, part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)
    scons = dependency_fixture("scons", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(scons.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'scons' failed with error code 33"


def test_validate_environment_invalid_scons(dependency_fixture, part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)
    scons = dependency_fixture("scons", invalid=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(scons.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid scons compiler version ''"


def test_validate_environment_with_scons_part(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["scons-deps"])


def test_validate_environment_without_scons_part(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'scons' not found and part 'my-part' does not depend on a part named "
        "'scons-deps' that would satisfy the dependency"
    )


def test_get_build_snaps_and_packages(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == set()


def test_get_build_environment(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {
        "DESTDIR": str(part_info.part_install_dir)
    }


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        SConsPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_build_commands(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == ["scons", "scons install"]


def test_get_build_commands_with_parameters(part_info):
    properties = SConsPlugin.properties_class.unmarshal(
        {"source": ".", "scons-parameters": ["a=1", "b=2"]}
    )
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == ["scons a=1 b=2", "scons install a=1 b=2"]
