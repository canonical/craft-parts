# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

"""Utilities and helpers."""

from typing import Any, Dict


def package_name() -> str:
    """Return the topmost package name."""
    return __name__.split(".", maxsplit=1)[0]


class Singleton(type):
    """Singleton metaclass."""

    _instances: Dict = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Return an existing instance, or create a new instance."""
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
            return instance

        if args or kwargs:
            raise RuntimeError("parameters can only be set once")

        return cls._instances[cls]
