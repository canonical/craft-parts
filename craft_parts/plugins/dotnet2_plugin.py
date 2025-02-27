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

"""The .NET plugin."""

import logging
from typing import Literal, cast

from overrides import override

from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class Dotnet2PluginProperties(PluginProperties, frozen=True):
    """The part properties used by the .NET plugin."""

    plugin: Literal["dotnet2"] = "dotnet2"

    # Global flags
    dotnet2_configuration: str = "Release"
    dotnet2_project: str | None = None
    dotnet2_self_contained: bool = False
    dotnet2_verbosity: str = "normal"
    dotnet2_version: str = "8.0"

    # Restore specific flags
    dotnet2_restore_sources: list[str] = []
    dotnet2_restore_configfile: str | None = None

    # Build specific flags
    dotnet2_build_framework: str | None = None

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class Dotnet2Plugin(Plugin):
    """A plugin for .NET projects.

    The .NET plugin uses the common plugin keywords as well as those for "sources".
    Additionally, the following plugin-specific keywords can be used:

    Global Flags:

    - ``dotnet2-configuration``
      (string)
      The .NET build configuration to use. (Default: "Release").

    - ``dotnet2-project``
      (string)
      The .NET proj or solution file to build. (Default: ommited).

    - ``dotnet2-self-contained``
      (bool)
      Build and publish the project as a self-contained application. (Default: False).

    - ``dotnet2-verbosity``
      (string)
      The verbosity level of the build output. Possible values are q[uiet], m[inimal],
      n[ormal], d[etailed], and diag[nostic]. (Default: "normal").

    - ``dotnet2-version``
      (string)
      The version of the .NET SDK to use. (Default: "8.0").

    Restore-specific Flags:

    - ``dotnet2-restore-sources``
      (string)
      The URI of the NuGet package sources to use during the restore operation.
      Multiple values can be specified. This setting overrides all of the sources
      specified in the nuget.config files.
      (Default: ommited).

    - ``dotnet2-restore-configfile``
      (string)
      The NuGet configuration file (nuget.config) to use. (Default: ommited).

    Build-specific Flags:

    - ``dotnet2-build-framework``
      (string)
      The target framework to build for. (Default: ommited).
    """

    properties_class = Dotnet2PluginProperties

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        options = cast(Dotnet2PluginProperties, self._options)

        snap_name = self._generate_snap_name(options)
        logger.info(f"Using .NET SDK content snap: {snap_name}")

        build_snaps = set()
        build_snaps.add(snap_name)

        return build_snaps

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        options = cast(Dotnet2PluginProperties, self._options)

        environment = {
            "DOTNET_NOLOGO": "1",
        }

        build_on = self._part_info.project_info.arch_build_on
        snap_name = self._generate_snap_name(options)

        if (build_on == "amd64"):
            environment["LD_LIBRARY_PATH"] = f"/snap/{snap_name}/current/lib/x86_64-linux-gnu:/snap/{snap_name}/current/usr/lib/x86_64-linux-gnu"
        elif (build_on == "arm64"):
            environment["LD_LIBRARY_PATH"] = f"/snap/{snap_name}/current/lib/aarch64-linux-gnu:/snap/{snap_name}/current/usr/lib/aarch64-linux-gnu"
        else:
            raise ValueError(f"Unsupported architecture: {build_on}")

        logger.info(f"Using environment:")
        for key, value in environment.items():
            logger.info(f"  {key}={value}")

        return environment

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(Dotnet2PluginProperties, self._options)

        # Locate the dotnet executable from the dotnet-sdk snap
        snap_location = f"/snap/{self._generate_snap_name(options)}/current"
        dotnet_path = f"{snap_location}/usr/lib/dotnet"

        # Runtime identifier
        _DEBIAN_ARCH_TO_DOTNET_RID = {
            "amd64": "linux-x64",
            "arm64": "linux-arm64"
        }

        build_for = self._part_info.project_info.arch_build_for
        dotnet_rid = _DEBIAN_ARCH_TO_DOTNET_RID.get(build_for, None)

        if not dotnet_rid:
            raise ValueError(f"Unsupported architecture: {build_for}")
        
        # Validate verbosity
        if options.dotnet2_verbosity not in ["quiet", "q", "minimal", "m", "normal", "n", "detailed", "d", "diagnostic", "diag"]:
            raise ValueError("Invalid verbosity level")

        # Restore step
        restore_cmd = self._get_restore_command(dotnet_path, dotnet_rid, options)

        # Build step
        build_cmd = self._get_build_command(dotnet_path, dotnet_rid, options)

        # Publish step
        publish_cmd = self._get_publish_command(dotnet_path, dotnet_rid, options)

        return [restore_cmd, build_cmd, publish_cmd]

    def _generate_snap_name(self, options: Dotnet2PluginProperties) -> str:
        version = options.dotnet2_version

        # Validate version
        if len(version.split('.')) == 1:
            if not version.isdigit() or int(version) < 6:
                raise ValueError("Version must be greater or equal to 6.0")
            snap_version = f"{version}0"
        elif len(version.split('.')) > 1:
            major, minor = version.split('.')
            if not (major.isdigit() and minor.isdigit()) or int(major) < 6:
                raise ValueError("Version must be greater or equal to 6.0")
            snap_version = major + minor
        else:
            raise ValueError("Invalid .NET version format")

        snap_name = f"dotnet-sdk-{snap_version}"
        return snap_name

    def _get_restore_command(self, dotnet_path: str, dotnet_rid: str, options: Dotnet2PluginProperties) -> str:
        restore_cmd = f"{dotnet_path}/dotnet restore"
        if options.dotnet2_project:
            restore_cmd += f" {options.dotnet2_project}"

        if options.dotnet2_restore_sources:
            logger.info(f"Using restore sources: {options.dotnet2_restore_sources}")
            for source in options.dotnet2_restore_sources:
                restore_cmd += f" --source {source}"
        if options.dotnet2_restore_configfile:
            restore_cmd += f" --configfile {options.dotnet2_restore_configfile}"

        restore_cmd += f" --verbosity {options.dotnet2_verbosity}"
        restore_cmd += f" --runtime {dotnet_rid}"

        return restore_cmd
    
    def _get_build_command(self, dotnet_path: str, dotnet_rid: str, options: Dotnet2PluginProperties) -> str:
        build_cmd = (
            f"{dotnet_path}/dotnet build "
            f"--configuration {options.dotnet2_configuration} "
            f"--no-restore"
        )

        if options.dotnet2_build_framework:
            build_cmd += f" --framework {options.dotnet2_build_framework}"

        build_cmd += f" --verbosity {options.dotnet2_verbosity}"

        # Self contained build
        build_cmd += f" --runtime {dotnet_rid}"
        build_cmd += f" --self-contained {options.dotnet2_self_contained}"

        if options.dotnet2_project:
            build_cmd += f" {options.dotnet2_project}"

        return build_cmd
    
    def _get_publish_command(self, dotnet_path: str, dotnet_rid: str, options: Dotnet2PluginProperties) -> str:
        publish_cmd = (
            f"{dotnet_path}/dotnet publish "
            f"--configuration {options.dotnet2_configuration} "
            f"--output {self._part_info.part_install_dir} "
            f"--verbosity {options.dotnet2_verbosity} "
            "--no-restore --no-build"
        )

        if options.dotnet2_project:
            publish_cmd += f" {options.dotnet2_project}"

        # Self contained build
        publish_cmd += f" --runtime {dotnet_rid}"
        publish_cmd += f" --self-contained {options.dotnet2_self_contained}"

        return publish_cmd
