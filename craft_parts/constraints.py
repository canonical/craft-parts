# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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
"""Pydantic constraints for various items."""

import collections
import re
from collections.abc import Callable
from typing import Annotated, TypeVar

from pydantic import AfterValidator, BeforeValidator, Field

T = TypeVar("T")
Tv = TypeVar("Tv")


def get_validator_by_regex(
    regex: re.Pattern[str], error_msg: str
) -> Callable[[str], str]:
    """Get a string validator by regular expression with a known error message.

    This allows providing better error messages for regex-based validation than the
    standard message provided by pydantic. Simply place the result of this function in
    a BeforeValidator attached to your annotated type.

    :param regex: a compiled regular expression on a string.
    :param error_msg: The error message to raise if the value is invalid.
    :returns: A validator function ready to be used by pydantic.BeforeValidator
    """

    def validate(value: str) -> str:
        """Validate the given string with the outer regex, raising the error message.

        :param value: a string to be validated
        :returns: that same string if it's valid.
        :raises: ValueError if the string is invalid.
        """
        value = str(value)
        if not regex.match(value):
            raise ValueError(error_msg)
        return value

    return validate


def _validate_list_is_unique(value: list[T]) -> list[T]:
    value_set = set(value)
    if len(value_set) == len(value):
        return value
    dupes = [item for item, count in collections.Counter(value).items() if count > 1]
    raise ValueError(f"Duplicate values in list: {dupes}")


def _validate_relative_path_str(path: str) -> str:
    """Validate that the given string matches a relative path.

    :param path: A string that can be parsed as a path.
    :returns: The same string if valid.
    :raises: ValueError if the string is not a valid relative path.
    """
    if not path:
        raise ValueError("path cannot be empty")
    if path.startswith("/"):
        raise ValueError(f"{path!r} must be a relative path (cannot start with '/')")
    return path


RelativePathStr = Annotated[
    str,
    # The functional validator is used to provide better error messages when parsing
    # this type.
    BeforeValidator(_validate_relative_path_str),
    # The field here is used to provide information in the JSON schema and IDEs.
    Field(description="relative path", min_length=1, pattern=re.compile(r"^[^\/].*")),
]

UniqueList = Annotated[list[T], AfterValidator(_validate_list_is_unique)]

# matches '<package-name>_<slice_name>'
# source: https://github.com/canonical/chisel/blob/97c0d1d0d064339ce5f96dd2205a6f081c6be305/internal/apacheutil/util.go#L24
CHISEL_SLICE_PATTERN = r"^([a-z0-9](?:-?[.a-z0-9+]){1,})_([a-z](?:-?[a-z0-9]){2,})$"
CHISEL_SLICE_COMPILED_REGEX = re.compile(CHISEL_SLICE_PATTERN)
MESSAGE_INVALID_CHISEL_SLICE = (
    "invalid Chisel slice: slices must be in the form '<package>_<slice>'. See "
    "https://ubuntu.com/chisel/docs/latest/explanation/slices/#naming-convention "
    "for the naming rules."
)

ChiselSliceStr = Annotated[
    str,
    BeforeValidator(
        get_validator_by_regex(
            CHISEL_SLICE_COMPILED_REGEX, MESSAGE_INVALID_CHISEL_SLICE
        )
    ),
    Field(
        description="Chisel slice reference",
        pattern=CHISEL_SLICE_PATTERN,
    ),
]

SingleEntryDict = Annotated[
    dict[T, Tv],
    Field(min_length=1, max_length=1),
]
