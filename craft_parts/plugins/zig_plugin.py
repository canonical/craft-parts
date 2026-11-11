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
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Build and install projects using the Zig build system."""

import re
import shlex
from pathlib import Path, PurePosixPath
from typing import Literal, cast

import pydantic
from typing_extensions import override

from craft_parts import errors
from craft_parts.constraints import UniqueList

from . import validator
from .base import Plugin
from .properties import PluginProperties

# The plugin always passes -j, which zig build accepts from 0.11.0.
_MINIMUM_RELEASE = (0, 11, 0)
# ASCII digits only: \d would also accept other Unicode decimal digits.
_VERSION = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.+-]+)?"
)
_SNAP = "zig/latest/beta"


class ZigPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Zig plugin."""

    plugin: Literal["zig"] = "zig"

    zig_build_parameters: list[str] = pydantic.Field(
        default=[],
        description="Additional arguments to pass to ``zig build install``.",
    )
    """Additional arguments to pass to ``zig build install``, such as the ``-D``
    options defined by the project.
    """

    zig_install_prefix: str = pydantic.Field(
        default="/",
        description="The installation prefix inside the part's install directory.",
    )
    """The absolute installation prefix inside ``$CRAFT_PART_INSTALL``. For example,
    ``/usr`` installs executables in ``$CRAFT_PART_INSTALL/usr/bin``.
    """

    source: str
    after: UniqueList[str] | None = None

    @pydantic.field_validator("zig_install_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        """Keep the installation prefix inside DESTDIR."""
        prefix = PurePosixPath(value)
        if not prefix.is_absolute() or ".." in prefix.parts or "\0" in value:
            raise ValueError(
                "zig-install-prefix must be an absolute path without '..' or NUL"
            )
        return value


class ZigPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Validate the selected compiler after its provider is available."""

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Check that Zig is available and supports the plugin's build options."""
        version = self.validate_dependency(
            dependency="zig",
            plugin_name="zig",
            argument="version",
            part_dependencies=part_dependencies,
        )
        if part_dependencies and "zig-deps" in part_dependencies:
            return
        match = _VERSION.fullmatch(version)
        if match is None:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid Zig compiler version {version!r}",
            )
        if tuple(int(part) for part in match.groups()) < _MINIMUM_RELEASE:
            minimum = ".".join(str(part) for part in _MINIMUM_RELEASE)
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"Zig {version!r} is older than {minimum}",
                resolution=f"Provide Zig {minimum} or later.",
            )


def _environment_path(path: Path) -> str:
    """Escape a literal path for the executor's double-quoted exports."""
    return (
        str(path)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
    )


class ZigPlugin(Plugin):
    """Build a project's install graph with the Zig build system."""

    properties_class = ZigPluginProperties
    validator_class = ZigPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return the Zig snap, unless a zig-deps part provides the compiler."""
        options = cast(ZigPluginProperties, self._options)
        if "zig-deps" in (options.after or []):
            return set()
        return {_SNAP}

    @override
    def get_build_packages(self) -> set[str]:
        """Zig distributions are self-contained; project libraries are explicit."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Keep the Zig caches outside the installed payload."""
        cache_dir = self._part_info.part_cache_dir / "zig"
        return {
            "ZIG_GLOBAL_CACHE_DIR": _environment_path(cache_dir / "global"),
            "ZIG_LOCAL_CACHE_DIR": _environment_path(
                self._part_info.part_build_dir / ".zig-cache"
            ),
        }

    @override
    def get_build_commands(self) -> list[str]:
        """Build and install all artifacts attached to the project's install step."""
        options = cast(ZigPluginProperties, self._options)
        search_prefixes = [
            argument
            for prefix in (self._part_info.stage_dir, self._part_info.stage_dir / "usr")
            if prefix.is_dir()
            for argument in ("--search-prefix", str(prefix))
        ]
        command = shlex.join(
            [
                "zig",
                "build",
                "install",
                "--prefix",
                options.zig_install_prefix,
                f"-j{self._part_info.parallel_build_count}",
                *search_prefixes,
                *options.zig_build_parameters,
            ]
        )
        return [
            f"DESTDIR={shlex.quote(str(self._part_info.part_install_dir))} {command}"
        ]
