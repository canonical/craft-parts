# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2025 Canonical Ltd.
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

import logging
from typing import Any, TYPE_CHECKING, cast

from . import errors, snaps
from .normalize import fix_pkg_config
from .platform import is_deb_based, is_dnf_based, is_yum_based

if TYPE_CHECKING:
    from .base import BaseRepository

logger = logging.getLogger(__name__)

# pylint: disable=import-outside-toplevel


def _get_repository_for_platform() -> type["BaseRepository"]:
    if is_deb_based():
        from .deb import Ubuntu  # noqa: PLC0415

        return Ubuntu

    if is_yum_based():
        from .yum import YUMRepository  # noqa: PLC0415

        return YUMRepository

    if is_dnf_based():
        from .dnf import DNFRepository  # noqa: PLC0415

        return DNFRepository

    from .base import DummyRepository  # noqa: PLC0415

    return DummyRepository


class _RepositoryProxy:
    """Dynamic dispatcher for repository instances."""

    def __getattr__(self, attr: str) -> Any:  # noqa: ANN401
        repo = _get_repository_for_platform()
        logger.debug("get repository attribute: attr=%s, repository:%s", attr, repo)
        return getattr(repo, attr)

    def __setattr__(self, attr: str, value: Any) -> None:  # noqa: ANN401
        repo = _get_repository_for_platform()
        logger.debug(
            "set repository attribute: attr=%s, value=%s, repo:%s", attr, value, repo
        )
        setattr(repo, attr, value)


Repository = cast("BaseRepository", _RepositoryProxy())

__all__ = [
    "errors",
    "fix_pkg_config",
    "Repository",
    "snaps",
]
