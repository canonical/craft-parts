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
from collections.abc import Callable, Mapping
from multiprocessing.connection import Connection
from pathlib import Path
from shutil import copytree, rmtree
from typing import Any

from craft_parts.utils import os_utils

from . import errors

logger = logging.getLogger(__name__)


def chroot(
    path: Path,
    target: Callable,
    use_host_sources: bool = False,  # noqa: FBT001, FBT002
    args: tuple[Any] = (),  # type: ignore  # noqa: PGH003
    kwargs: Mapping[str, Any] = {},
) -> Any:  # noqa: ANN401
    """Execute a callable in a chroot environment.

    :param path: The new filesystem root.
    :param target: The callable to run in the chroot environment.
    :param args: Arguments for target.
    :param kwargs: Keyword arguments for target.

    :returns: The target function return value.
    """
    logger.debug("[pid=%d] parent process", os.getpid())
    parent_conn, child_conn = multiprocessing.Pipe()
    child = multiprocessing.Process(
        target=_runner, args=(Path(path), child_conn, target, args, kwargs)
    )
    logger.debug("[pid=%d] set up chroot", os.getpid())
    _setup_chroot(path, use_host_sources)
    try:
        child.start()
        res, err = parent_conn.recv()
        child.join()
    finally:
        logger.debug("[pid=%d] clean up chroot", os.getpid())
        _cleanup_chroot(path, use_host_sources)

    if isinstance(err, str):
        raise errors.OverlayChrootExecutionError(err)

    return res


def _runner(
    path: Path,
    conn: Connection,
    target: Callable,
    args: tuple,
    kwargs: dict,
) -> None:
    """Chroot to the execution directory and call the target function."""
    logger.debug("[pid=%d] child process: target=%r", os.getpid(), target)
    try:
        logger.debug("[pid=%d] chroot to %r", os.getpid(), path)
        os.chdir(path)
        os.chroot(path)
        res = target(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        conn.send((None, str(exc)))
        return

    conn.send((res, None))


def _compare_os_release(host: os_utils.OsRelease, chroot: os_utils.OsRelease):
    """Compare OsRelease objects from host and chroot for compatibility. See _host_compatible_chroot."""
    if (host_val := host.id()) != (chroot_val := chroot.id()):
        errors.IncompatibleChrootError("id", host_val, chroot_val)

    if (host_val := host.version_id()) != (chroot_val := chroot.version_id()):
        errors.IncompatibleChrootError("version_id", host_val, chroot_val)


def _host_compatible_chroot(path: Path) -> bool:
    """Raise exception if host and chroot are not the same distrobution and release"""
    # Note: /etc/os-release is symlinked to /usr/lib/os-release
    # This could cause an issue if /etc/os-release is removed at any point.
    host_os_release = os_utils.OsRelease()
    chroot_os_release = os_utils.OsRelease(
        os_release_file=str(path / "/etc/os-release")
    )
    _compare_os_release(host_os_release, chroot_os_release)


def _setup_chroot(path: Path, use_host_sources: bool) -> None:
    """Prepare the chroot environment before executing the target function."""
    logger.debug("setup chroot: %r", path)
    if sys.platform == "linux":
        # base configuration
        _setup_chroot_mounts(path, _linux_mounts)

        if use_host_sources:
            _host_compatible_chroot(path)

            _setup_chroot_mounts(path, _ubuntu_apt_mounts)

    logger.debug("chroot setup complete")


def _cleanup_chroot(path: Path, use_host_sources: bool) -> None:
    """Clean the chroot environment after executing the target function."""
    logger.debug("cleanup chroot: %r", path)
    if sys.platform == "linux":
        _cleanup_chroot_mounts(path, _linux_mounts)

        if use_host_sources:
            # Note: no need to check if host is compatible since
            # we already called _host_compatible_chroot in _setup_chroot
            _cleanup_chroot_mounts(path, _ubuntu_apt_mounts)

    logger.debug("chroot cleanup complete")


class _Mount:
    def __init__(
        self, src: str | Path, mountpoint: str | Path, *args, fstype: str | None = None
    ) -> None:
        """Mount entry for chroot setup."""

        self.src = Path(src)
        self.mountpoint = Path(mountpoint)
        self.args = list(args)

        if fstype is not None:
            self.args.append(f"-t{fstype}")

    @staticmethod
    def get_abs_path(path: Path, chroot_path: Path):
        return path / str(chroot_path).lstrip("/")

    def mountpoint_exists(self, mountpoint: Path):
        return mountpoint.exists()

    def _mount(self, src: Path, mountpoint: Path, *args: str) -> None:
        logger.debug("[pid=%d] mount %r on chroot", os.getpid(), src)
        os_utils.mount(str(src), str(mountpoint), *args)

    def _umount(self, mountpoint: Path, *args: str) -> None:
        logger.debug("[pid=%d] umount: %r", os.getpid(), mountpoint)
        os_utils.umount(str(mountpoint), *args)

    def mount_to(self, chroot: Path, *args: str) -> None:
        abs_mountpoint = self.get_abs_path(chroot, self.mountpoint)

        if not self.mountpoint_exists(abs_mountpoint):
            logger.warning("[pid=%d] mount: %r not found!", os.getpid(), abs_mountpoint)
            return

        self._mount(self.src, abs_mountpoint, *self.args, *args)

    def unmount_from(self, chroot: Path, *args: str) -> None:
        abs_mountpoint = self.get_abs_path(chroot, self.mountpoint)

        if not self.mountpoint_exists(abs_mountpoint):
            logger.warning("[pid=%d] umount: %r not found!", os.getpid(), chroot)
            return

        self._umount(abs_mountpoint, *args)


class _BindMount(_Mount):
    bind_type = "bind"

    def __init__(
        self,
        src: str | Path,
        mountpoint: str | Path,
        *args: str,
    ) -> None:
        super().__init__(src, mountpoint, f"--{self.bind_type}", *args)

    def mountpoint_exists(self, mountpoint: Path):
        if self.src.exists() and self.src.is_file():
            return mountpoint.parent.exists()

        return mountpoint.exists()

    def _mount(self, src: Path, mountpoint: Path, *args: str) -> None:
        if src.is_dir():
            # remove existing content of dir
            if mountpoint.exists():
                rmtree(mountpoint)

            # prep mount point
            mountpoint.mkdir(exist_ok=True)

        elif src.is_file():
            # remove existing file
            if mountpoint.exists():
                mountpoint.unlink()
            else:
                mountpoint.parent.mkdir(exist_ok=True)

            # prep mount point
            mountpoint.touch()
        else:
            raise FileNotFoundError(f"Path not found: {src}")

        super()._mount(src, mountpoint, *args)


class _RBindMount(_BindMount):
    bind_type = "rbind"

    def _umount(self, mountpoint: Path, *args) -> None:
        super()._umount(mountpoint, "--recursive", "--lazy", *args)


class _TempFSClone(_Mount):
    def __init__(self, src: str, mountpoint: str, *args) -> None:
        super().__init__(src, mountpoint, *args, fstype="tmpfs")

    def _mount(self, src: Path, mountpoint: Path, *args) -> None:
        if src.is_dir():
            # remove existing content of dir
            if mountpoint.exists():
                rmtree(mountpoint)

            # prep mount point
            mountpoint.mkdir(parents=True, exist_ok=True)

        elif src.is_file():
            raise NotADirectoryError(f"Path is a directory: {src}")
        else:
            raise FileNotFoundError(f"Path not found: {src}")

        super()._mount(src, mountpoint, *args)

        copytree(src, mountpoint, dirs_exist_ok=True)


# Essential filesystems to mount in order to have basic utilities and
# name resolution working inside the chroot environment.
#
# Some images (such as cloudimgs) symlink ``/etc/resolv.conf`` to
# ``/run/systemd/resolve/stub-resolv.conf``. We want resolv.conf to be
# a regular file to bind-mount the host resolver configuration on.
#
# There's no need to restore the file to its original condition because
# this operation happens on a temporary filesystem layer.
_linux_mounts: list[_Mount] = [
    _BindMount("/etc/resolv.conf", "/etc/resolv.conf"),
    _Mount("proc", "/proc", fstype="proc"),
    _Mount("sysfs", "/sys", fstype="sysfs"),
    # Device nodes require MS_REC to be bind mounted inside a container.
    _RBindMount("/dev", "/dev", "--make-rprivate"),
]

# Mounts required to import host's Ubuntu Pro apt configuration to chroot
# TODO: parameterize this per linux distribution / package manager
_ubuntu_apt_mounts = [
    _TempFSClone("/etc/apt", "/etc/apt"),
    _BindMount("/usr/share/ca-certificates/", "/usr/share/ca-certificates/"),
    _BindMount("/etc/ssl/certs/", "/etc/ssl/certs/"),
    _BindMount("/etc/ca-certificates.conf", "/etc/ca-certificates.conf"),
]


def _setup_chroot_mounts(path: Path, mounts: list[_Mount]) -> None:
    """Linux-specific chroot environment preparation."""

    for entry in mounts:
        entry.mount_to(path)


def _cleanup_chroot_mounts(path: Path, mounts: list[_Mount]) -> None:
    """Linux-specific chroot environment cleanup."""

    for entry in reversed(mounts):
        entry.unmount_from(path)
