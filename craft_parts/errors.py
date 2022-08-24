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

"""Craft parts errors."""

import dataclasses
from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from pydantic.error_wrappers import ErrorDict


@dataclasses.dataclass(repr=True)
class PartsError(Exception):
    """Unexpected error.

    :param brief: Brief description of error.
    :param details: Detailed information.
    :param resolution: Recommendation, if any.
    """

    brief: str
    details: Optional[str] = None
    resolution: Optional[str] = None

    def __str__(self) -> str:
        components = [self.brief]

        if self.details:
            components.append(self.details)

        if self.resolution:
            components.append(self.resolution)

        return "\n".join(components)


class PartDependencyCycle(PartsError):
    """A dependency cycle has been detected in the parts definition."""

    def __init__(self) -> None:
        brief = "A circular dependency chain was detected."
        resolution = "Review the parts definition to remove dependency cycles."

        super().__init__(brief=brief, resolution=resolution)


class InvalidApplicationName(PartsError):
    """The application name contains invalid characters.

    :param name: The invalid application name.
    """

    def __init__(self, name: str):
        self.name = name
        brief = f"Application name {name!r} is invalid."
        resolution = (
            "Valid application names contain letters, underscores or numbers, "
            "and must start with a letter."
        )

        super().__init__(brief=brief, resolution=resolution)


class InvalidPartName(PartsError):
    """An operation was requested on a part that's in the parts specification.

    :param part_name: The invalid part name.
    """

    def __init__(self, part_name: str):
        self.part_name = part_name
        brief = f"A part named {part_name!r} is not defined in the parts list."
        resolution = "Review the parts definition and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class InvalidArchitecture(PartsError):
    """The machine architecture is not supported.

    :param arch_name: The unsupported architecture name.
    """

    def __init__(self, arch_name: str):
        self.arch_name = arch_name
        brief = f"Architecture {arch_name!r} is not supported."
        resolution = "Make sure the architecture name is correct."

        super().__init__(brief=brief, resolution=resolution)


class PartSpecificationError(PartsError):
    """A part was not correctly specified.

    :param part_name: The name of the part being processed.
    :param message: The error message.
    """

    def __init__(self, *, part_name: str, message: str):
        self.part_name = part_name
        self.message = message
        brief = f"Part {part_name!r} validation failed."
        details = message
        resolution = f"Review part {part_name!r} and make sure it's correct."

        super().__init__(brief=brief, details=details, resolution=resolution)

    @classmethod
    def from_validation_error(cls, *, part_name: str, error_list: List["ErrorDict"]):
        """Create a PartSpecificationError from a pydantic error list.

        :param part_name: The name of the part being processed.
        :param error_list: A list of dictionaries containing pydantic error definitions.
        """
        formatted_errors: List[str] = []

        for error in error_list:
            loc = error.get("loc")
            msg = error.get("msg")

            if not (loc and msg) or not isinstance(loc, tuple):
                continue

            field = cls._format_loc(loc)
            if msg == "field required":
                formatted_errors.append(f"- field {field!r} is required")
            elif msg == "extra fields not permitted":
                formatted_errors.append(f"- extra field {field!r} not permitted")
            else:
                formatted_errors.append(f"- {msg} in field {field!r}")

        return cls(part_name=part_name, message="\n".join(formatted_errors))

    @classmethod
    def _format_loc(cls, loc):
        """Format location."""
        loc_parts = []
        for loc_part in loc:
            if isinstance(loc_part, str):
                loc_parts.append(loc_part)
            elif isinstance(loc_part, int):
                # Integer indicates an index. Go back and fix up previous part.
                previous_part = loc_parts.pop()
                previous_part += f"[{loc_part}]"
                loc_parts.append(previous_part)
            else:
                raise RuntimeError(f"unhandled loc: {loc_part}")

        loc = ".".join(loc_parts)

        # Filter out internal __root__ detail.
        loc = loc.replace(".__root__", "")
        return loc


class CopyTreeError(PartsError):
    """Failed to copy or link a file tree.

    :param message: The error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Failed to copy or link file tree: {message}."
        resolution = "Make sure paths and permissions are correct."

        super().__init__(brief=brief, resolution=resolution)


class CopyFileNotFound(PartsError):
    """An attempt was made to copy a file that doesn't exist.

    :param name: The file name.
    """

    def __init__(self, name: str):
        self.name = name
        brief = f"Failed to copy {name!r}: no such file or directory."

        super().__init__(brief=brief)


class XAttributeError(PartsError):
    """Failed to read or write an extended attribute.

    :param action: The action being performed.
    :param key: The extended attribute key.
    :param path: The file path.
    :param is_write: Whether this is an attribute write operation.
    """

    def __init__(self, key: str, path: str, is_write: bool = False):
        self.key = key
        self.path = path
        self.is_write = is_write
        action = "write" if is_write else "read"
        brief = f"Unable to {action} extended attribute."
        details = f"Failed to {action} attribute {key!r} on {path!r}."
        resolution = "Make sure your filesystem supports extended attributes."

        super().__init__(brief=brief, details=details, resolution=resolution)


class XAttributeTooLong(PartsError):
    """Failed to write an extended attribute because key and/or value is too long.

    :param key: The extended attribute key.
    :param value: The extended attribute value.
    :param path: The file path.
    """

    def __init__(self, key: str, value: str, path: str):
        self.key = key
        self.value = value
        self.path = path
        brief = "Failed to write attribute: key and/or value is too long."
        details = f"key={key!r}, value={value!r}"

        super().__init__(brief=brief, details=details)


class UndefinedPlugin(PartsError):
    """The part didn't define a plugin and the part name is not a valid plugin name.

    :param part_name: The name of the part with no plugin definition.
    """

    def __init__(self, *, part_name: str):
        self.part_name = part_name
        brief = f"Plugin not defined for part {part_name!r}."
        resolution = f"Review part {part_name!r} and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class InvalidPlugin(PartsError):
    """A request was made to use a plugin that's not registered.

    :param plugin_name: The invalid plugin name."
    :param part_name: The name of the part defining the invalid plugin.
    """

    def __init__(self, plugin_name: str, *, part_name: str):
        self.plugin_name = plugin_name
        self.part_name = part_name
        brief = f"Plugin {plugin_name!r} in part {part_name!r} is not registered."
        resolution = f"Review part {part_name!r} and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class OsReleaseIdError(PartsError):
    """Failed to determine the host operating system identification string."""

    def __init__(self):
        brief = "Unable to determine the host operating system ID."

        super().__init__(brief=brief)


class OsReleaseNameError(PartsError):
    """Failed to determine the host operating system name."""

    def __init__(self):
        brief = "Unable to determine the host operating system name."

        super().__init__(brief=brief)


class OsReleaseVersionIdError(PartsError):
    """Failed to determine the host operating system version."""

    def __init__(self):
        brief = "Unable to determine the host operating system version ID."

        super().__init__(brief=brief)


class OsReleaseCodenameError(PartsError):
    """Failed to determine the host operating system version codename."""

    def __init__(self):
        brief = "Unable to determine the host operating system codename."

        super().__init__(brief=brief)


class FilesetError(PartsError):
    """An invalid fileset operation was performed.

    :param name: The name of the fileset.
    :param message: The error message.
    """

    def __init__(self, *, name: str, message: str):
        self.name = name
        self.message = message
        brief = f"{name!r} fileset error: {message}."
        resolution = "Review the parts definition and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class FilesetConflict(PartsError):
    """Inconsistent stage to prime filtering.

    :param conflicting_files: A set containing the conflicting file names.
    """

    def __init__(self, conflicting_files: Set[str]):
        self.conflicting_files = conflicting_files
        brief = "Failed to filter files: inconsistent 'stage' and 'prime' filesets."
        details = (
            f"The following files have been excluded in the 'stage' fileset, "
            f"but included by the 'prime' fileset: {conflicting_files!r}."
        )
        resolution = (
            "Make sure that the files included in 'prime' are also included in 'stage'."
        )

        super().__init__(brief=brief, details=details, resolution=resolution)


class FileOrganizeError(PartsError):
    """Failed to organize a file layout.

    :param part_name: The name of the part being processed.
    :param message: The error message.
    """

    def __init__(self, *, part_name, message):
        self.part_name = part_name
        self.message = message
        brief = f"Failed to organize part {part_name!r}: {message}."

        super().__init__(brief=brief)


class PartFilesConflict(PartsError):
    """Different parts list the same files with different contents.

    :param part_name: The name of the part being processed.
    :param other_part_name: The name of the conflicting part.
    :param conflicting_files: The list of conflicting files.
    """

    def __init__(
        self, *, part_name: str, other_part_name: str, conflicting_files: List[str]
    ):
        self.part_name = part_name
        self.other_part_name = other_part_name
        self.conflicting_files = conflicting_files
        indented_conflicting_files = (f"    {i}" for i in conflicting_files)
        file_paths = "\n".join(sorted(indented_conflicting_files))
        brief = "Failed to stage: parts list the same file with different contents."
        details = (
            f"Parts {part_name!r} and {other_part_name!r} list the following "
            f"files, but with different contents:\n"
            f"{file_paths}"
        )

        super().__init__(brief=brief, details=details)


class StageFilesConflict(PartsError):
    """Files from a part conflict with files already being staged.

    :param part_name: The name of the part being processed.
    :param conflicting_files: The list of confictling files.
    """

    def __init__(self, *, part_name: str, conflicting_files: List[str]):
        self.part_name = part_name
        self.conflicting_files = conflicting_files
        indented_conflicting_files = (f"    {i}" for i in conflicting_files)
        file_paths = "\n".join(sorted(indented_conflicting_files))
        brief = "Failed to stage: part files conflict with files already being staged."
        details = (
            f"The following files in part {part_name!r} are already being staged "
            f"with different content:\n"
            f"{file_paths}"
        )

        super().__init__(brief=brief, details=details)


class PluginEnvironmentValidationError(PartsError):
    """Plugin environment validation failed at runtime.

    :param part_name: The name of the part being processed.
    """

    def __init__(self, *, part_name: str, reason: str):
        self.part_name = part_name
        self.reason = reason
        brief = f"Environment validation failed for part {part_name!r}: {reason}."

        super().__init__(brief=brief)


class PluginBuildError(PartsError):
    """Plugin build script failed at runtime.

    :param part_name: The name of the part being processed.
    """

    def __init__(self, *, part_name: str):
        self.part_name = part_name
        brief = f"Failed to run the build script for part {part_name!r}."

        super().__init__(brief=brief)


class InvalidControlAPICall(PartsError):
    """A control API call was made with invalid parameters.

    :param part_name: The name of the part being processed.
    :param scriptlet_name: The name of the scriptlet that originated the call.
    :param message: The error message.
    """

    def __init__(self, *, part_name: str, scriptlet_name: str, message: str):
        self.part_name = part_name
        self.scriptlet_name = scriptlet_name
        self.message = message
        brief = (
            f"{scriptlet_name!r} in part {part_name!r} executed an invalid control "
            f"API call: {message}."
        )
        resolution = "Review the scriptlet and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class ScriptletRunError(PartsError):
    """A scriptlet execution failed.

    :param part_name: The name of the part being processed.
    :param scriptlet_name: The name of the scriptlet that failed to execute.
    :param exit_code: The execution error code.
    """

    def __init__(self, *, part_name: str, scriptlet_name: str, exit_code: int):
        self.part_name = part_name
        self.scriptlet_name = scriptlet_name
        self.exit_code = exit_code
        brief = (
            f"{scriptlet_name!r} in part {part_name!r} failed with code {exit_code}."
        )
        resolution = "Review the scriptlet and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class CallbackRegistrationError(PartsError):
    """Error in callback function registration.

    :param message: the error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Callback registration error: {message}."

        super().__init__(brief=brief)


class StagePackageNotFound(PartsError):
    """Failed to install a stage package.

    :param part_name: The name of the part being processed.
    :param package_name: The name of the package.
    """

    def __init__(self, *, part_name: str, package_name: str):
        self.part_name = part_name
        self.package_name = package_name
        brief = f"Stage package not found in part {part_name!r}: {package_name}."

        super().__init__(brief=brief)


class OverlayPackageNotFound(PartsError):
    """Failed to install an overlay package.

    :param part_name: The name of the part being processed.
    :param message: the error message.
    """

    def __init__(self, *, part_name: str, package_name: str):
        self.part_name = part_name
        self.package_name = package_name
        brief = f"Overlay package not found in part {part_name!r}: {package_name}."

        super().__init__(brief=brief)


class InvalidAction(PartsError):
    """An attempt was made to execute an action with invalid parameters.

    :param message: The error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Action is invalid: {message}."

        super().__init__(brief=brief)


class OverlayPlatformError(PartsError):
    """A project using overlays was processed on a non-Linux platform."""

    def __init__(self) -> None:
        brief = "The overlay step is only supported on Linux."

        super().__init__(brief=brief)


class OverlayPermissionError(PartsError):
    """A project using overlays was processed by a non-privileged user."""

    def __init__(self) -> None:
        brief = "Using the overlay step requires superuser privileges."

        super().__init__(brief=brief)


class DebError(PartsError):
    """A "deb"-related command failed."""

    def __init__(self, deb_path, command, exit_code):
        brief = (
            f"Failed when handling {deb_path}: "
            f"command {command!r} exited with code {exit_code}."
        )
        resolution = "Make sure the deb file is correctly specified."

        super().__init__(brief=brief, resolution=resolution)
