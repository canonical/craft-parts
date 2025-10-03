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
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar

from craft_parts.utils import os_utils

from . import errors

if TYPE_CHECKING:
    from collections.abc import Callable
    from multiprocessing.connection import Connection

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def chroot(
    path: Path,
    target: Callable[..., _T],
    mount_package_sources: bool = False,  # noqa: FBT001, FBT002
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

    # This typehint technically should be "Connection[Any, tuple[_T, None] | tuple[None, str]]"
    # However, types surrounding multiprocessing are finnicky at best and the way we handle the
    # result here makes the typehint effectively true, since we don't attempt to access the first
    # field of the tuple unless the second field is None.
    parent_conn: Connection[Any, tuple[_T, str | None]]
    parent_conn, child_conn = multiprocessing.Pipe()
    child = multiprocessing.Process(
        target=_runner, args=(Path(path), child_conn, target, args, kwargs)
    )
    logger.debug("[pid=%d] set up chroot", os.getpid())
    _setup_chroot(path, mount_package_sources)
    try:
        child.start()
        res, err = parent_conn.recv()
        child.join()
    finally:
        logger.debug("[pid=%d] clean up chroot", os.getpid())
        _cleanup_chroot(path, mount_package_sources)

    if isinstance(err, str):
        raise errors.OverlayChrootExecutionError(err)

    return res


def _runner(
    path: Path,
    conn: Connection[tuple[_T, str | None], Any],
    target: Callable[..., _T],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Chroot to the execution directory and call the target function."""
    logger.debug("[pid=%d] child process: target=%r", os.getpid(), target)
    try:
        logger.debug("[pid=%d] chroot to %r", os.getpid(), path)
        os.chdir(path)
        os.chroot(path)
        res = target(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        # Just send None for data since it won't be accessed anyways
        conn.send((None, str(exc)))  # type: ignore[arg-type]
        return

    conn.send((res, None))


def _compare_os_release(host: os_utils.OsRelease, chroot: os_utils.OsRelease) -> None:
    """Compare OsRelease objects from host and chroot for compatibility. See _host_compatible_chroot."""
    if (host_val := host.id()) != (chroot_val := chroot.id()):
        raise errors.IncompatibleChrootError("id", host_val, chroot_val)

    if (host_val := host.version_id()) != (chroot_val := chroot.version_id()):
        raise errors.IncompatibleChrootError("version_id", host_val, chroot_val)


def _host_compatible_chroot(path: Path) -> None:
    """Raise exception if host and chroot are not the same distribution and release."""
    # Note: /etc/os-release is symlinked to /usr/lib/os-release
    # This could cause an issue if /etc/os-release is removed at any point.
    host_os_release = os_utils.OsRelease()
    chroot_os_release = os_utils.OsRelease(
        os_release_file=str(path / "/etc/os-release")
    )
    _compare_os_release(host_os_release, chroot_os_release)


def _setup_chroot(path: Path, mount_package_sources: bool) -> None:  # noqa: FBT001
    """Prepare the chroot environment before executing the target function."""
    logger.debug("setup chroot: %r", path)
    if sys.platform == "linux":
        # base configuration
        _setup_chroot_mounts(path, _linux_mounts)

        if mount_package_sources:
            _host_compatible_chroot(path)

            _setup_chroot_mounts(path, _ubuntu_apt_mounts)

    logger.debug("chroot setup complete")


def _cleanup_chroot(path: Path, mount_package_sources: bool) -> None:  # noqa: FBT001
    """Clean the chroot environment after executing the target function."""
    logger.debug("cleanup chroot: %r", path)
    if sys.platform == "linux":
        _cleanup_chroot_mounts(path, _linux_mounts)

        if mount_package_sources:
            # Note: no need to check if host is compatible since
            # we already called _host_compatible_chroot in _setup_chroot
            _cleanup_chroot_mounts(path, _ubuntu_apt_mounts)

    logger.debug("chroot cleanup complete")


class _Mount:
    def __init__(
        self,
        src: str | Path,
        dst: str | Path,
        *args: str,
        fstype: str | None = None,
        skip_missing: bool = True,
    ) -> None:
        """Manage setup and clean up of chroot mounts.

        :param src: Mount source. This can be a device or path on the file system.
        :param dst: Point. Path to the mount point relative to the chroot mounted on.
        :param args: Additional args to pass to mount command.
        :param fstype: fstype arg to use when calling mount.
        :param skip_missing: skip mounts when dst_exists returns False.
        """
        self.src = Path(src)
        self.dst = Path(dst)
        self.args = [*args]
        self.skip_missing = skip_missing

        if fstype is not None:
            self.args.append(f"-t{fstype}")

        logger.debug("[pid=%d] Mount Manager %s", os.getpid(), self)

    def _mount(self, src: Path, chroot: Path, *args: str) -> None:
        abs_dst = self.get_abs_path(chroot, self.dst)
        os_utils.mount(str(src), str(abs_dst), *args)

    def _umount(self, chroot: Path, *args: str) -> None:
        abs_dst = self.get_abs_path(chroot, self.dst)
        os_utils.umount(str(abs_dst), *args)

    def get_abs_path(self, path: Path, chroot_path: Path) -> Path:
        """Make `chroot_path` relative to host `path`."""
        return path / str(chroot_path).lstrip("/")

    def dst_exists(self, chroot: Path) -> bool:
        """Return True if `self.dst` exists within `chroot`."""
        abs_dst = self.get_abs_path(chroot, self.dst)
        return abs_dst.is_symlink() or abs_dst.exists()

    def remove_dst(self, chroot: Path) -> None:
        """Remove `self.dst` if present to prepare mountpoint `self.dst`."""
        # Overriding this method is not required.

    def create_dst(self, chroot: Path) -> None:
        """Create mountpoint `self.dst` later used in mount call."""
        abs_dst = self.get_abs_path(chroot, self.dst)
        abs_dst.parent.mkdir(parents=True, exist_ok=True)

    def mount_to(self, chroot: Path, *args: str) -> None:
        """Mount `self.src` to `self.dst` within chroot."""
        logger.debug(f"Mounting {self.dst}")
        if self.dst_exists(chroot):
            self.remove_dst(chroot)
        elif self.skip_missing:
            abs_dst = self.get_abs_path(chroot, self.dst)
            logger.warning(
                "[pid=%d] mount: %r not found. Skipping", os.getpid(), abs_dst
            )
            return
        self.create_dst(chroot)
        self._mount(self.src, chroot, *self.args, *args)

    def unmount_from(self, chroot: Path, *args: str) -> None:
        """Unmount `self.dst` within chroot."""
        logger.debug(f"Mounting {self.dst}")
        if self.skip_missing and not self.dst_exists(chroot):
            abs_dst = self.get_abs_path(chroot, self.dst)
            logger.warning("[pid=%d] umount: %r not found!", os.getpid(), abs_dst)
            return

        self._umount(chroot, *args)


class _BindMount(_Mount):
    bind_type = "bind"

    def __init__(
        self,
        src: str | Path,
        dst: str | Path,
        *args: str,
        skip_missing: bool = True,
    ) -> None:
        """Manage setup and clean up of `--bind` mount chroot mounts.

        This subclass of _Mount contains extra support for creating mount points for
        individual files.
        :param src: Mount source. This can be a device or path on the file system.
        :param dst: Point. Path to the mount point relative to the chroot mounted on.
        :param args: Additional args to pass to mount command.
        :param skip_missing: skip mounts when dst_exists returns False.
        """
        super().__init__(
            src, dst, f"--{self.bind_type}", *args, skip_missing=skip_missing
        )

    def dst_exists(self, chroot: Path) -> bool:
        abs_dst = self.get_abs_path(chroot, self.dst)

        if self.src.is_file():
            return abs_dst.is_symlink() or abs_dst.exists() or abs_dst.parent.is_dir()

        return abs_dst.is_symlink() or abs_dst.exists()

    def create_dst(self, chroot: Path) -> None:
        abs_dst = self.get_abs_path(chroot, self.dst)

        if self.src.is_dir():
            abs_dst.mkdir(parents=True, exist_ok=True)
        elif self.src.is_file():
            abs_dst.touch()

    def remove_dst(self, chroot: Path) -> None:
        abs_dst = self.get_abs_path(chroot, self.dst)

        if abs_dst.is_symlink() or abs_dst.is_file():
            abs_dst.unlink()

    def _mount(self, src: Path, chroot: Path, *args: str) -> None:
        if not src.exists():
            raise FileNotFoundError(f"Path not found: {src}")

        super()._mount(src, chroot, *args)


class _RBindMount(_BindMount):
    bind_type = "rbind"

    def _umount(self, chroot: Path, *args: str) -> None:
        super()._umount(chroot, "--recursive", "--lazy", *args)


class _TempFSClone(_Mount):
    def __init__(
        self, src: str, dst: str, *args: str, skip_missing: bool = True
    ) -> None:
        """Manage setup and clean up of `--bind` mount chroot mounts.

        This subclass of _Mount contains extra support for creating mount points for
        individual files.
        :param src: Mount source. This can be a device or path on the file system.
        :param dst: Point. Path to the mount point relative to the chroot mounted on.
        :param args: Additional args to pass to mount command.
        :param skip_missing: skip mounts when dst_exists returns False.
        """
        super().__init__(src, dst, *args, fstype="tmpfs", skip_missing=skip_missing)

    def _mount(self, src: Path, chroot: Path, *args: str) -> None:
        if src.is_file():
            raise NotADirectoryError(f"Path is a file: {src}")
        if not src.exists():
            raise FileNotFoundError(f"Path not found: {src}")

        super()._mount(src, chroot, *args)

        abs_dst = self.get_abs_path(chroot, self.dst)
        copytree(src, abs_dst, dirs_exist_ok=True)


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
# Improvement: parameterize this per linux distribution / package manager
_ubuntu_apt_mounts = [
    _TempFSClone("/etc/apt", "/etc/apt", skip_missing=False),
    _BindMount(
        "/usr/share/ca-certificates/",
        "/usr/share/ca-certificates/",
        skip_missing=False,
    ),
    _BindMount("/usr/share/keyrings/", "/usr/share/keyrings/", skip_missing=True),
    _BindMount("/etc/ssl/certs/", "/etc/ssl/certs/", skip_missing=False),
    _BindMount(
        "/etc/ca-certificates.conf", "/etc/ca-certificates.conf", skip_missing=False
    ),
]


def _setup_chroot_mounts(path: Path, mounts: list[_Mount]) -> None:
    """Linux-specific chroot environment preparation."""
    for entry in mounts:
        entry.mount_to(path)


def _cleanup_chroot_mounts(path: Path, mounts: list[_Mount]) -> None:
    """Linux-specific chroot environment cleanup."""
    for entry in reversed(mounts):
        entry.unmount_from(path)
