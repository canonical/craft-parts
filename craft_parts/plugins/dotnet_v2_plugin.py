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
import re
from enum import Enum
from typing import Literal, cast

import pydantic
from overrides import override

from craft_parts.utils.formatting_utils import humanize_list

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)

_DEBIAN_ARCH_TO_DOTNET_RID: dict[str, str] = {
    "amd64": "linux-x64",
    "arm64": "linux-arm64",
}


class DotnetConfiguration(str, Enum):
    """The .NET build configuration."""

    DEBUG = "Debug"
    RELEASE = "Release"


class DotnetVerbosity(str, Enum):
    """The .NET build verbosity level."""

    QUIET = "quiet"
    QUIET_SHORT = "q"
    MINIMAL = "minimal"
    MINIMAL_SHORT = "m"
    NORMAL = "normal"
    NORMAL_SHORT = "n"
    DETAILED = "detailed"
    DETAILED_SHORT = "d"
    DIAGNOSTIC = "diagnostic"
    DIAGNOSTIC_SHORT = "diag"


class DotnetV2PluginProperties(PluginProperties, frozen=True):
    """The part properties used by the .NET plugin."""

    plugin: Literal["dotnet"] = "dotnet"

    # Global flags
    dotnet_configuration: DotnetConfiguration = DotnetConfiguration.RELEASE
    dotnet_project: str | None = None
    dotnet_properties: dict[str, str] = {}
    dotnet_self_contained: bool = False
    dotnet_verbosity: DotnetVerbosity = DotnetVerbosity.NORMAL
    dotnet_version: str | None = None

    # Restore specific flags
    dotnet_restore_configfile: str | None = None
    dotnet_restore_properties: dict[str, str] = {}
    dotnet_restore_sources: list[str] = []

    # Build specific flags
    dotnet_build_framework: str | None = None
    dotnet_build_properties: dict[str, str] = {}

    # Publish specific flags
    dotnet_publish_properties: dict[str, str] = {}

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    @pydantic.field_validator("dotnet_version")
    @classmethod
    def validate_dotnet_version(cls, value: str | None) -> str | None:
        """Validate the dotnet-version property.

        :param value: The value to validate.

        :return: The validated value.
        """
        if value is None or value == "none":
            return value

        # Match either single digit (e.g. "8") or major.minor format (e.g. "8.0")
        pattern = r"^(\d+)(?:\.(\d+))?$"
        match = re.match(pattern, value)

        oldest_supported_dotnet_version = 6
        if match:
            major = int(match.group(1))
            if major >= oldest_supported_dotnet_version:
                return value

        raise ValueError(f"Invalid dotnet-version {value!r}")


class DotnetV2PluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the .NET plugin.

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
        # Validating only if .NET SDK is being provided by user. Otherwise, the plugin
        # will make sure there is an SDK available according to `dotnet-version`.
        options = cast(DotnetV2PluginProperties, self._options)
        if options.dotnet_version is None:
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
      The .NET proj or solution file to build. (Default: omitted).

    - ``dotnet-properties``
      (dictionary of strings to strings)
      The list of MSBuild properties to be used by the restore, build, and publish commands.
      (Default: empty).

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
      (Default: omitted).

    - ``dotnet-restore-properties``
      (dictionary of strings to strings)
      The list of MSBuild properties to be used by the restore command. (Default: empty).

    - ``dotnet-restore-configfile``
      (string)
      The NuGet configuration file (nuget.config) to use. (Default: omitted).

    Build-specific Flags:

    - ``dotnet-build-framework``
      (string)
      The target framework to build for. (Default: omitted).

    - ``dotnet-build-properties``
      (dictionary of strings to strings)
      The list of MSBuild properties to be used by the build command. (Default: empty).

    Publish-specific Flags:

    - ``dotnet-publish-properties``
      (dictionary of strings to strings)
      The list of MSBuild properties to be used by the publish command. (Default: empty).
    """

    properties_class = DotnetV2PluginProperties
    validator_class = DotnetV2PluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        options = cast(DotnetV2PluginProperties, self._options)

        # .NET binary provided by the user
        if (
            "dotnet-deps" in self._part_info.part_dependencies
            or options.dotnet_version is None
        ):
            return set()

        snap_name = self._generate_snap_name(options)

        if not snap_name:
            return set()

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
        if (
            "dotnet-deps" in self._part_info.part_dependencies
            or options.dotnet_version is None
        ):
            return environment

        build_on = self._part_info.project_info.arch_build_on
        snap_name = self._generate_snap_name(options)

        _, lib_path = self._get_dotnet_platform_info(build_on, snap_name)
        if lib_path:
            environment["LD_LIBRARY_PATH"] = lib_path

        snap_location = f"/snap/{snap_name}/current"
        dotnet_path = f"{snap_location}/usr/lib/dotnet"
        environment["PATH"] = f"{dotnet_path}:${{PATH}}"

        logger.info("Using environment:")
        for key, value in environment.items():
            logger.info(f"  {key}={value}")

        return environment

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(DotnetV2PluginProperties, self._options)

        build_for = self._part_info.project_info.arch_build_for
        dotnet_rid, _ = self._get_dotnet_platform_info(build_for)

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

        version_split = version.split(".")

        if len(version_split) == 1:
            snap_version = f"{version}0"
        else:
            major, minor = version.split(".")
            snap_version = major + minor

        return f"dotnet-sdk-{snap_version}"

    def _get_restore_command(
        self, dotnet_rid: str, options: DotnetV2PluginProperties
    ) -> str:
        restore_cmd = ["dotnet", "restore"]

        if options.dotnet_restore_sources:
            logger.info(f"Using restore sources: {options.dotnet_restore_sources}")
            restore_cmd.extend(
                [f"--source {source}" for source in options.dotnet_restore_sources]
            )
        if options.dotnet_restore_configfile:
            restore_cmd.append(f"--configfile {options.dotnet_restore_configfile}")

        restore_cmd.append(f"--verbosity {options.dotnet_verbosity.value}")
        restore_cmd.append(f"--runtime {dotnet_rid}")

        for prop_name, prop_value in options.dotnet_properties.items():
            restore_cmd.append(f"-p:{prop_name}={prop_value}")
        for prop_name, prop_value in options.dotnet_restore_properties.items():
            restore_cmd.append(f"-p:{prop_name}={prop_value}")

        if options.dotnet_project:
            restore_cmd.append(f"{options.dotnet_project}")

        return " ".join(restore_cmd)

    def _get_build_command(
        self, dotnet_rid: str, options: DotnetV2PluginProperties
    ) -> str:
        build_cmd = [
            "dotnet",
            "build",
            f"--configuration {options.dotnet_configuration.value}",
            "--no-restore",
        ]

        if options.dotnet_build_framework:
            build_cmd.append(f"--framework {options.dotnet_build_framework}")

        build_cmd.append(f"--verbosity {options.dotnet_verbosity.value}")

        # Self contained build
        build_cmd.append(f"--runtime {dotnet_rid}")
        build_cmd.append(f"--self-contained {options.dotnet_self_contained}")

        for prop_name, prop_value in options.dotnet_properties.items():
            build_cmd.append(f"-p:{prop_name}={prop_value}")
        for prop_name, prop_value in options.dotnet_build_properties.items():
            build_cmd.append(f"-p:{prop_name}={prop_value}")

        if options.dotnet_project:
            build_cmd.append(f"{options.dotnet_project}")

        return " ".join(build_cmd)

    def _get_publish_command(
        self, dotnet_rid: str, options: DotnetV2PluginProperties
    ) -> str:
        publish_cmd = [
            "dotnet",
            "publish",
            f"--configuration {options.dotnet_configuration.value}",
            f"--output {self._part_info.part_install_dir}",
            f"--verbosity {options.dotnet_verbosity.value}",
            "--no-restore",
            "--no-build",
        ]

        # Self contained build
        publish_cmd.append(f" --runtime {dotnet_rid}")
        publish_cmd.append(f" --self-contained {options.dotnet_self_contained}")

        for prop_name, prop_value in options.dotnet_properties.items():
            publish_cmd.append(f" -p:{prop_name}={prop_value}")
        for prop_name, prop_value in options.dotnet_publish_properties.items():
            publish_cmd.append(f" -p:{prop_name}={prop_value}")

        if options.dotnet_project:
            publish_cmd.append(f" {options.dotnet_project}")

        return " ".join(publish_cmd)

    def _get_dotnet_platform_info(
        self, arch: str, snap_name: str | None = None
    ) -> tuple[str, str | None]:
        """Get the .NET RID and library path for the given architecture.

        :param arch: The architecture to get the info for.
        :param snap_name: The name of the snap containing the .NET SDK.

        :return: A tuple containing the .NET RID and the LD_LIBRARY_PATH value.

        :raises ValueError: If the architecture is not supported.
        """
        if arch in _DEBIAN_ARCH_TO_DOTNET_RID:
            rid = _DEBIAN_ARCH_TO_DOTNET_RID[arch]
            lib_path = None
            if snap_name:
                lib_path = (
                    f"/snap/{snap_name}/current/lib/{self._part_info.project_info.arch_triplet_build_on}:"
                    f"/snap/{snap_name}/current/usr/lib/{self._part_info.project_info.arch_triplet_build_on}"
                )
            return rid, lib_path

        raise ValueError(
            f"Unsupported architecture {arch!r}. Supported architectures are {humanize_list(_DEBIAN_ARCH_TO_DOTNET_RID.keys(), 'and')}."
        )
