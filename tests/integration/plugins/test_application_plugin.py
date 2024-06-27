# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Set

import craft_parts
import pytest
import yaml
from craft_parts import Action, ActionType, Step, errors, plugins
from craft_parts.utils.process_utils import DEFAULT_STDERR, DEFAULT_STDOUT


class AppPluginProperties(plugins.PluginProperties, plugins.PluginModel):
    """The application-defined plugin properties."""

    app_stuff: List[str]
    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        plugin_data = plugins.extract_plugin_properties(
            data, plugin_name="app", required=["source"]
        )
        return cls(**plugin_data)


class AppPlugin(plugins.Plugin):
    """Our application plugin."""

    properties_class = AppPluginProperties

    def get_build_snaps(self) -> Set[str]:
        return {"build_snap"}

    def get_build_packages(self) -> Set[str]:
        return {"build_package"}

    def get_build_environment(self) -> Dict[str, str]:
        return {"PARTS_TEST_VAR": "application plugin"}

    def get_build_commands(self) -> List[str]:
        return ["echo hello ${PARTS_TEST_VAR}"]


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


def test_application_plugin_happy(new_dir, partitions, mocker):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
            source: .
            app-stuff:
            - first
            - second
            - third
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)
    old_parts = parts.copy()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_application_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.RUN),
        Action("foo", Step.BUILD, action_type=ActionType.RUN),
    ]

    mock_install_packages = mocker.patch(
        "craft_parts.packages.Repository.install_packages"
    )

    mock_install_snaps = mocker.patch("craft_parts.packages.snaps.install_snaps")

    output_path = Path("output.txt")
    error_path = Path("error.txt")

    with output_path.open("w") as output, error_path.open("w") as error:
        with lf.action_executor() as exe:
            exe.execute(actions[1], stdout=output, stderr=error)

    assert output_path.read_text() == "hello application plugin\n"
    assert error_path.read_text() == "+ echo hello application plugin\n"

    mock_install_packages.assert_called_once_with(
        ["build_package"],
        stdout=DEFAULT_STDOUT,
        stderr=DEFAULT_STDERR,
    )
    mock_install_snaps.assert_called_once_with({"build_snap"})

    # make sure parts data was not changed
    assert parts == old_parts


def test_application_plugin_missing_stuff(new_dir, partitions):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
            source: .
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    with pytest.raises(errors.PartSpecificationError) as raised:
        craft_parts.LifecycleManager(
            parts,
            application_name="test_application_plugin",
            cache_dir=new_dir,
            partitions=partitions,
        )

    assert raised.value.part_name == "foo"
    assert raised.value.message == "- field 'app-stuff' is required"


def test_application_plugin_type_error(new_dir, partitions):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
            source: .
            app-stuff: "some stuff"
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    with pytest.raises(errors.PartSpecificationError) as raised:
        craft_parts.LifecycleManager(
            parts,
            application_name="test_application_plugin",
            cache_dir=new_dir,
            partitions=partitions,
        )

    assert raised.value.part_name == "foo"
    assert raised.value.message == "- value is not a valid list in field 'app-stuff'"


def test_application_plugin_extra_property(new_dir, partitions):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
            source: .
            app-stuff: ["value"]
            app-other: True
        """
    )

    # register our application plugin
    plugins.register({"app": AppPlugin})

    parts = yaml.safe_load(_parts_yaml)

    with pytest.raises(errors.PartSpecificationError) as raised:
        craft_parts.LifecycleManager(
            parts,
            application_name="test_application_plugin",
            cache_dir=new_dir,
            partitions=partitions,
        )

    assert raised.value.part_name == "foo"
    assert raised.value.message == "- extra field 'app-other' not permitted"


def test_application_plugin_not_registered(new_dir, partitions):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: app
            source: .
        """
    )

    # don't register our application plugin
    parts = yaml.safe_load(_parts_yaml)

    with pytest.raises(errors.InvalidPlugin) as raised:
        craft_parts.LifecycleManager(
            parts,
            application_name="test_application_plugin",
            cache_dir=new_dir,
            partitions=partitions,
        )

    assert raised.value.plugin_name == "app"
    assert raised.value.part_name == "foo"
