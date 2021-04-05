# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""Text formatting utilities."""

from typing import Iterable, Sized


def humanize_list(
    items: Iterable[str], conjunction: str, item_format: str = "{!r}"
) -> str:
    """Format a list into a human-readable string.

    :param list items: List to humanize.
    :param str conjunction: The conjunction used to join the final element to
                            the rest of the list (e.g. 'and').
    :param str item_format: Format string to use per item.
    """
    if not items:
        return ""

    quoted_items = [item_format.format(item) for item in sorted(items)]
    if not quoted_items:
        return ""

    if len(quoted_items) == 1:
        return quoted_items[0]

    humanized = ", ".join(quoted_items[:-1])

    if len(quoted_items) > 2:
        humanized += ","

    return "{} {} {}".format(humanized, conjunction, quoted_items[-1])


def pluralize(container: Sized, if_one: str, if_multiple: str) -> str:
    """Return the appropriate plural form according to the number of elements."""
    if len(container) > 1:
        return if_multiple

    return if_one
