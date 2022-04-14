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
from pydantic import ValidationError

from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.conda_plugin import CondaPlugin


@pytest.fixture
def part_info(new_dir):
    yield PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


class TestPluginCondaPlugin:
    """Conda plugin tests."""

    def test_validate_environment(self, dependency_fixture, part_info):
        conda = dependency_fixture("conda")
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(
            part_name="my-part",
            env=f"PATH={str(conda.parent)}",
        )
        validator.validate_environment()

    def test_validate_environment_missing_dependencies(
        self, dependency_fixture, part_info
    ):
        """Validate that missing dependencies raise an exception.

        :param dependencies: tuple consisting of 1 missing dependency
        and a list of valid dependencies
        """
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert raised.value.reason == "'conda' not found"

    def test_validate_environment_broken_dependencies(
        self, dependency_fixture, part_info
    ):
        """Validate that broken dependencies raise an exception.

        :param dependencies: tuple consisting of 1 broken dependency
        and a list of valid dependencies
        """
        broken_dependency = dependency_fixture("conda", broken=True)
        path = f"PATH={str(broken_dependency.parent)}"

        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(part_name="my-part", env=path)
        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert raised.value.reason == "'conda' failed with error code 33"

    def test_validate_environment_part_dependencies(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
        validator.validate_environment(part_dependencies=["conda"])

    def test_validate_environment_missing_part_dependencies(
        self, dependency_fixture, part_info
    ):
        """Validate that missing part dependencies raise an exception.

        :param dependencies: tuple consisting of 1 missing part dependency
        and a list of valid part dependencies
        """
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment(part_dependencies=["foo"])

        assert raised.value.reason == (
            "'conda' not found and part 'my-part' depends on a part named 'conda'"
        )

    def test_get_build_snaps(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)
        assert plugin.get_build_snaps() == set()

    def test_get_build_packages(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)
        assert plugin.get_build_packages() == set()

    def test_get_build_environment(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_environment() == {}

    def test_get_build_commands(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "CONDA_TARGET_PREFIX_OVERRIDE=/snap/${CRAFT_PROJECT_NAME}/current "
            "conda create --prefix $CRAFT_PART_INSTALL --yes",
        ]

    def test_get_build_commands_conda_packages(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal(
            {"conda-packages": ["test-package-1", "test-package-2"]}
        )
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "CONDA_TARGET_PREFIX_OVERRIDE=/snap/${CRAFT_PROJECT_NAME}/current "
            "conda create --prefix $CRAFT_PART_INSTALL "
            "--yes test-package-1 test-package-2"
        ]

    def test_get_build_commands_conda_packages_none(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({"conda-packages": None})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "CONDA_TARGET_PREFIX_OVERRIDE=/snap/${CRAFT_PROJECT_NAME}/current "
            "conda create --prefix $CRAFT_PART_INSTALL --yes"
        ]

    def test_get_build_commands_conda_packages_empty(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal({"conda-packages": []})
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "CONDA_TARGET_PREFIX_OVERRIDE=/snap/${CRAFT_PROJECT_NAME}/current "
            "conda create --prefix $CRAFT_PART_INSTALL --yes"
        ]

    @pytest.mark.parametrize(
        "conda_packages",
        ["i am a string", {"i am": "a dictionary"}],
    )
    def test_get_build_commands_conda_packages_invalid(self, conda_packages, part_info):
        with pytest.raises(ValidationError):
            CondaPlugin.properties_class.unmarshal({"conda-packages": conda_packages})

    def test_get_build_commands_conda_python_version(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal(
            {"conda-python-version": "3.9"}
        )
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "CONDA_TARGET_PREFIX_OVERRIDE=/snap/${CRAFT_PROJECT_NAME}/current "
            "conda create --prefix $CRAFT_PART_INSTALL --yes python=3.9"
        ]

    @pytest.mark.parametrize(
        "conda_python_version",
        [{"i am": "a dictionary"}, ["i am", "a list"]],
    )
    def test_get_build_commands_conda_python_version_invalid(
        self, conda_python_version, part_info
    ):
        with pytest.raises(ValidationError):
            CondaPlugin.properties_class.unmarshal(
                {"conda-python-version": conda_python_version}
            )

    def test_get_build_commands_conda_install_prefix(self, part_info):
        properties = CondaPlugin.properties_class.unmarshal(
            {"conda-install-prefix": "/test/install/directory"}
        )
        plugin = CondaPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "CONDA_TARGET_PREFIX_OVERRIDE=/test/install/directory "
            "conda create --prefix $CRAFT_PART_INSTALL --yes"
        ]

    @pytest.mark.parametrize(
        "conda_install_prefix",
        [{"i am": "a dictionary"}, ["i am", "a list"]],
    )
    def test_get_build_commands_conda_install_prefix_invalid(
        self, conda_install_prefix, part_info
    ):
        with pytest.raises(ValidationError):
            CondaPlugin.properties_class.unmarshal(
                {"conda-install-prefix": conda_install_prefix}
            )
