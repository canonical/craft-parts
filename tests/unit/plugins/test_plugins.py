# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021,2024 Canonical Ltd.
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
from craft_parts import plugins
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins import nil_plugin
from craft_parts.plugins.plugins import (
    AutotoolsPlugin,
    CMakePlugin,
    DotnetPlugin,
    DumpPlugin,
    GoPlugin,
    MakePlugin,
    MesonPlugin,
    NilPlugin,
    NpmPlugin,
    PythonPlugin,
    QmakePlugin,
    RustPlugin,
)


class TestGetPlugin:
    """Check plugin instantiation given the part and API version.

    The plugin is ordinarily selected using the `plugin` property defined
    in the part. If it's not defined, use the part name as a fallback.
    """

    @pytest.mark.parametrize(
        ("name", "plugin_class", "data"),
        [
            ("autotools", AutotoolsPlugin, {"source": "."}),
            ("cmake", CMakePlugin, {"source": "."}),
            ("dotnet", DotnetPlugin, {"source": "."}),
            ("dump", DumpPlugin, {"source": "."}),
            ("go", GoPlugin, {"source": "."}),
            ("make", MakePlugin, {"source": "."}),
            ("meson", MesonPlugin, {"source": "."}),
            ("nil", NilPlugin, {}),
            ("nil", NilPlugin, {"source": "."}),
            ("npm", NpmPlugin, {"source": "."}),
            ("python", PythonPlugin, {"source": "."}),
            ("qmake", QmakePlugin, {"source": "."}),
            ("rust", RustPlugin, {"source": "."}),
        ],
    )
    def test_get_plugin(self, new_dir, name, plugin_class, data):
        part = Part("foo", {"plugin": name})
        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(project_info=project_info, part=part)

        pclass = plugins.get_plugin_class(name)
        assert pclass == plugin_class

        plugin = plugins.get_plugin(
            part=part,
            part_info=part_info,
            properties=pclass.properties_class.unmarshal(data),
        )

        assert isinstance(plugin, plugin_class)

    def test_get_plugin_fallback(self, new_dir):
        part = Part("nil", {})
        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(project_info=project_info, part=part)

        plugin = plugins.get_plugin(
            part=part,
            part_info=part_info,
            properties=nil_plugin.NilPluginProperties(),
        )

        assert isinstance(plugin, nil_plugin.NilPlugin)

    def test_get_plugin_unregistered(self, new_dir):
        part = Part("foo", {"plugin": "invalid"})
        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(project_info=project_info, part=part)

        with pytest.raises(ValueError) as raised:  # noqa: PT011
            plugins.get_plugin(
                part=part,
                part_info=part_info,
                properties=None,  # type: ignore[reportGeneralTypeIssues]
            )
        assert str(raised.value) == "plugin not registered: 'invalid'"

    def test_get_plugin_unspecified(self, new_dir):
        part = Part("foo", {})
        project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(project_info=project_info, part=part)

        with pytest.raises(ValueError) as raised:  # noqa: PT011
            plugins.get_plugin(
                part=part,
                part_info=part_info,
                properties=None,  # type: ignore[reportGeneralTypeIssues]
            )
        assert str(raised.value) == "plugin not registered: 'foo'"


class FooPlugin(plugins.Plugin):
    """A test plugin."""

    properties_class = plugins.PluginProperties

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return []


class TestPluginRegistry:
    """Verify plugin register/unregister functions."""

    def test_register_unregister(self):
        with pytest.raises(ValueError):  # noqa: PT011
            plugins.get_plugin_class("plugin1")

        plugins.register(
            {
                "plugin1": FooPlugin,
                "plugin2": FooPlugin,
                "plugin3": FooPlugin,
                "plugin4": FooPlugin,
            },
        )
        foo_plugin = plugins.get_plugin_class("plugin1")
        assert foo_plugin == FooPlugin

        registered_plugins = plugins.get_registered_plugins()
        for plugin in ["plugin1", "plugin2", "plugin3"]:
            assert plugin in registered_plugins
            assert registered_plugins[plugin] == FooPlugin

        # unregister a plugin
        plugins.unregister("plugin1")
        # unregister many plugins
        plugins.unregister("plugin2", "plugin3")

        # assert plugins are unregistered
        for plugin in ["plugin1", "plugin2", "plugin3"]:
            with pytest.raises(ValueError):  # noqa: PT011
                plugins.get_plugin_class(plugin)

        # unregister all plugins
        plugins.unregister_all()
        with pytest.raises(ValueError):  # noqa: PT011
            plugins.get_plugin_class("plugin4")


class TestHelpers:
    """Verify plugin helper functions."""

    def test_extract_part_properties(self):
        data = {
            "foo": True,
            "test": "yes",
            "test-one": 1,
            "test-two": 2,
            "not-test-three": 3,
        }
        old_data = data.copy()

        new_data = plugins.extract_part_properties(data, plugin_name="test")
        assert new_data == {
            "foo": True,
            "test": "yes",
            "not-test-three": 3,
        }

        # make sure we don't destroy original data
        assert data == old_data
