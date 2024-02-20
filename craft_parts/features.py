# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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

"""Global features to be configured by the application."""

import contextlib
import dataclasses
import logging

from craft_parts.errors import FeatureError
from craft_parts.utils import Singleton

logger = logging.getLogger()


@dataclasses.dataclass(frozen=True)
class Features(metaclass=Singleton):
    """Configurable craft-parts features.

    :cvar enable_overlay: Enables the overlay step.
    :cvar enable_partitions: Enables the usage of partitions.
    """

    enable_overlay: bool = False
    enable_partitions: bool = False

    def __init__(
        self, *, enable_overlay: bool = False, enable_partitions: bool = False
    ) -> None:
        """Initialize craft-parts features.

        :param enable_overlay: Enables the overlay step.
        :param enable_partitions: Enables the usage of partitions.

        :raises FeatureError: If mutually exclusive features are enabled.
        """
        if enable_overlay and enable_partitions:
            raise FeatureError(
                message="Cannot enable overlay and partition features.",
                details=("Overlay and partition features are mutually exclusive."),
            )
        object.__setattr__(self, "enable_overlay", enable_overlay)
        object.__setattr__(self, "enable_partitions", enable_partitions)

    @classmethod
    def reset(cls) -> None:
        """Delete stored class instance."""
        logger.warning("deleting current features configuration")
        with contextlib.suppress(KeyError):
            del cls._instances[cls]
