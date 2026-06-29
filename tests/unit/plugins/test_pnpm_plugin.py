# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.pnpm_plugin import PnpmPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment_wrapper_enabled(part_info):
    properties = PnpmPlugin.properties_class.unmarshal({"source": "."})
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_without_wrapper(part_info):
    properties = PnpmPlugin.properties_class.unmarshal(
        {"source": ".", "pnpm-use-wrapper": False}
    )
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment()


def test_get_build_snaps_and_packages(part_info):
    properties = PnpmPlugin.properties_class.unmarshal({"source": "."})
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == set()


def test_get_build_packages_without_wrapper(part_info):
    properties = PnpmPlugin.properties_class.unmarshal(
        {"source": ".", "pnpm-use-wrapper": False}
    )
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == {"ca-certificates", "curl"}


def test_get_build_environment(part_info):
    properties = PnpmPlugin.properties_class.unmarshal({"source": "."})
    plugin = PnpmPlugin(properties=properties, part_info=part_info)
    assert plugin.get_build_environment() == {}


def test_get_build_environment_without_wrapper(part_info):
    properties = PnpmPlugin.properties_class.unmarshal(
        {"source": ".", "pnpm-use-wrapper": False}
    )
    plugin = PnpmPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()

    assert env == {"PATH": "${CRAFT_PART_BUILD}/.parts/bin:${PATH}"}


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        PnpmPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_pull_commands(part_info):
    properties = PnpmPlugin.properties_class.unmarshal({"source": "."})
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == []


def test_get_pull_commands_without_wrapper(part_info):
    properties = PnpmPlugin.properties_class.unmarshal(
        {"source": ".", "pnpm-use-wrapper": False}
    )
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == []


def test_get_pull_commands_without_wrapper_custom_version(part_info):
    properties = PnpmPlugin.properties_class.unmarshal(
        {"source": ".", "pnpm-use-wrapper": False, "pnpm-version": "10.11.0"}
    )
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == []


def test_get_build_commands(part_info):
    properties = PnpmPlugin.properties_class.unmarshal({"source": "."})
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        """[ -e ${CRAFT_PART_BUILD_WORK}/pnpm ] || {
>&2 echo 'pnpm wrapper file not found, set pnpm-use-wrapper to false to bootstrap pnpm from official releases.'; exit 1;
}""",
        "chmod +x ${CRAFT_PART_BUILD_WORK}/pnpm",
        "if [ -f pnpm-lock.yaml ]; then ${CRAFT_PART_BUILD_WORK}/pnpm install --frozen-lockfile; else ${CRAFT_PART_BUILD_WORK}/pnpm install --no-frozen-lockfile; fi",
        "${CRAFT_PART_BUILD_WORK}/pnpm run build",
    ]


def test_get_build_commands_without_wrapper(part_info):
    properties = PnpmPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "pnpm-use-wrapper": False,
            "pnpm-task": "run build",
            "pnpm-parameters": ["--filter", "sample-app"],
        }
    )
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        'mkdir -p "${CRAFT_PART_BUILD}/.parts/bin"',
        'curl -fsSL "https://github.com/pnpm/pnpm/releases/download/v10.12.1/pnpm-linux-x64" -o "${CRAFT_PART_BUILD}/.parts/bin/pnpm"',
        'chmod +x "${CRAFT_PART_BUILD}/.parts/bin/pnpm"',
        "if [ -f pnpm-lock.yaml ]; then ${CRAFT_PART_BUILD}/.parts/bin/pnpm install --frozen-lockfile; else ${CRAFT_PART_BUILD}/.parts/bin/pnpm install --no-frozen-lockfile; fi",
        "${CRAFT_PART_BUILD}/.parts/bin/pnpm run build --filter sample-app",
    ]


def test_get_out_of_source_build(part_info):
    properties = PnpmPlugin.properties_class.unmarshal({"source": "."})
    plugin = PnpmPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False
