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

"""Execute a callable in a chroot environment."""

import logging
import multiprocessing
import os
import sys
from collections import namedtuple
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


def chroot(path: Path, target: Callable, *args, **kwargs) -> Any:
    """Execute a callable in a chroot environment."""
    logger.debug("[pid=%d] parent process", os.getpid())
    parent_conn, child_conn = multiprocessing.Pipe()
    child = multiprocessing.Process(
        target=_runner, args=(Path(path), child_conn, target, args, kwargs)
    )
    _setup_chroot(path)
    try:
        child.start()
        res, exc = parent_conn.recv()
        child.join()
    finally:
        _cleanup_chroot(path)

    if isinstance(exc, Exception):
        raise exc

    return res


def _runner(
    path: Path,
    conn: Connection,
    target: Callable,
    args: Tuple,
    kwargs: Dict,
) -> None:
    logger.debug("[pid=%d] child process: target=%r", os.getpid(), target)
    try:
        logger.debug("[pid=%d] chroot to %r", os.getpid(), path)
        os.chdir(path)
        os.chroot(path)
        res = target(*args, **kwargs)
    except Exception as exc:  # pylint: disable=broad-except
        conn.send((None, exc))
        return

    conn.send((res, None))
    sys.exit()


def _setup_chroot(path: Path) -> None:
    logger.debug("setup chroot: %r", path)
    if sys.platform == "linux":
        _setup_chroot_linux(path)


def _cleanup_chroot(path: Path) -> None:
    logger.debug("cleanup chroot: %r", path)
    if sys.platform == "linux":
        _cleanup_chroot_linux(path)


_Mount = namedtuple("_Mount", ["fstype", "src", "mountpoint", "option"])

_linux_mounts: List[_Mount] = [
    _Mount(None, "/etc/resolv.conf", "/etc/resolv.conf", "--bind"),
    _Mount("proc", "proc", "/proc", None),
    _Mount("sysfs", "sysfs", "/sys", None),
    _Mount(None, "/dev", "/dev", "--bind"),
    # _Mount("tmpfs", "tmpfs", "/dev/shm", None),
]


def _setup_chroot_linux(path: Path) -> None:
    for entry in _linux_mounts:
        args = []
        if entry.option:
            args.append(entry.option)
        if entry.fstype:
            args.append(f"-t{entry.fstype}")

        mountpoint = path / entry.mountpoint.lstrip("/")

        # Some images (such as cloudimgs) symlink ``/etc/resolv.conf`` to
        # ``/run/systemd/resolve/stub-resolv.conf``. We want resolv.conf to be
        # a regular file to bind-mount the host resolver configuration on.
        #
        # There's no need to restore the file to its original conditions because
        # this operation happens on a temporary filesystem layer.
        if mountpoint.is_symlink():
            mountpoint.unlink()
            mountpoint.touch()

        logger.debug("[pid=%d] mount %r on chroot", os.getpid(), str(mountpoint))
        os_utils.mount(entry.src, str(mountpoint), *args)


def _cleanup_chroot_linux(path: Path) -> None:
    for entry in reversed(_linux_mounts):
        mountpoint = path / entry.mountpoint.lstrip("/")
        logger.debug("[pid=%d] umount: %r", os.getpid(), str(mountpoint))
        os_utils.umount(str(mountpoint))
