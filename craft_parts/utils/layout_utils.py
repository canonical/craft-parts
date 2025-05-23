# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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
"""Layout utilities."""

from typing import Any

from craft_parts import errors, features
from craft_parts.layouts import LayoutItem


def validate_layout(data: list[dict[str, Any]]) -> None:
    """Validate a layout.

    :param data: The repository data to validate.
    """
    if not isinstance(data, list):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError("value must be a dictionary")
    layout = [LayoutItem.unmarshal(item) for item in data]

    if layout[0].mount != "/":
        raise ValueError("A filesystem first entry must map the '/' mount.")


def validate_layouts(layouts: dict[str, Any] | None) -> None:
    """Validate the layouts section.

    If layouts are defined then both partition and overlay features must
    be enabled.
    A layout dict must only have a single "default" entry.
    The first entry in default must map the '/' mount.
    """
    if not layouts:
        return

    if (
        not features.Features().enable_partitions
        or not features.Features().enable_overlay
    ):
        raise errors.FeatureError(
            "Filesystems are defined but partition feature or overlay feature are not enabled."
        )

    if len(layouts) > 1:
        raise errors.FeatureError("One and only one filesystem must be defined.")

    default_layout = layouts.get("default")
    if default_layout is None:
        raise errors.FeatureError("A 'default' filesystem must be defined.")

    if len(default_layout) == 0:
        raise errors.FeatureError(
            "The 'default' filesystem must defined at least one entry."
        )

    default_layout_obj = LayoutItem.unmarshal(default_layout[0])

    if default_layout_obj.mount != "/":
        raise errors.FeatureError(
            "The 'default' filesystem first entry must map the '/' mount."
        )
