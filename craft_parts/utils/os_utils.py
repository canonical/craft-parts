# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

"""Utilities related to the operating system."""

import contextlib
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from craft_parts import errors

logger = logging.getLogger(__name__)

_WRITE_TIME_INTERVAL = 0.02


# TODO:stdmsg: replace/remove terminal-related utilities


class TimedWriter:
    """Enforce minimum times between writes.

    Ensure subsequent writes happen at least at the specified minimum
    interval apart from each other, otherwise hosts with low tick
    resolution may generate files with identical timestamps.
    """

    _last_write_time = 0.0

    @classmethod
    def write_text(
        cls,
        filepath: Path,
        text: str,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Write text to the specified file.

        :param filepath: The path to the file to write to.
        :param text: The text to write.
        :param encoding: The name of the encoding used to encode and
            decode the file. See the corresponding parameter in ``os.open``
            for details.
        :param errors: How encoding/decoding errors are handled, in the
            same format used in ``os.open``.
        """
        delta = time.time() - cls._last_write_time
        if delta < _WRITE_TIME_INTERVAL:
            time.sleep(_WRITE_TIME_INTERVAL - delta)

        filepath.write_text(text, encoding=encoding, errors=errors)

        cls._last_write_time = time.time()


def get_bin_paths(*, root: Path, existing_only=True) -> List[str]:
    """List common system executable paths.

    :param root: A path to prepend to each entry in the list.
    :param existing_only: Only list paths that are present in the system.

    :return: The list of executable paths.
    """
    paths = [
        root / "usr" / "sbin",
        root / "usr" / "bin",
        root / "sbin",
        root / "bin",
    ]

    return [str(p) for p in paths if not existing_only or p.exists()]


def get_include_paths(*, root: Path, arch_triplet: str) -> List[str]:
    """List common include paths.

    :param root: A path to prepend to each entry in the list.
    :arch_triplet: The machine-vendor-os platform triplet definition.

    :return: The list of include paths.
    """
    paths = [
        root / "include",
        root / "usr" / "include",
        root / "include" / arch_triplet,
        root / "usr" / "include" / arch_triplet,
    ]

    return [str(p) for p in paths if p.exists()]


def get_library_paths(
    *, root: Path, arch_triplet: str, existing_only=True
) -> List[str]:
    """List common library paths.

    :param root: A path to prepend to each entry in the list.
    :arch_triplet: The machine-vendor-os platform triplet definition.
    :param existing_only: Only list paths that are present in the system.

    :return: The list of library paths.
    """
    paths = [
        root / "lib",
        root / "usr" / "lib",
        root / "lib" / arch_triplet,
        root / "usr" / "lib" / arch_triplet,
    ]

    return [str(p) for p in paths if not existing_only or p.exists()]


def get_pkg_config_paths(*, root: Path, arch_triplet: str) -> List[str]:
    """List common pkg-config paths.

    :param root: A path to prepend to each entry in the list.
    :arch_triplet: The machine-vendor-os platform triplet definition.

    :return: The list of pkg-config paths.
    """
    paths = [
        root / "lib" / "pkgconfig",
        root / "lib" / arch_triplet / "pkgconfig",
        root / "usr" / "lib" / "pkgconfig",
        root / "usr" / "lib" / arch_triplet / "pkgconfig",
        root / "usr" / "share" / "pkgconfig",
        root / "usr" / "local" / "lib" / "pkgconfig",
        root / "usr" / "local" / "lib" / arch_triplet / "pkgconfig",
        root / "usr" / "local" / "share" / "pkgconfig",
    ]

    return [str(p) for p in paths if p.exists()]


def is_dumb_terminal() -> bool:
    """Verify whether the caller is running on a dumb terminal.

    :return: True if on a dumb terminal.
    """
    is_stdout_tty = os.isatty(1)
    is_term_dumb = os.environ.get("TERM", "") == "dumb"
    return not is_stdout_tty or is_term_dumb


def is_snap(application_name: str) -> bool:
    """Verify whether we're running as a snap.

    :application_name: The snap application name. If provided, check
        if it matches the snap name.
    """
    snap_name = os.environ.get("SNAP_NAME")
    res = snap_name == application_name

    logger.debug("is_snap: %s, SNAP_NAME set to %s", res, snap_name)

    return res


def is_inside_container() -> bool:
    """Determine if the application is in a container.

    :return: Whether the process is running inside a container.
    """
    for path in ["/.dockerenv", "/run/.containerenv"]:
        if os.path.exists(path):
            logger.debug("application running in a docker or podman (OCI) container")
            return True

    return False


def get_system_info() -> str:
    """Obtain running system information."""
    # Use subprocess directly here. common.run_output will use binaries out
    # of the snap, and we want to use the one on the host.
    try:
        if sys.platform == "linux":
            uname_cmd = [
                "uname",
                "--kernel-name",
                "--kernel-release",
                "--kernel-version",
                "--machine",
                "--processor",
                "--hardware-platform",
                "--operating-system",
            ]
        else:
            uname_cmd = ["uname", "-s", "-r", "-v", "-m", "-p"]

        output = subprocess.check_output(uname_cmd)
    except subprocess.CalledProcessError as err:
        logger.warning(
            "'uname' exited with code %d: unable to record machine manifest",
            err.returncode,
        )
        return ""

    try:
        uname = output.decode().strip()
    except UnicodeEncodeError:
        logger.warning("Could not decode output for 'uname' correctly")
        uname = output.decode("latin-1", "surrogateescape").strip()

    return uname


def mount(device: str, mountpoint: str, *args) -> None:
    """Mount a filesystem.

    :param device: The device to mount.
    :param mountpoint: Where the device will be mounted.
    :param *args: Additional arguments to ``mount(8)``.

    :raises subprocess.CalledProcessError: on error.
    """
    logger.debug("mount device=%r, mountpoint=%r, args=%r", device, mountpoint, args)
    subprocess.check_call(["/bin/mount", *args, device, mountpoint])


def mount_overlayfs(mountpoint: str, *args) -> None:
    """Mount an overlay filesystem using fuse-overlayfs.

    :param mountpoint: Where the device will be mounted.
    :param *args: Additional arguments to ``mount(8)``.

    :raises subprocess.CalledProcessError: on error.
    """
    logger.debug("fuse-overlayfs mountpoint=%r, args=%r", mountpoint, args)
    subprocess.check_call(["fuse-overlayfs", *args, mountpoint])


_UMOUNT_RETRIES = 5


def umount(mountpoint: str, *args) -> None:
    """Unmount a filesystem.

    :param mountpoint: The mount point or device to unmount.

    :raises subprocess.CalledProcessError: on error.
    """
    logger.debug("umount mountpoint=%r, args=%r", mountpoint, args)
    attempt = 0
    while True:  # unmount in Github CI fails randomly and needs a retry
        try:
            subprocess.check_call(["/bin/umount", *args, mountpoint])
            break
        except subprocess.CalledProcessError as err:
            attempt += 1
            if attempt > _UMOUNT_RETRIES:
                raise err

            time.sleep(1)
            logger.debug(
                "retry umount %r (%d/%d)", mountpoint, attempt, _UMOUNT_RETRIES
            )


_ID_TO_UBUNTU_CODENAME = {
    "17.10": "artful",
    "17.04": "zesty",
    "16.04": "xenial",
    "14.04": "trusty",
}


# TODO: consolidate os-release strategy with craft-providers/charmcraft


class OsRelease:
    """A class to intelligently determine the OS on which we're running."""

    def __init__(self, *, os_release_file: str = "/etc/os-release") -> None:
        """Create a new OsRelease instance.

        :param os_release_file: Path to os-release file to be parsed.
        """
        self._os_release: Dict[str, str] = {}
        with contextlib.suppress(FileNotFoundError):
            with open(os_release_file) as file:
                for line in file:
                    entry = line.rstrip().split("=")
                    if len(entry) == 2:
                        self._os_release[entry[0]] = entry[1].strip('"')

    def id(self) -> str:
        """Return the OS ID.

        :raises OsReleaseIdError: If no ID can be determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["ID"]

        raise errors.OsReleaseIdError()

    def name(self) -> str:
        """Return the OS name.

        :raises OsReleaseNameError: If no name can be determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["NAME"]

        raise errors.OsReleaseNameError()

    def version_id(self) -> str:
        """Return the OS version ID.

        :raises OsReleaseVersionIdError: If no version ID can be determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["VERSION_ID"]

        raise errors.OsReleaseVersionIdError()

    def version_codename(self) -> str:
        """Return the OS version codename.

        This first tries to use the VERSION_CODENAME. If that's missing, it
        tries to use the VERSION_ID to figure out the codename on its own.

        :raises OsReleaseCodenameError: If no version codename can be
            determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["VERSION_CODENAME"]

        with contextlib.suppress(KeyError):
            return _ID_TO_UBUNTU_CODENAME[self._os_release["VERSION_ID"]]

        raise errors.OsReleaseCodenameError()


def process_run(command: List[str], log_func: Callable[[str], None], **kwargs) -> None:
    """Run a command and handle its output."""
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        **kwargs,
    ) as proc:
        if not proc.stdout:
            return
        for line in iter(proc.stdout.readline, ""):
            log_func(":: " + line.strip())
        ret = proc.wait()

    if ret:
        raise subprocess.CalledProcessError(ret, command)
