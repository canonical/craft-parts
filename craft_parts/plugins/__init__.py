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

"""Craft Parts plugins subsystem."""

from .base import PluginModel, extract_plugin_properties
from .plugins import (
    Plugin,
    PluginProperties,
    extract_part_properties,
    get_plugin,
    get_plugin_class,
    get_registered_plugins,
    register,
    unregister_all,
)
from .validator import PluginEnvironmentValidator

__all__ = [
    "Plugin",
    "PluginEnvironmentValidator",
    "PluginModel",
    "PluginProperties",
    "extract_part_properties",
    "extract_plugin_properties",
    "get_plugin",
    "get_plugin_class",
    "get_registered_plugins",
    "register",
    "unregister_all",
]
