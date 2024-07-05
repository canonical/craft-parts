# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021, 2024 Canonical Ltd.
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

"""Source handler definitions and helpers."""

from . import errors
from .base import SourceModel
from .deb_source import DebSource, DebSourceModel
from .file_source import FileSource, FileSourceModel
from .git_source import GitSource, GitSourceModel
from .local_source import LocalSource, LocalSourceModel
from .rpm_source import RpmSource, RpmSourceModel
from .sevenzip_source import SevenzipSource, SevenzipSourceModel
from .snap_source import SnapSource, SnapSourceModel
from .sources import SourceHandler, get_source_handler, get_source_type_from_uri
from .tar_source import TarSource, TarSourceModel
from .zip_source import ZipSource, ZipSourceModel

__all__ = [
    "errors",
    "SourceModel",
    "DebSource",
    "DebSourceModel",
    "FileSource",
    "FileSourceModel",
    "GitSource",
    "GitSourceModel",
    "LocalSource",
    "LocalSourceModel",
    "RpmSource",
    "RpmSourceModel",
    "SevenzipSource",
    "SevenzipSourceModel",
    "SnapSource",
    "SnapSourceModel",
    "SourceHandler",
    "TarSource",
    "TarSourceModel",
    "ZipSource",
    "ZipSourceModel",
    "get_source_handler",
    "get_source_type_from_uri",
]
