# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""Sandbox managing an environment to execute commands in."""

import logging
import multiprocessing
import os
import re
import signal
import subprocess
from collections.abc import Callable, Sequence
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from craft_parts import errors
from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


SWAPPER_SUFFIX = "REAL"


class FileSwapper:
    """File swapper to temporarily replace a file with another."""

    _target: Path
    _base_path: Path
    _content: str

    def __init__(self, target: Path, content: str) -> None:
        self._target = target
        self._content = content

    def _swapped(self) -> Path:
        """Path of the swapped file."""
        return self._base_path / Path(f"{self._target}.{SWAPPER_SUFFIX}")

    def swap(self, base_path: Path) -> None:
        """Backup the target file and replace it with the provided content."""
        self._base_path = base_path
        target = base_path / self._target
        if not target.exists() or not target.is_file():
            return
        os.rename(
            target,
            self._swapped(),
        )
        with target.open("w") as f:
            f.write(self._content)

    def restore(self) -> None:
        """Restore the swapped file."""
        if not self._swapped().exists() or not self._swapped().is_file():
            return
        os.replace(
            self._swapped(),
            self._base_path / self._target,
        )


class Diversion:
    """Diversion handler."""

    _dpkg_divert: str = "dpkg-divert"
    _target: Path
    _target_diverted: Path
    _base_path: Path

    def __init__(
        self,
        target: Path,
    ) -> None:
        self._target = target
        self._target_diverted = Path(f"{target}.dpkg-divert")

    def _common_args(self) -> list[str]:
        """Define common diversion arguments."""
        return [
            "--local",
            f"--root={self._base_path}",
            "--rename",
            str(self._target),
        ]

    def divert(self, base_path: Path) -> None:
        """Divert the target."""
        self._base_path = base_path
        command = [
            self._dpkg_divert,
            "--divert",
            str(self._target_diverted),
            *self._common_args(),
        ]
        os_utils.process_run(command, logger.debug)

    def undivert(self) -> None:
        """Remove the diversion.

        Trying to remove a non-existent diversion will not return an error.
        So this is fine to always try to undivert even if the diversion did
        not happen.
        """
        command = [self._dpkg_divert, "--remove", *self._common_args()]
        os_utils.process_run(command, logger.debug)


class Mount:
    """Mount entry for sandbox setup."""

    _fstype: str | None
    _src: str
    _relative_mountpoint: str
    _options: list[str] | None = None
    _mountpoint: Path | None = None
    _lazy_umount: bool = False

    def __init__(
        self,
        fstype: str | None,
        src: str,
        relative_mountpoint: str,
        *,
        options: list[str] | None = None,
    ) -> None:
        self._fstype = fstype
        self._src = src
        self._relative_mountpoint = relative_mountpoint
        if options:
            self._options = options

    def mount(self, base_path: Path) -> None:
        """Mount the mountpoint.

        :param base_path: path to mount the mountpoint under.
        """
        args: list[str] = []
        if self._options:
            args.extend(self._options)
        if self._fstype:
            args.append(f"-t{self._fstype}")

        self._mountpoint = base_path / self._relative_mountpoint.lstrip("/")
        pid = os.getpid()
        if not self._mountpoint.exists():
            raise errors.SandboxMountError(
                mountpoint=str(self._mountpoint),
                message=f"mountpoint {str(self._mountpoint)} does not exist.",
            )

        logger.debug("[pid=%d] mount %r on chroot", pid, str(self._mountpoint))
        os_utils.mount(self._src, str(self._mountpoint), *args)

    def umount(self) -> None:
        """Umount the mountpoint."""
        pid = os.getpid()

        if self._mountpoint and self._mountpoint.exists():
            logger.debug("[pid=%d] umount: %r", pid, str(self._mountpoint))

            os_utils.mount(str(self._mountpoint), "--make-rprivate")
            args: list[str] = ["--recursive"]

            if self._lazy_umount:
                args.append("--lazy")
            os_utils.umount(str(self._mountpoint), *args)


def _runner(
    path: Path,
    conn: Connection,
    target: Callable[..., str | None],
    args: tuple[str],
    kwargs: dict[str, Any],
) -> None:
    """Chroot to the sandbox and call the target function."""
    pid = os.getpid()
    logger.debug("[pid=%d] child process: target=%r", pid, target)
    try:
        logger.debug("[pid=%d] chroot to %r", pid, path)
        os.chdir(path)
        os.chroot(path)
        res = target(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        conn.send((None, str(exc)))
        return

    conn.send((res, None))


_default_mounts: tuple[Mount, ...] = (
    Mount(
        fstype=None,
        src="/etc/resolv.conf",
        relative_mountpoint="etc/resolv.conf",
        options=["--bind"],
    ),
    Mount(fstype="proc", src="proc", relative_mountpoint="proc"),
    Mount(fstype="sys", src="sys", relative_mountpoint="sys"),
    Mount(
        fstype="devtmpfs",
        src="devtmpfs",
        relative_mountpoint="/dev",
    ),
    Mount(
        fstype="devpts",
        src="devpts",
        relative_mountpoint="/dev/pts",
        options=["-o", "nodev,nosuid"],
    ),
)

_default_diversions: tuple[Diversion, ...] = (
    Diversion(target=Path("/usr/sbin/policy-rc.d")),
)

_start_stop_daemon_content = """#!/bin/sh
echo
echo "Warning: Fake start-stop-daemon called, doing nothing"
"""

_initctl_content = """#!/bin/sh
if [ "$1" = version ]; then exec /sbin/initctl.REAL "$@"; fi
echo
echo "Warning: Fake initctl called, doing nothing"
"""

_default_swaps: tuple[FileSwapper, ...] = (
    FileSwapper(
        target=Path("/sbin/start-stop-daemon"), content=_start_stop_daemon_content
    ),
    FileSwapper(target=Path("/sbin/initctl"), content=_initctl_content),
)


class Sandbox:
    """Sandbox manager."""

    _mounts: Sequence[Mount]
    _diversions: Sequence[Diversion]
    _swaps: Sequence[FileSwapper]
    _root: Path

    def __init__(
        self,
        *,
        root: Path,
        mounts: Sequence[Mount] | None = _default_mounts,
        diversions: Sequence[Diversion] | None = _default_diversions,
        swaps: Sequence[FileSwapper] | None = _default_swaps,
        # Extend enable adding mounts/diversions/swaps to the default ones
        extend_mounts: Sequence[Mount] | None = None,
        extend_diversions: Sequence[Diversion] | None = None,
        extend_swaps: Sequence[FileSwapper] | None = None,
    ) -> None:
        self._root = root
        self._mounts = mounts
        if extend_mounts:
            self._mounts.extend(extend_mounts)
        self._diversions = diversions
        if extend_diversions:
            self._diversions.extend(extend_diversions)
        self._swaps = swaps
        if extend_swaps:
            self._swaps.extend(extend_swaps)

    def _setup_mounts(self) -> None:
        for entry in self._mounts:
            entry.mount(base_path=self._root)

    def _setup_diversions(self) -> None:
        for entry in self._diversions:
            entry.divert(base_path=self._root)

    def _setup_swaps(self) -> None:
        for entry in self._swaps:
            entry.swap(base_path=self._root)

    def _setup(self) -> None:
        """Sandbox preparation."""
        logger.debug("setup sandbox: %r", str(self._root))

        self._setup_mounts()
        self._setup_diversions()
        self._setup_swaps()

        logger.debug("sandbox setup complete")

    def _cleanup_processes(self) -> None:
        """Clean potentially dangling process in the sandbox.

        Helps being reasonably sure mountpoints can be umounted.
        """
        for d in (self._root / "proc").iterdir():
            if (
                d.is_dir()
                and re.match(r"\d+", d.stem)
                and (d / "root").readlink() == self._root
            ):
                logger.debug(f"Found a dangling process: {d}. Killing it.")
                os.kill(int(d.stem), signal.SIGKILL)

    def _cleanup_mounts(self) -> None:
        """Umounts mounted dir.

        Try to umount as many mountpoint as possible to leave the system
        as clean as possible.
        """
        umount_errors: list[str] = []
        for entry in reversed(self._mounts):
            try:
                entry.umount()
            except subprocess.CalledProcessError as err:  # noqa: PERF203
                msg = str(err)
                if err.stderr:
                    msg += f" ({err.stderr.strip()!s})"
                umount_errors.append(msg)

        if umount_errors:
            raise errors.SandboxError(
                brief="Failed to clean the sandbox", details="\n".join(umount_errors)
            )

    def _cleanup_diversions(self) -> None:
        for entry in self._diversions:
            entry.undivert()

    def _cleanup_swaps(self) -> None:
        for entry in self._swaps:
            entry.restore()

    def _cleanup(self) -> None:
        """Sandbox cleanup."""
        logger.debug("cleanup the sandbox: %r", self._root)
        self._cleanup_processes()
        self._cleanup_diversions()
        self._cleanup_swaps()
        self._cleanup_mounts()

    def execute(
        self, target: Callable[..., str | None], *args: Any, **kwargs: Any
    ) -> Any:  # noqa: ANN401
        """Execute a callable in the sandbox environment.

        :param target: The callable to run in the sandbox environment.
        :param args: Arguments for target.
        :param kwargs: Keyword arguments for target.

        :returns: The target function return value.
        """
        logger.debug("[pid=%d] parent process", os.getpid())
        parent_conn, child_conn = multiprocessing.Pipe()
        child = multiprocessing.Process(
            target=_runner, args=(self._root, child_conn, target, args, kwargs)
        )
        logger.debug("[pid=%d] set up the sandbox", os.getpid())
        try:
            self._setup()
            child.start()
            res, err = parent_conn.recv()
            child.join()
        finally:
            logger.debug("[pid=%d] clean up the sandbox", os.getpid())
            self._cleanup()

        if isinstance(err, str):
            raise errors.SandboxExecutionError(err)

        return res
