# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

"""The fpc-use plugin."""

import shlex
from typing import Literal, cast

from typing_extensions import override

from craft_parts.constraints import UniqueList

from .base import Plugin
from .properties import PluginProperties

FPC_USE_DIR = "fpc-use"
"""Name of the backstage directory holding the exports of fpc-use parts."""


class FpcUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the fpc-use plugin."""

    plugin: Literal["fpc-use"] = "fpc-use"

    fpc_use_unit_paths: UniqueList[str] = ["."]
    fpc_use_include_paths: UniqueList[str] = []

    # part properties required by the plugin
    source: str


class FpcUsePlugin(Plugin):
    """A plugin to make Free Pascal units available to other parts.

    The part's source is exported to the backstage area, where parts using the
    fpc plugin that come after this part pick it up as unit and include search
    paths. Nothing is compiled or installed by this plugin.

    The fpc-use plugin uses the common plugin keys as well as those for
    "sources". Additionally, the following plugin-specific keys can be used:

    - ``fpc-use-unit-paths``
      (list of strings)
      Directories containing units, relative to the source directory. Default
      is the source directory itself.
    - ``fpc-use-include-paths``
      (list of strings)
      Directories containing include files, relative to the source directory.
      Default is not to export any include search paths.
    """

    properties_class = FpcUsePluginProperties

    @classmethod
    @override
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(FpcUsePluginProperties, self._options)

        export_dir = (
            self._part_info.part_export_dir / FPC_USE_DIR / self._part_info.part_name
        )
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "unit-paths").write_text(
            "".join(f"{path}\n" for path in options.fpc_use_unit_paths)
        )
        (export_dir / "include-paths").write_text(
            "".join(f"{path}\n" for path in options.fpc_use_include_paths)
        )

        source = shlex.quote(str(self._part_info.part_src_subdir))
        return [f"ln -sfn {source} {shlex.quote(str(export_dir / 'source'))}"]
