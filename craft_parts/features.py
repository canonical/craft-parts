# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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

from craft_parts.utils import Singleton

logger = logging.getLogger()


@dataclasses.dataclass(frozen=True)
class Features(metaclass=Singleton):
    """Configurable craft-parts features."""

    enable_overlay: bool = False

    @classmethod
    def reset(cls) -> None:
        """Delete stored class instance."""
        logger.warning("deleting current features configuration")
        with contextlib.suppress(KeyError):
            del cls._instances[cls]
