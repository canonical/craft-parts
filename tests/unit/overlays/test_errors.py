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

from craft_parts.overlays import errors


def test_overlay_mount_error():
    err = errors.OverlayMountError("/mountpoint", "something wrong happened")
    assert err.mountpoint == "/mountpoint"
    assert err.message == "something wrong happened"
    assert err.brief == (
        "Failed to mount overlay on /mountpoint: something wrong happened"
    )
    assert err.details is None
    assert err.resolution is None


def test_overlay_unmount_error():
    err = errors.OverlayUnmountError("/mountpoint", "something wrong happened")
    assert err.mountpoint == "/mountpoint"
    assert err.message == "something wrong happened"
    assert err.brief == "Failed to unmount /mountpoint: something wrong happened"
    assert err.details is None
    assert err.resolution is None


def test_overlay_chroot_execution_error():
    err = errors.OverlayChrootExecutionError("something wrong happened")
    assert err.message == "something wrong happened"
    assert err.brief == "Overlay environment execution error: something wrong happened"
    assert err.details is None
    assert err.resolution is None
