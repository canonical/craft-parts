# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
"""The sbt plugin."""

from typing import Literal, cast

from typing_extensions import override

from . import validator
from .java_plugin import JavaPlugin
from .properties import PluginProperties


class SbtPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the sbt plugin."""

    plugin: Literal["sbt"] = "sbt"

    sbt_task: str = "package"
    sbt_parameters: list[str] = []
    sbt_use_wrapper: bool = True
    sbt_version: str = "1.12.11"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class SbtPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the sbt plugin."""

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin."""
        del part_dependencies


class SbtPlugin(JavaPlugin):
    """A plugin to build parts that use sbt."""

    properties_class = SbtPluginProperties
    validator_class = SbtPluginEnvironmentValidator

    @property
    def _sbt_executable(self) -> str:
        options = cast(SbtPluginProperties, self._options)
        return (
            "${CRAFT_PART_BUILD_WORK}/sbt"
            if options.sbt_use_wrapper
            else "${CRAFT_PART_BUILD}/.parts/sbt/bin/sbt"
        )

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        options = cast(SbtPluginProperties, self._options)
        if options.sbt_use_wrapper:
            return set()
        return {"ca-certificates", "curl", "tar"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        env = super().get_build_environment()

        options = cast(SbtPluginProperties, self._options)
        if not options.sbt_use_wrapper:
            env["PATH"] = "${CRAFT_PART_BUILD}/.parts/sbt/bin:${PATH}"

        return env

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        return []

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(SbtPluginProperties, self._options)

        return [
            *self._get_sbt_bootstrap_commands(options=options),
            *self._get_wrapper_validation_commands(options=options),
            f"{self._sbt_executable} {options.sbt_task} {' '.join(options.sbt_parameters)}".strip(),
            *self._get_java_post_build_commands(),
        ]

    def _get_sbt_bootstrap_commands(self, options: SbtPluginProperties) -> list[str]:
        if options.sbt_use_wrapper:
            return []

        sbt_url = (
            "https://github.com/sbt/sbt/releases/download/"
            f"v{options.sbt_version}/sbt-{options.sbt_version}.tgz"
        )
        return [
            "mkdir -p ${CRAFT_PART_BUILD}/.parts",
            f'curl -fsSL "{sbt_url}" -o "${{CRAFT_PART_BUILD}}/.parts/sbt-{options.sbt_version}.tgz"',
            f'tar -xzf "${{CRAFT_PART_BUILD}}/.parts/sbt-{options.sbt_version}.tgz" -C "${{CRAFT_PART_BUILD}}/.parts"',
            f'rm -f "${{CRAFT_PART_BUILD}}/.parts/sbt-{options.sbt_version}.tgz"',
        ]

    def _get_wrapper_validation_commands(
        self, options: SbtPluginProperties
    ) -> list[str]:
        if not options.sbt_use_wrapper:
            return []

        return [
            """[ -e ${CRAFT_PART_BUILD_WORK}/sbt ] || {
>&2 echo 'sbt wrapper file not found, set sbt-use-wrapper to false to bootstrap sbt from official releases.'; exit 1;
}""",
            "chmod +x ${CRAFT_PART_BUILD_WORK}/sbt",
        ]

    @override
    def get_out_of_source_build(self) -> bool:
        return False
