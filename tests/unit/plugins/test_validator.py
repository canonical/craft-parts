# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import subprocess
from pathlib import Path
from typing import Literal

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin, PluginEnvironmentValidator, PluginProperties


@pytest.fixture
def foo_exe(new_dir):
    exe = Path(new_dir, "mock_bin", "foo")
    exe.parent.mkdir(exist_ok=True)
    exe.write_text("echo bar")
    exe.chmod(0o755)
    return exe


@pytest.fixture
def empty_foo_exe(new_dir):
    exe = Path(new_dir, "mock_bin", "foo")
    exe.parent.mkdir(exist_ok=True)
    exe.touch()
    exe.chmod(0o755)
    return exe


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"plugin": "foo"}),
    )


class FooPluginProperties(PluginProperties, frozen=True):
    """Test plugin properties."""

    plugin: Literal["foo"] = "foo"


class FooPluginEnvironmentValidator(PluginEnvironmentValidator):
    """Check the execution environment for the test plugin."""

    def validate_environment(self, *, part_dependencies: list[str] | None = None):
        """Ensure the environment contains dependencies needed by the plugin.

        If the foo executable is created in a part, that part must be named
        `build-foo`.
        """
        try:
            output = self._execute("foo")
            if output.strip() != "bar":
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="foo is expected to print bar",
                )
        except subprocess.CalledProcessError as err:
            if part_dependencies is None:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="foo executable not found",
                ) from err

            if "build-foo" not in part_dependencies:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=(
                        f"foo executable not found and part {self._part_name!r} "
                        f"does not depend on a part named 'build-foo'"
                    ),
                ) from err


class FooPlugin(Plugin):
    """The test plugin."""

    properties_class = FooPluginProperties
    validator_class = FooPluginEnvironmentValidator

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return ["foo"]


def test_validation_happy(part_info, foo_exe):
    properties = FooPluginProperties()
    validator = FooPlugin.validator_class(
        part_name=part_info.part_name,
        env=f"PATH={str(foo_exe.parent)}",
        properties=properties,
    )
    validator.validate_environment()


def test_validation_error(part_info):
    properties = FooPluginProperties()
    validator = FooPlugin.validator_class(
        part_name=part_info.part_name, env="", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    err = raised.value
    assert err.part_name == "my-part"
    assert err.reason == "foo executable not found"


def test_validation_built_by_part(part_info):
    properties = FooPluginProperties()
    validator = FooPlugin.validator_class(
        part_name=part_info.part_name, env="", properties=properties
    )
    validator.validate_environment(part_dependencies=["build-foo"])


def test_validation_built_by_part_error(part_info):
    properties = FooPluginProperties()
    validator = FooPlugin.validator_class(
        part_name=part_info.part_name, env="", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    err = raised.value
    assert err.part_name == "my-part"
    assert err.reason == (
        "foo executable not found and part 'my-part' "
        "does not depend on a part named 'build-foo'"
    )


def test_validation_output_error(part_info, empty_foo_exe):
    properties = FooPluginProperties()
    validator = FooPlugin.validator_class(
        part_name=part_info.part_name,
        env=f"PATH={str(empty_foo_exe.parent)}",
        properties=properties,
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    err = raised.value
    assert err.part_name == "my-part"
    assert err.reason == "foo is expected to print bar"
