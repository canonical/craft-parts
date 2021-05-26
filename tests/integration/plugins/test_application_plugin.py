# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import textwrap
from typing import Any, Dict, List, Set

import pytest
import yaml

import craft_parts
from craft_parts import Action, ActionType, Step, errors, plugins


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


def teardown_function():
    plugins.unregister_all()


@pytest.mark.usefixtures("new_dir")
def test_application_plugin_happy(capfd, mocker):
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

    lf = craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.RUN),
        Action("foo", Step.BUILD, action_type=ActionType.RUN),
    ]

    mock_install_build_packages = mocker.patch(
        "craft_parts.packages.Repository.install_build_packages"
    )

    mock_install_build_snaps = mocker.patch("craft_parts.packages.snaps.install_snaps")

    with lf.action_executor() as exe:
        exe.execute(actions[1])

    out, _ = capfd.readouterr()
    assert out == "hello application plugin\n"

    mock_install_build_packages.assert_called_once_with(["build_package"])
    mock_install_build_snaps.assert_called_once_with({"build_snap"})


@pytest.mark.usefixtures("new_dir")
def test_application_plugin_missing_stuff():
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
        craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    assert raised.value.part_name == "foo"
    assert raised.value.message == "'app-stuff': field required"


@pytest.mark.usefixtures("new_dir")
def test_application_plugin_type_error():
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
        craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    assert raised.value.part_name == "foo"
    assert raised.value.message == "'app-stuff': value is not a valid list"


@pytest.mark.usefixtures("new_dir")
def test_application_plugin_extra_property():
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
        craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    assert raised.value.part_name == "foo"
    assert raised.value.message == "'app-other': extra fields not permitted"


@pytest.mark.usefixtures("new_dir")
def test_application_plugin_not_registered():
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
        craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    assert raised.value.plugin_name == "app"
    assert raised.value.part_name == "foo"
