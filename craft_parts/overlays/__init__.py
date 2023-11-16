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

from .layers import LayerHash
from .layers import LayerStateManager
from .overlay_fs import is_opaque_dir
from .overlay_fs import is_whiteout_file
from .overlay_manager import LayerMount
from .overlay_manager import OverlayManager
from .overlay_manager import PackageCacheMount
from .overlays import is_oci_opaque_dir
from .overlays import is_oci_whiteout_file
from .overlays import oci_opaque_dir
from .overlays import oci_whited_out_file
from .overlays import oci_whiteout
from .overlays import visible_in_layer
