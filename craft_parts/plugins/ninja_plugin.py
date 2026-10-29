# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
"""The ninja plugin."""

import shlex
from typing import Literal, cast

import pydantic
from typing_extensions import override

from . import validator
from .base import Plugin
from .properties import PluginProperties


class NinjaPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the ninja plugin."""

    plugin: Literal["ninja"] = "ninja"

    ninja_configure_command: str = ""
    ninja_build_directory: str = "."
    ninja_target: str = ""
    ninja_parameters: list[str] = []
    ninja_install: bool = False

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    @pydantic.field_validator("ninja_build_directory")
    @classmethod
    def validate_ninja_build_directory(cls, value: str) -> str:
        """Validate ninja-build-directory values."""
        if value.strip() == "":
            raise ValueError("ninja-build-directory must not be empty")
        return value


class NinjaPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the ninja plugin."""

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin."""
        self.validate_dependency(
            dependency="ninja",
            plugin_name="ninja",
            part_dependencies=part_dependencies,
        )


class NinjaPlugin(Plugin):
    """A plugin to build parts that use Ninja."""

    properties_class = NinjaPluginProperties
    validator_class = NinjaPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"ninja-build"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        return []

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(NinjaPluginProperties, self._options)

        commands: list[str] = []
        if options.ninja_configure_command:
            commands.append(options.ninja_configure_command)

        ninja_cmd = ["ninja"]
        if options.ninja_build_directory != ".":
            ninja_cmd.extend(["-C", options.ninja_build_directory])
        if options.ninja_target:
            ninja_cmd.append(options.ninja_target)
        ninja_cmd.extend(options.ninja_parameters)
        commands.append(shlex.join(ninja_cmd))

        if options.ninja_install:
            install_cmd = ["ninja"]
            if options.ninja_build_directory != ".":
                install_cmd.extend(["-C", options.ninja_build_directory])
            install_cmd.append("install")
            commands.append(
                f"DESTDIR={self._part_info.part_install_dir} {shlex.join(install_cmd)}"
            )

        return commands

    @override
    def get_out_of_source_build(self) -> bool:
        return False
