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
import textwrap
from pathlib import Path
from typing import Literal

import craft_parts
import pytest
import yaml
from craft_parts import Step, errors, plugins


@pytest.fixture
def mytool(new_dir):
    tool = Path(new_dir, "mock_bin", "mytool")
    tool.parent.mkdir(exist_ok=True)
    tool.write_text("echo ok")
    tool.chmod(0o755)
    return tool


@pytest.fixture
def mytool_not_ok(new_dir):
    tool = Path(new_dir, "mock_bin", "mytool")
    tool.parent.mkdir(exist_ok=True)
    tool.write_text("echo not ok")
    tool.chmod(0o755)
    return tool


@pytest.fixture
def mytool_error(new_dir):
    tool = Path(new_dir, "mock_bin", "mytool")
    tool.parent.mkdir(exist_ok=True)
    tool.write_text("exit 22")
    tool.chmod(0o755)
    return tool


class AppPluginProperties(plugins.PluginProperties, frozen=True):
    """The application-defined plugin properties."""

    plugin: Literal["app"] = "app"


class AppPluginEnvironmentValidator(plugins.PluginEnvironmentValidator):
    """Check the execution environment for the app plugin."""

    def validate_environment(self, *, part_dependencies: list[str] | None = None):
        """Ensure the environment contains dependencies needed by the plugin.

        If mytool is created by a part, that part must be named `mytool`.
        """
        try:
            output = self._execute("mytool")
            if output.strip() != "ok":
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="mytool is expected to print ok",
                )
        except subprocess.CalledProcessError as err:
            if err.returncode != plugins.validator.COMMAND_NOT_FOUND:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"mytool failed with error code {err.returncode}",
                ) from err

            if part_dependencies is None:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="mytool not found",
                ) from err

            if "mytool" not in part_dependencies:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=(
                        f"mytool not found and part {self._part_name!r} "
                        f"does not depend on a part named 'mytool'"
                    ),
                ) from err


class AppPlugin(plugins.Plugin):
    """Our application plugin."""

    properties_class = AppPluginProperties
    validator_class = AppPluginEnvironmentValidator

    def validate_environment(self, env: dict[str, str]):
        try:
            subprocess.run("mytool", check=True, env=env)
        except subprocess.CalledProcessError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_info.part_name,
                reason="mytool not found",
            ) from err

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return []


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


def test_validate_plugin(new_dir, partitions, mytool):
    _parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: app
            build-environment:
              - PATH: "$PATH:{new_dir}/mock_bin"
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="mytest", cache_dir=new_dir, partitions=partitions
    )

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)

    with lf.action_executor() as exe:
        exe.execute(actions)


def test_validate_plugin_satisfied_with_part(new_dir, partitions):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
            after: [mytool]
          mytool:
            plugin: nil
            override-build: |
              mkdir "$CRAFT_PART_INSTALL"/bin
              echo "echo ok" > "$CRAFT_PART_INSTALL"/bin/mytool
              chmod +x "$CRAFT_PART_INSTALL"/bin/mytool
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="mytest", cache_dir=new_dir, partitions=partitions
    )

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)

    with lf.action_executor() as exe:
        exe.execute(actions)


def test_validate_plugin_early_error(new_dir, partitions):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="mytest", cache_dir=new_dir, partitions=partitions
    )

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        with lf.action_executor() as exe:
            exe.execute(actions)
    assert raised.value.reason == (
        "mytool not found and part 'foo' does not depend on a part named 'mytool'"
    )


def test_validate_plugin_bad_output(new_dir, partitions, mytool_not_ok):
    _parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: app
            build-environment:
              - PATH: "$PATH:{new_dir}/mock_bin"
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="mytest", cache_dir=new_dir, partitions=partitions
    )

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        with lf.action_executor() as exe:
            exe.execute(actions)
    assert raised.value.reason == "mytool is expected to print ok"


def test_validate_plugin_command_error(new_dir, partitions, mytool_error):
    _parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: app
            build-environment:
              - PATH: "$PATH:{new_dir}/mock_bin"
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="mytest", cache_dir=new_dir, partitions=partitions
    )

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        with lf.action_executor() as exe:
            exe.execute(actions)
    assert raised.value.reason == "mytool failed with error code 22"
