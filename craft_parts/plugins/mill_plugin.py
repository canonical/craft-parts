# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
"""The mill plugin."""

from typing import Literal, cast

from typing_extensions import override

from . import validator
from .java_plugin import JavaPlugin
from .properties import PluginProperties


class MillPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the mill plugin."""

    plugin: Literal["mill"] = "mill"

    mill_task: str = "__.assembly"
    mill_parameters: list[str] = []
    mill_use_wrapper: bool = True
    mill_version: str = "0.12.8"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class MillPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the mill plugin."""

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin."""
        del part_dependencies


class MillPlugin(JavaPlugin):
    """A plugin to build parts that use Mill."""

    properties_class = MillPluginProperties
    validator_class = MillPluginEnvironmentValidator

    @property
    def _mill_executable(self) -> str:
        options = cast(MillPluginProperties, self._options)
        return (
            "${CRAFT_PART_BUILD_WORK}/mill"
            if options.mill_use_wrapper
            else "${CRAFT_PART_BUILD}/.parts/bin/mill"
        )

    @property
    def _mill_local_path(self) -> str:
        return f"{self._part_info.part_build_subdir}/.parts/bin/mill"

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        options = cast(MillPluginProperties, self._options)
        if options.mill_use_wrapper:
            return set()
        return {"ca-certificates", "curl"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        env = super().get_build_environment()

        options = cast(MillPluginProperties, self._options)
        if not options.mill_use_wrapper:
            env["PATH"] = "${CRAFT_PART_BUILD}/.parts/bin:${PATH}"

        return env

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        options = cast(MillPluginProperties, self._options)
        if options.mill_use_wrapper:
            return []

        mill_url = (
            "https://github.com/com-lihaoyi/mill/releases/download/"
            f"{options.mill_version}/{options.mill_version}"
        )
        return [
            f'mkdir -p "{self._part_info.part_build_subdir}/.parts/bin"',
            f'curl -fsSL "{mill_url}" -o "{self._mill_local_path}"',
            f'chmod +x "{self._mill_local_path}"',
        ]

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(MillPluginProperties, self._options)

        return [
            *self._get_wrapper_validation_commands(options=options),
            f"{self._mill_executable} {options.mill_task} {' '.join(options.mill_parameters)}".strip(),
            *self._get_java_post_build_commands(),
        ]

    def _get_wrapper_validation_commands(
        self, options: MillPluginProperties
    ) -> list[str]:
        if not options.mill_use_wrapper:
            return []

        return [
            """[ -e ${CRAFT_PART_BUILD_WORK}/mill ] || {
>&2 echo 'mill wrapper file not found, set mill-use-wrapper to false to use a system-installed mill binary.'; exit 1;
}""",
            "chmod +x ${CRAFT_PART_BUILD_WORK}/mill",
        ]
