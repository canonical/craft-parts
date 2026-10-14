# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.mill_plugin import MillPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment_wrapper_enabled(part_info):
    properties = MillPlugin.properties_class.unmarshal({"source": "."})
    plugin = MillPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_without_wrapper(part_info):
    properties = MillPlugin.properties_class.unmarshal(
        {"source": ".", "mill-use-wrapper": False}
    )
    plugin = MillPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment()


def test_get_build_snaps_and_packages(part_info):
    properties = MillPlugin.properties_class.unmarshal({"source": "."})
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == set()


def test_get_build_packages_without_wrapper(part_info):
    properties = MillPlugin.properties_class.unmarshal(
        {"source": ".", "mill-use-wrapper": False}
    )
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == {"ca-certificates", "curl"}


def test_get_build_environment(part_info):
    properties = MillPlugin.properties_class.unmarshal({"source": "."})
    plugin = MillPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert "JAVA_HOME" in env


def test_get_build_environment_without_wrapper(part_info):
    properties = MillPlugin.properties_class.unmarshal(
        {"source": ".", "mill-use-wrapper": False}
    )
    plugin = MillPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()

    assert "JAVA_HOME" in env
    assert env["PATH"] == "${CRAFT_PART_BUILD}/.parts/bin:${PATH}"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        MillPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_build_commands(part_info):
    properties = MillPlugin.properties_class.unmarshal({"source": "."})
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        """[ -e ${CRAFT_PART_BUILD_WORK}/mill ] || {
>&2 echo 'mill wrapper file not found, set mill-use-wrapper to false to use a system-installed mill binary.'; exit 1;
}""",
        "chmod +x ${CRAFT_PART_BUILD_WORK}/mill",
        "${CRAFT_PART_BUILD_WORK}/mill __.assembly",
        *plugin._get_java_post_build_commands(),
    ]


def test_get_pull_commands_without_wrapper(part_info):
    properties = MillPlugin.properties_class.unmarshal(
        {"source": ".", "mill-use-wrapper": False}
    )
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == [
        f'mkdir -p "{plugin._part_info.part_build_subdir}/.parts/bin"',
        'curl -fsSL "https://github.com/com-lihaoyi/mill/releases/download/0.12.8/0.12.8" -o '
        f'"{plugin._part_info.part_build_subdir}/.parts/bin/mill"',
        f'chmod +x "{plugin._part_info.part_build_subdir}/.parts/bin/mill"',
    ]


def test_get_pull_commands_with_custom_version(part_info):
    properties = MillPlugin.properties_class.unmarshal(
        {"source": ".", "mill-use-wrapper": False, "mill-version": "0.12.9"}
    )
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert (
        "https://github.com/com-lihaoyi/mill/releases/download/0.12.9/0.12.9"
        in plugin.get_pull_commands()[1]
    )


def test_get_build_commands_without_wrapper(part_info):
    properties = MillPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "mill-use-wrapper": False,
            "mill-task": "foo.run",
            "mill-parameters": ["--watch"],
        }
    )
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "${CRAFT_PART_BUILD}/.parts/bin/mill foo.run --watch",
        *plugin._get_java_post_build_commands(),
    ]


def test_get_out_of_source_build(part_info):
    properties = MillPlugin.properties_class.unmarshal({"source": "."})
    plugin = MillPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False
