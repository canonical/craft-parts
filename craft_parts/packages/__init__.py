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

"""Operations with platform-specific package repositories."""

from . import errors  # noqa: F401
from . import snaps  # noqa: F401
from .normalize import fix_pkg_config  # noqa: F401
from .platform import is_deb_based

# pylint: disable=import-outside-toplevel


def _get_repository_for_platform():
    if is_deb_based():
        from .deb import Ubuntu

        return Ubuntu

    from .base import DummyRepository

    return DummyRepository


Repository = _get_repository_for_platform()
