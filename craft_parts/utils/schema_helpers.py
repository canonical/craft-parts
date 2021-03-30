# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2018 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Helpers to reformat jsonschema error messages."""

import collections
import contextlib
from typing import Dict, List

import jsonschema  # type: ignore

from craft_parts.utils import formatting_utils

# dict of jsonschema validator -> cause pairs. Wish jsonschema just gave us
# better messages.
_VALIDATION_ERROR_CAUSES = {
    "maxLength": "maximum length is {validator_value}",
    "minLength": "minimum length is {validator_value}",
}


def determine_preamble(error: jsonschema.ValidationError) -> str:
    """Obtain the jsonschema validation error message preamble.

    :param error: The jsonschema validation error.

    :returns: The error preamble.
    """
    messages = []
    path = _determine_property_path(error)
    if path:
        messages.append(
            "The '{}' property does not match the required schema:".format(
                "/".join(path)
            )
        )
    return " ".join(messages)


def determine_cause(error: jsonschema.ValidationError) -> str:
    """Obtain the cause from the jsonschema validation error.

    :param error: The jsonschema validation error.

    :returns: The jsonschema validation error.
    """
    messages: List[str] = []

    with contextlib.suppress(TypeError, KeyError):
        msg: str = error.validator_value["validation-failure"].format(error)
        messages.append(msg)

    # The schema itself may have a custom validation error message. If so,
    # use it as well.
    with contextlib.suppress(AttributeError, TypeError, KeyError):
        key = error
        if (
            error.schema.get("type") == "object"
            and error.validator == "additionalProperties"
        ):
            key = list(error.instance.keys())[0]

        msg = error.schema["validation-failure"].format(key)
        messages.append(msg)

    # anyOf failures might have usable context... try to improve them a bit
    if error.validator == "anyOf":
        contextual_messages: Dict[str, List[str]] = collections.OrderedDict()
        for contextual_error in error.context:
            key = contextual_error.schema_path.popleft()
            if key not in contextual_messages:
                contextual_messages[key] = []
            message = contextual_error.message
            if message:
                # Sure it starts lower-case (not all messages do)
                contextual_messages[key].append(message[0].lower() + message[1:])

        oneof_messages: List[str] = []
        for key, value in contextual_messages.items():
            oneof_messages.append(formatting_utils.humanize_list(value, "and", "{}"))

        messages.append(formatting_utils.humanize_list(oneof_messages, "or", "{}"))

    return " ".join(messages)


def determine_supplemental_info(error: jsonschema.ValidationError) -> str:
    """Obtain additional information from the jsonschema validation error.

    :param error: The jsonschema validation error.
    """
    message = _VALIDATION_ERROR_CAUSES.get(error.validator, "").format(
        validator_value=error.validator_value
    )

    if not message and error.validator == "anyOf":
        message = _interpret_anyof(error)

    if not message and error.cause:
        message = error.cause

    return message


def _determine_property_path(error: jsonschema.ValidationError) -> List[str]:
    path: List[str] = []
    absolute_path = error.absolute_path
    while absolute_path:
        element = absolute_path.popleft()
        # assume numbers are indices and use 'xxx[123]' notation.
        if isinstance(element, int):
            path[-1] = "{}[{}]".format(path[-1], element)
        else:
            path.append(str(element))

    return path


def _interpret_anyof(error: jsonschema.ValidationError) -> str:
    """Interpret a validation error caused by the anyOf validator.

    :returns: A string containing a (hopefully) helpful validation error
        message. It may be empty.
    """
    usages = []
    try:
        for validator in error.validator_value:
            usages.append(validator["usage"])
    except (TypeError, KeyError):
        return ""

    return "must be one of {}".format(
        formatting_utils.humanize_list(usages, "or", "{}")
    )
