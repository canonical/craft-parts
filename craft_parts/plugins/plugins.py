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

"""Definitions and helpers to handle plugins."""

import copy
from typing import TYPE_CHECKING, Any, Dict, Type

from .autotools_plugin import AutotoolsPlugin
from .base import Plugin
from .cmake_plugin import CMakePlugin
from .dotnet_plugin import DotnetPlugin
from .dump_plugin import DumpPlugin
from .go_plugin import GoPlugin
from .make_plugin import MakePlugin
from .meson_plugin import MesonPlugin
from .nil_plugin import NilPlugin
from .npm_plugin import NpmPlugin
from .properties import PluginProperties
from .python_plugin import PythonPlugin
from .rust_plugin import RustPlugin

if TYPE_CHECKING:
    # import module to avoid circular imports in sphinx doc generation
    from craft_parts import infos, parts


PluginType = Type[Plugin]


# Plugin registry by plugin API version
_BUILTIN_PLUGINS: Dict[str, PluginType] = {
    "autotools": AutotoolsPlugin,
    "cmake": CMakePlugin,
    "dotnet": DotnetPlugin,
    "dump": DumpPlugin,
    "go": GoPlugin,
    "meson": MesonPlugin,
    "make": MakePlugin,
    "nil": NilPlugin,
    "npm": NpmPlugin,
    "python": PythonPlugin,
    "rust": RustPlugin,
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


def get_registered_plugins() -> Dict[str, PluginType]:
    """Return the list of currently registered plugins."""
    return copy.deepcopy(_PLUGINS)


def register(plugins: Dict[str, PluginType]) -> None:
    """Register part handler plugins.

    :param plugins: a dictionary where the keys are plugin names and values
        are plugin classes. Valid plugins must subclass class:`Plugin`.
    """
    _PLUGINS.update(plugins)


def unregister_all() -> None:
    """Unregister all user-registered plugins."""
    global _PLUGINS  # pylint: disable=global-statement
    _PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)


def extract_part_properties(
    data: Dict[str, Any], *, plugin_name: str
) -> Dict[str, Any]:
    """Get common part properties without plugin-specific entries.

    :param data: A dictionary containing all part properties.
    :param plugin_name: The name of the plugin.

    :return: A dictionary containing only common part properties.
    """
    prefix = f"{plugin_name}-"
    return {k: v for k, v in data.items() if not k.startswith(prefix)}
