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

"""The new .NET plugin."""

import logging
from typing import Literal, cast

from overrides import override

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class DotnetV2PluginProperties(PluginProperties, frozen=True):
    """The part properties used by the .NET plugin."""

    plugin: Literal["dotnet"] = "dotnet"

    # Global flags
    dotnet_configuration: str = "Release"
    dotnet_project: str | None = None
    dotnet_self_contained: bool = False
    dotnet_verbosity: str = "normal"
    dotnet_version: str | None = None

    # Restore specific flags
    dotnet_restore_sources: list[str] = []
    dotnet_restore_configfile: str | None = None

    # Build specific flags
    dotnet_build_framework: str | None = None

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class DotnetV2PluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Dotnet plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.
        """
        self.validate_dependency(
            dependency="dotnet",
            plugin_name="dotnet",
            part_dependencies=part_dependencies,
        )


class DotnetV2Plugin(Plugin):
    """A plugin for .NET projects.

    The .NET plugin uses the common plugin keywords as well as those for "sources".
    Additionally, the following plugin-specific keywords can be used:

    Global Flags:

    - ``dotnet-configuration``
      (string)
      The .NET build configuration to use. (Default: "Release").

    - ``dotnet-project``
      (string)
      The .NET proj or solution file to build. (Default: ommited).

    - ``dotnet-self-contained``
      (bool)
      Build and publish the project as a self-contained application. (Default: False).

    - ``dotnet-verbosity``
      (string)
      The verbosity level of the build output. Possible values are q[uiet], m[inimal],
      n[ormal], d[etailed], and diag[nostic]. (Default: "normal").

    - ``dotnet-version``
      (string)
      The version of the .NET SDK to download and use. This parameter is optional, so if
      no value is specified, the plugin will assume a .NET SDK is being provided and will
      not attempt to download one.

    Restore-specific Flags:

    - ``dotnet-restore-sources``
      (string)
      The URI of the NuGet package sources to use during the restore operation.
      Multiple values can be specified. This setting overrides all of the sources
      specified in the nuget.config files.
      (Default: ommited).

    - ``dotnet-restore-configfile``
      (string)
      The NuGet configuration file (nuget.config) to use. (Default: ommited).

    Build-specific Flags:

    - ``dotnet-build-framework``
      (string)
      The target framework to build for. (Default: ommited).
    """

    properties_class = DotnetV2PluginProperties
    validator_class = DotnetV2PluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        options = cast(DotnetV2PluginProperties, self._options)

        # .NET binary provided by the user
        if "dotnet-deps" in self._part_info.part_dependencies or options.dotnet_version is None:
            return set()

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
        options = cast(DotnetV2PluginProperties, self._options)

        environment = {
            "DOTNET_NOLOGO": "1",
        }

        # .NET binary provided by the user
        if "dotnet-deps" in self._part_info.part_dependencies:
            return environment

        build_on = self._part_info.project_info.arch_build_on
        snap_name = self._generate_snap_name(options)

        if (build_on == "amd64"):
            environment["LD_LIBRARY_PATH"] = f"/snap/{snap_name}/current/lib/x86_64-linux-gnu:/snap/{snap_name}/current/usr/lib/x86_64-linux-gnu"
        elif (build_on == "arm64"):
            environment["LD_LIBRARY_PATH"] = f"/snap/{snap_name}/current/lib/aarch64-linux-gnu:/snap/{snap_name}/current/usr/lib/aarch64-linux-gnu"
        else:
            raise ValueError(f"Unsupported architecture: {build_on}")

        snap_location = f"/snap/{self._generate_snap_name(options)}/current"
        dotnet_path = f"{snap_location}/usr/lib/dotnet"
        environment["PATH"] = f"{dotnet_path}:${{PATH}}"

        logger.info(f"Using environment:")
        for key, value in environment.items():
            logger.info(f"  {key}={value}")

        return environment

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(DotnetV2PluginProperties, self._options)

        # Check if version is valid
        self._generate_snap_name(options)

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
        if options.dotnet_verbosity not in ["quiet", "q", "minimal", "m", "normal", "n", "detailed", "d", "diagnostic", "diag"]:
            raise ValueError("Invalid verbosity level")

        # Restore step
        restore_cmd = self._get_restore_command(dotnet_rid, options)

        # Build step
        build_cmd = self._get_build_command(dotnet_rid, options)

        # Publish step
        publish_cmd = self._get_publish_command(dotnet_rid, options)

        return [restore_cmd, build_cmd, publish_cmd]

    def _generate_snap_name(self, options: DotnetV2PluginProperties) -> str | None:
        version = options.dotnet_version
        if version is None:
            return None

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

    def _get_restore_command(self, dotnet_rid: str, options: DotnetV2PluginProperties) -> str:
        restore_cmd = "dotnet restore"

        if options.dotnet_restore_sources:
            logger.info(f"Using restore sources: {options.dotnet_restore_sources}")
            for source in options.dotnet_restore_sources:
                restore_cmd += f" --source {source}"
        if options.dotnet_restore_configfile:
            restore_cmd += f" --configfile {options.dotnet_restore_configfile}"

        restore_cmd += f" --verbosity {options.dotnet_verbosity}"
        restore_cmd += f" --runtime {dotnet_rid}"

        if options.dotnet_project:
            restore_cmd += f" {options.dotnet_project}"

        return restore_cmd
    
    def _get_build_command(self, dotnet_rid: str, options: DotnetV2PluginProperties) -> str:
        build_cmd = (
            "dotnet build "
            f"--configuration {options.dotnet_configuration} "
            f"--no-restore"
        )

        if options.dotnet_build_framework:
            build_cmd += f" --framework {options.dotnet_build_framework}"

        build_cmd += f" --verbosity {options.dotnet_verbosity}"

        # Self contained build
        build_cmd += f" --runtime {dotnet_rid}"
        build_cmd += f" --self-contained {options.dotnet_self_contained}"

        if options.dotnet_project:
            build_cmd += f" {options.dotnet_project}"

        return build_cmd
    
    def _get_publish_command(self, dotnet_rid: str, options: DotnetV2PluginProperties) -> str:
        publish_cmd = (
            "dotnet publish "
            f"--configuration {options.dotnet_configuration} "
            f"--output {self._part_info.part_install_dir} "
            f"--verbosity {options.dotnet_verbosity} "
            "--no-restore --no-build"
        )

        # Self contained build
        publish_cmd += f" --runtime {dotnet_rid}"
        publish_cmd += f" --self-contained {options.dotnet_self_contained}"

        if options.dotnet_project:
            publish_cmd += f" {options.dotnet_project}"

        return publish_cmd
