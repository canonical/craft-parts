# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Source handler error definitions."""

from typing import List, Sequence

from craft_parts import errors
from craft_parts.utils import formatting_utils


class SourceError(errors.PartsError):
    """Base class for source handler errors."""


class InvalidSourceType(SourceError):
    """Failed to determine a source type.

    :param source: The source defined for the part.
    """

    def __init__(self, source: str):
        self.source = source
        brief = f"Failed to pull source: unable to determine source type of {source!r}."

        super().__init__(brief=brief)


class InvalidSourceOption(SourceError):
    """A source option is not allowed for the given source type.

    :param source_type: The part's source type.
    :param option: The invalid source option.
    """

    def __init__(self, *, source_type: str, option: str):
        self.source_type = source_type
        self.option = option
        brief = (
            f"Failed to pull source: {option!r} cannot be used "
            f"with a {source_type} source."
        )
        resolution = "Make sure sources are correctly specified."

        super().__init__(brief=brief, resolution=resolution)


class IncompatibleSourceOptions(SourceError):
    """Source specified options that cannot be used at the same time.

    :param source_type: The part's source type.
    :param options: The list of incompatible source options.
    """

    def __init__(self, source_type: str, options: List[str]):
        self.source_type = source_type
        self.options = options
        humanized_options = formatting_utils.humanize_list(options, "and")
        brief = (
            f"Failed to pull source: cannot specify both {humanized_options} "
            f"for a {source_type} source."
        )
        resolution = "Make sure sources are correctly specified."

        super().__init__(brief=brief, resolution=resolution)


class ChecksumMismatch(SourceError):
    """A checksum doesn't match the expected value.

    :param expected: The expected checksum.
    :param obtained: The actual checksum.
    """

    def __init__(self, *, expected: str, obtained: str):
        self.expected = expected
        self.obtained = obtained
        brief = f"Expected digest {expected}, obtained {obtained}."

        super().__init__(brief=brief)


class SourceUpdateUnsupported(SourceError):
    """The source handler doesn't support updating.

    :param name: The source type.
    """

    def __init__(self, name: str):
        self.name = name
        brief = f"Failed to update source: {name!r} sources don't support updating."

        super().__init__(brief=brief)


class NetworkRequestError(SourceError):
    """A network request operation failed.

    :param message: The error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Network request error: {message}."
        resolution = "Check the network and try again."

        super().__init__(brief=brief, resolution=resolution)


class SourceNotFound(SourceError):
    """Failed to retrieve a source.

    :param source: The source defined for the part.
    """

    def __init__(self, source: str):
        self.source = source
        brief = f"Failed to pull source: {source!r} not found."
        resolution = "Make sure the source path is correct and accessible."

        super().__init__(brief=brief, resolution=resolution)


class InvalidSnapPackage(SourceError):
    """A snap package is invalid.

    :param snap_file: The snap file name.
    """

    def __init__(self, snap_file: str):
        self.snap_file = snap_file
        brief = f"Snap {snap_file!r} does not contain valid data."
        resolution = "Ensure the source lists a proper snap file."

        super().__init__(brief=brief, resolution=resolution)


class PullError(SourceError):
    """Failed pulling source.

    :param command: The command used to pull the source.
    :param exit_code: The command exit code.
    """

    def __init__(self, *, command: Sequence, exit_code: int):
        self.command = command
        self.exit_code = exit_code
        brief = (
            f"Failed to pull source: command {command!r} exited with code {exit_code}."
        )
        resolution = "Make sure sources are correctly specified."

        super().__init__(brief=brief, resolution=resolution)


class VCSError(SourceError):
    """A version control system command failed."""

    def __init__(self, message: str):
        self.message = message
        brief = message

        super().__init__(brief=brief)
