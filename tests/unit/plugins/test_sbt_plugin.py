# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.sbt_plugin import SbtPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment_wrapper_enabled(part_info):
    properties = SbtPlugin.properties_class.unmarshal({"source": "."})
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_without_wrapper(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {"source": ".", "sbt-use-wrapper": False}
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment()


def test_get_build_snaps_and_packages(part_info):
    properties = SbtPlugin.properties_class.unmarshal({"source": "."})
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == set()


def test_get_build_packages_without_wrapper(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {"source": ".", "sbt-use-wrapper": False}
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == {"ca-certificates", "curl", "tar"}


def test_get_build_environment(part_info):
    properties = SbtPlugin.properties_class.unmarshal({"source": "."})
    plugin = SbtPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert "JAVA_HOME" in env


def test_get_build_environment_without_wrapper(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {"source": ".", "sbt-use-wrapper": False}
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()

    assert "JAVA_HOME" in env
    assert env["PATH"] == "${CRAFT_PART_BUILD}/.parts/sbt/bin:${PATH}"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        SbtPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_build_commands(part_info):
    properties = SbtPlugin.properties_class.unmarshal({"source": "."})
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        """[ -e ${CRAFT_PART_BUILD_WORK}/sbt ] || {
>&2 echo 'sbt wrapper file not found, set sbt-use-wrapper to false to bootstrap sbt from official releases.'; exit 1;
}""",
        "chmod +x ${CRAFT_PART_BUILD_WORK}/sbt",
        "${CRAFT_PART_BUILD_WORK}/sbt package",
        *plugin._get_java_post_build_commands(),
    ]


def test_get_pull_commands_without_wrapper(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {"source": ".", "sbt-use-wrapper": False}
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == []


def test_get_pull_commands_with_custom_version(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {"source": ".", "sbt-use-wrapper": False, "sbt-version": "1.11.7"}
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == []


def test_get_build_commands_without_wrapper(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "sbt-use-wrapper": False,
            "sbt-task": "test",
            "sbt-parameters": ["-Dsbt.log.noformat=true"],
        }
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "mkdir -p ${CRAFT_PART_BUILD}/.parts",
        'curl -fsSL "https://github.com/sbt/sbt/releases/download/v1.12.11/sbt-1.12.11.tgz" -o "${CRAFT_PART_BUILD}/.parts/sbt-1.12.11.tgz"',
        'tar -xzf "${CRAFT_PART_BUILD}/.parts/sbt-1.12.11.tgz" -C "${CRAFT_PART_BUILD}/.parts"',
        'rm -f "${CRAFT_PART_BUILD}/.parts/sbt-1.12.11.tgz"',
        "${CRAFT_PART_BUILD}/.parts/sbt/bin/sbt test -Dsbt.log.noformat=true",
        *plugin._get_java_post_build_commands(),
    ]


def test_get_build_commands_without_wrapper_custom_version(part_info):
    properties = SbtPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "sbt-use-wrapper": False,
            "sbt-version": "1.11.7",
        }
    )
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert (
        "https://github.com/sbt/sbt/releases/download/v1.11.7/sbt-1.11.7.tgz"
        in plugin.get_build_commands()[1]
    )


def test_get_out_of_source_build(part_info):
    properties = SbtPlugin.properties_class.unmarshal({"source": "."})
    plugin = SbtPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False
