# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021,2024 Canonical Ltd.
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

"""Definitions and helpers to handle plugins."""

import copy
from typing import TYPE_CHECKING, Any

from craft_parts import errors

from .ant_plugin import AntPlugin
from .autotools_plugin import AutotoolsPlugin
from .base import Plugin
from .cargo_use_plugin import CargoUsePlugin
from .cmake_plugin import CMakePlugin
from .dotnet_plugin import DotnetPlugin
from .dump_plugin import DumpPlugin
from .go_plugin import GoPlugin
from .go_use_plugin import GoUsePlugin
from .gradle_plugin import GradlePlugin
from .jlink_plugin import JLinkPlugin
from .make_plugin import MakePlugin
from .maven_plugin import MavenPlugin
from .maven_use_plugin import MavenUsePlugin
from .meson_plugin import MesonPlugin
from .nil_plugin import NilPlugin
from .npm_plugin import NpmPlugin
from .poetry_plugin import PoetryPlugin
from .properties import PluginProperties
from .python_plugin import PythonPlugin
from .qmake_plugin import QmakePlugin
from .rust_plugin import RustPlugin
from .scons_plugin import SConsPlugin
from .uv_plugin import UvPlugin

if TYPE_CHECKING:
    # import module to avoid circular imports in sphinx doc generation
    from craft_parts import infos, parts

PluginType = type[Plugin]

# build-attributes that require plugin support.
PLUGINS_BUILD_ATTRIBUTES = {"self-contained"}


# Plugin registry by plugin API version
_BUILTIN_PLUGINS: dict[str, PluginType] = {
    "ant": AntPlugin,
    "autotools": AutotoolsPlugin,
    "cargo-use": CargoUsePlugin,
    "cmake": CMakePlugin,
    "dotnet": DotnetPlugin,
    "dump": DumpPlugin,
    "go": GoPlugin,
    "go-use": GoUsePlugin,
    "gradle": GradlePlugin,
    "jlink": JLinkPlugin,
    "make": MakePlugin,
    "maven": MavenPlugin,
    "maven-use": MavenUsePlugin,
    "meson": MesonPlugin,
    "nil": NilPlugin,
    "npm": NpmPlugin,
    "poetry": PoetryPlugin,
    "python": PythonPlugin,
    "qmake": QmakePlugin,
    "rust": RustPlugin,
    "scons": SConsPlugin,
    "uv": UvPlugin,
}

_PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)


def get_plugin(
    *,
    part: "parts.Part",
    part_info: "infos.PartInfo",
    properties: PluginProperties,
) -> Plugin:
    """Obtain a plugin instance for the specified part.

    :param part: The part requesting the plugin.
    :param part_info: The part information data.
    :param properties: The plugin properties.

    :return: The plugin instance.
    """
    plugin_name = part.plugin_name if part.plugin_name else part.name
    plugin_class = get_plugin_class(plugin_name)

    return plugin_class(properties=properties, part_info=part_info)


def get_plugin_class(name: str) -> PluginType:
    """Obtain a plugin class given the name.

    :param name: The plugin name.

    :return: The plugin class.

    :raise ValueError: If the plugin name is invalid.
    """
    if name not in _PLUGINS:
        raise ValueError(f"plugin not registered: {name!r}")

    return _PLUGINS[name]


def get_registered_plugins() -> dict[str, PluginType]:
    """Return the list of currently registered plugins."""
    return copy.deepcopy(_PLUGINS)


def register(plugins: dict[str, PluginType]) -> None:
    """Register part handler plugins.

    :param plugins: a dictionary where the keys are plugin names and values
        are plugin classes. Valid plugins must subclass class:`Plugin`.
    """
    _PLUGINS.update(plugins)


def unregister(*plugins: str) -> None:
    """Unregister plugins by name."""
    for plugin in plugins:
        _PLUGINS.pop(plugin, None)


def unregister_all() -> None:
    """Unregister all user-registered plugins."""
    global _PLUGINS  # noqa: PLW0603
    _PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)


def extract_part_properties(
    data: dict[str, Any], *, plugin_name: str
) -> dict[str, Any]:
    """Get common part properties without plugin-specific entries.

    :param data: A dictionary containing all part properties.
    :param plugin_name: The name of the plugin.

    :return: A dictionary containing only common part properties.
    """
    prefix = f"{plugin_name}-"
    return {k: v for k, v in data.items() if not k.startswith(prefix)}


def validate_build_attributes(data: dict[str, Any], *, plugin_name: str) -> None:
    """Validate that the build-attributes are compatible with the plugin."""
    plugin_class = get_plugin_class(plugin_name)
    build_attributes = data.get("build-attributes", [])

    # Plugin-related build attributes requested by the user
    user_attributes = {
        attr for attr in build_attributes if attr in PLUGINS_BUILD_ATTRIBUTES
    }

    # build attributes that the plugin itself supports
    plugin_attributes = plugin_class.supported_build_attributes()

    if unsupported := user_attributes - plugin_attributes:
        raise errors.UnsupportedBuildAttributesError(unsupported, plugin_name)


def validate_and_extract(data: dict[str, Any], *, plugin_name: str) -> dict[str, Any]:
    """Validate plugin-related attributes and extract common part properties.

    :param data: A dictionary containing all part properties.
    :param plugin_name: The name of the plugin.

    :return: A dictionary containing only common part properties.
    """
    validate_build_attributes(data, plugin_name=plugin_name)
    return extract_part_properties(data, plugin_name=plugin_name)
