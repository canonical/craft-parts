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

import re
from typing import Annotated

from pydantic import BeforeValidator, Field


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
