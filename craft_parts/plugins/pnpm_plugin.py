# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
"""The pnpm plugin."""

from typing import Literal, cast

from typing_extensions import override

from . import validator
from .base import Plugin
from .properties import PluginProperties


class PnpmPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the pnpm plugin."""

    plugin: Literal["pnpm"] = "pnpm"

    pnpm_task: str = "run build"
    pnpm_parameters: list[str] = []
    pnpm_use_wrapper: bool = True
    pnpm_version: str = "10.12.1"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class PnpmPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the pnpm plugin."""

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin."""
        del part_dependencies


class PnpmPlugin(Plugin):
    """A plugin to build parts that use pnpm."""

    properties_class = PnpmPluginProperties
    validator_class = PnpmPluginEnvironmentValidator

    @property
    def _pnpm_executable(self) -> str:
        options = cast(PnpmPluginProperties, self._options)
        return (
            "${CRAFT_PART_BUILD_WORK}/pnpm"
            if options.pnpm_use_wrapper
            else "${CRAFT_PART_BUILD}/.parts/bin/pnpm"
        )

    @property
    def _pnpm_local_path(self) -> str:
        return "${CRAFT_PART_BUILD}/.parts/bin/pnpm"

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        options = cast(PnpmPluginProperties, self._options)
        if options.pnpm_use_wrapper:
            return set()
        return {"ca-certificates", "curl"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        options = cast(PnpmPluginProperties, self._options)
        if options.pnpm_use_wrapper:
            return {}

        return {"PATH": "${CRAFT_PART_BUILD}/.parts/bin:${PATH}"}

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        return []

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(PnpmPluginProperties, self._options)

        return [
            *self._get_pnpm_bootstrap_commands(options=options),
            *self._get_wrapper_validation_commands(options=options),
            f"if [ -f pnpm-lock.yaml ]; then {self._pnpm_executable} install --frozen-lockfile; else {self._pnpm_executable} install --no-frozen-lockfile; fi",
            f"{self._pnpm_executable} {options.pnpm_task} {' '.join(options.pnpm_parameters)}".strip(),
        ]

    def _get_pnpm_bootstrap_commands(self, options: PnpmPluginProperties) -> list[str]:
        if options.pnpm_use_wrapper:
            return []

        pnpm_url = (
            "https://github.com/pnpm/pnpm/releases/download/"
            f"v{options.pnpm_version}/pnpm-linux-x64"
        )
        return [
            'mkdir -p "${CRAFT_PART_BUILD}/.parts/bin"',
            f'curl -fsSL "{pnpm_url}" -o "{self._pnpm_local_path}"',
            f'chmod +x "{self._pnpm_local_path}"',
        ]

    def _get_wrapper_validation_commands(
        self, options: PnpmPluginProperties
    ) -> list[str]:
        if not options.pnpm_use_wrapper:
            return []

        return [
            """[ -e ${CRAFT_PART_BUILD_WORK}/pnpm ] || {
>&2 echo 'pnpm wrapper file not found, set pnpm-use-wrapper to false to bootstrap pnpm from official releases.'; exit 1;
}""",
            "chmod +x ${CRAFT_PART_BUILD_WORK}/pnpm",
        ]

    @override
    def get_out_of_source_build(self) -> bool:
        return False
