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
from craft_parts.plugins.rust_plugin import RustPlugin


@pytest.fixture
def part_info(new_dir):
    yield PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


class TestPluginRustPlugin:
    """Rust plugin tests."""

    def test_validate_environment(self, dependency_fixture, part_info):
        cargo = dependency_fixture("cargo")
        rustc = dependency_fixture("rustc")
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(
            part_name="my-part",
            env=f"PATH={str(cargo.parent)}:{str(rustc.parent)}",
            properties=properties,
        )
        validator.validate_environment()

    @pytest.mark.parametrize(
        "dependencies",
        [
            ("cargo", ["rustc"]),
            ("rustc", ["cargo"]),
        ],
    )
    def test_validate_environment_missing_dependencies(
        self, dependencies, dependency_fixture, part_info
    ):
        """Validate that missing dependencies raise an exception.

        :param dependencies: tuple consisting of 1 missing dependency
        and a list of valid dependencies
        """
        missing_dependency_name, valid_dependency_names = dependencies
        path = "PATH="

        for valid_dependencies_name in valid_dependency_names:
            valid_dependency = dependency_fixture(valid_dependencies_name)
            path += f":{str(valid_dependency.parent)}"

        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(
            part_name="my-part", env=path, properties=properties
        )
        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert raised.value.reason == f"'{missing_dependency_name}' not found"

    @pytest.mark.parametrize(
        "dependencies",
        [
            ("cargo", ["rustc"]),
            ("rustc", ["cargo"]),
        ],
    )
    def test_validate_environment_broken_dependencies(
        self, dependencies, dependency_fixture, part_info
    ):
        """Validate that broken dependencies raise an exception.

        :param dependencies: tuple consisting of 1 broken dependency
        and a list of valid dependencies
        """
        broken_dependency_name, valid_dependency_names = dependencies
        broken_dependency = dependency_fixture(broken_dependency_name, broken=True)
        path = f"PATH={str(broken_dependency.parent)}"

        for valid_dependencies_name in valid_dependency_names:
            valid_dependency = dependency_fixture(valid_dependencies_name)
            path += f":{str(valid_dependency.parent)}"

        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(
            part_name="my-part", env=path, properties=properties
        )
        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert (
            raised.value.reason
            == f"'{broken_dependency_name}' failed with error code 33"
        )

    def test_validate_environment_part_dependencies(self, part_info):
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(
            part_name="my-part", env="PATH=/foo", properties=properties
        )
        validator.validate_environment(part_dependencies=["rust-deps"])

    @pytest.mark.parametrize(
        "satisfied_dependency,error_dependency",
        [
            ("cargo", "rustc"),
            ("rustc", "cargo"),
        ],
    )
    def test_validate_environment_missing_part_dependencies(
        self,
        satisfied_dependency,
        error_dependency,
        dependency_fixture,
        new_dir,
        part_info,
    ):
        """Validate that missing part dependencies raise an exception.

        :param dependencies: tuple consisting of 1 missing part dependency
        and a list of valid part dependencies
        """
        dependency = dependency_fixture(name=satisfied_dependency)

        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        validator = plugin.validator_class(
            part_name="my-part",
            properties=properties,
            env=f"PATH={str(dependency.parent)}",
        )
        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment(part_dependencies=[])

        assert raised.value.reason == (
            f"{error_dependency!r} not found and part 'my-part' "
            "does not depend on a part named 'rust-deps' that "
            "would satisfy the dependency"
        )

    def test_get_build_snaps(self, part_info):
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)
        assert plugin.get_build_snaps() == set()

    def test_get_build_packages(self, part_info):
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)
        assert plugin.get_build_packages() == {"gcc", "git"}

    def test_get_build_environment(self, part_info):
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_environment() == {
            "PATH": "${HOME}/.cargo/bin:${PATH}",
        }

    def test_get_build_commands(self, part_info):
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            'cargo install --locked --path . --root "${CRAFT_PART_INSTALL}" --force',
        ]

    def test_get_build_commands_rust_features(self, part_info):
        properties = RustPlugin.properties_class.unmarshal(
            {"source": ".", "rust-features": ["test-feature-1", "test-feature-2"]}
        )
        plugin = RustPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            'cargo install --locked --path . --root "${CRAFT_PART_INSTALL}" --force '
            "--features 'test-feature-1 test-feature-2'",
        ]

    @pytest.mark.parametrize(
        "rust_features",
        [None, "i am a string", {"i am": "a dictionary"}, ["duplicate", "duplicate"]],
    )
    def test_get_build_commands_rust_features_invalid(self, rust_features, part_info):
        with pytest.raises(ValidationError):
            RustPlugin.properties_class.unmarshal(
                {"source": ".", "rust-features": rust_features}
            )

    def test_get_build_commands_rust_path(self, part_info):
        properties = RustPlugin.properties_class.unmarshal(
            {"source": ".", "rust-path": ["test-path-1", "test-path-2"]}
        )
        plugin = RustPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            "cargo install --locked --path test-path-1"
            ' --root "${CRAFT_PART_INSTALL}" --force',
        ]

    @pytest.mark.parametrize(
        "rust_path",
        [None, "i am a string", {"i am": "a dictionary"}, ["duplicate", "duplicate"]],
    )
    def test_get_build_commands_rust_path_invalid(self, rust_path, part_info):
        with pytest.raises(ValidationError):
            RustPlugin.properties_class.unmarshal(
                {"source": ".", "rust-path": rust_path}
            )

    def test_get_out_of_source_build(self, part_info):
        properties = RustPlugin.properties_class.unmarshal({"source": "."})
        plugin = RustPlugin(properties=properties, part_info=part_info)

        assert plugin.get_out_of_source_build() is False
