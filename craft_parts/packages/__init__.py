# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2023 Canonical Ltd.
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
from typing import TYPE_CHECKING, Type

from . import errors, snaps
from .normalize import fix_pkg_config
from .platform import is_deb_based, is_dnf_based, is_yum_based

if TYPE_CHECKING:
    from .base import BaseRepository

# pylint: disable=import-outside-toplevel


def _get_repository_for_platform() -> Type["BaseRepository"]:
    if is_deb_based():
        from .deb import Ubuntu

        return Ubuntu

    if is_yum_based():
        from .yum import YUMRepository

        return YUMRepository

    if is_dnf_based():
        from .dnf import DNFRepository

        return DNFRepository

    from .base import DummyRepository

    return DummyRepository


Repository = _get_repository_for_platform()
