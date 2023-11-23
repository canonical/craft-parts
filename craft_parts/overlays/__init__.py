# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""Overlay filesystem management and helpers."""

from .layers import LayerHash, LayerStateManager
from .overlay_fs import is_opaque_dir, is_whiteout_file
from .overlay_manager import LayerMount, OverlayManager, PackageCacheMount
from .overlays import (
    is_oci_opaque_dir,
    is_oci_whiteout_file,
    oci_opaque_dir,
    oci_whited_out_file,
    oci_whiteout,
    visible_in_layer,
)
