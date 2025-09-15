# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""File-related utilities."""

import contextlib
import errno
import hashlib
import logging
import os
import shutil
import stat
import sys
from collections.abc import Callable, Generator
from pathlib import Path

from craft_parts import errors
from craft_parts.permissions import Permissions, apply_permissions

logger = logging.getLogger(__name__)


class NonBlockingRWFifo:
    """A non-blocking FIFO for reading and writing."""

    def __init__(self, path: str) -> None:
        os.mkfifo(path)
        self._path = path

        # Using RDWR for every FIFO just so we can open them reliably whenever
        # (i.e. write-only FIFOs can't be opened successfully until the reader
        # is in place)
        self._fd = os.open(self._path, os.O_RDWR | os.O_NONBLOCK)

    @property
    def path(self) -> str:
        """Return the path to the FIFO file."""
        return self._path

    def read(self) -> str:
        """Read from the FIFO."""
        total_read = ""
        with contextlib.suppress(BlockingIOError):
            value = os.read(self._fd, 1024)
            while value:
                total_read += value.decode(sys.getfilesystemencoding())
                value = os.read(self._fd, 1024)
        return total_read

    def write(self, data: str) -> int:
        """Write to the FIFO.

        :param data: The data to write.
        """
        return os.write(self._fd, data.encode(sys.getfilesystemencoding()))

    def close(self) -> None:
        """Close the FIFO."""
        if self._fd is not None:
            os.close(self._fd)


def link_or_copy(
    source: str,
    destination: str,
    *,
    follow_symlinks: bool = False,
    permissions: list[Permissions] | None = None,
) -> None:
    """Hard-link source and destination files. Copy if it fails to link.

    Hard-linking may fail (e.g. a cross-device link, or permission denied), so
    as a backup plan we just copy it. Note that we always copy the file if its
    ``permissions`` will change.

    :param source: The source to which destination will be linked.
    :param destination: The destination to be linked to source.
    :param follow_symlinks: Whether or not symlinks should be followed.
    :param permissions: The permissions definitions that should be applied to the
        new file.
    """
    try:
        if permissions or (not follow_symlinks and os.path.islink(source)):  # noqa: PTH114
            copy(source, destination)
        else:
            link(source, destination, follow_symlinks=follow_symlinks)
    except OSError as err:
        if err.errno == errno.EEXIST and not os.path.isdir(destination):  # noqa: PTH112
            # os.link will fail if the destination already exists, so let's
            # remove it and try again.
            os.remove(destination)  # noqa: PTH107
            link_or_copy(
                source,
                destination,
                follow_symlinks=follow_symlinks,
                permissions=permissions,
            )
        else:
            copy(source, destination, follow_symlinks=follow_symlinks)

    if permissions:
        apply_permissions(destination, permissions)


def link(source: str, destination: str, *, follow_symlinks: bool = False) -> None:
    """Hard-link source and destination files.

    :param source: The source to which destination will be linked.
    :param destination: The destination to be linked to source.
    :param follow_symlinks: Whether or not symlinks should be followed.

    :raises CopyFileNotFound: If source doesn't exist.
    """
    # Note that follow_symlinks doesn't seem to work for os.link, so we'll
    # implement this logic ourselves using realpath.
    source_path = source
    if follow_symlinks:
        source_path = os.path.realpath(source)

    if not os.path.exists(os.path.dirname(destination)):  # noqa: PTH110, PTH120
        create_similar_directory(
            os.path.dirname(source_path),  # noqa: PTH120
            os.path.dirname(destination),  # noqa: PTH120
        )

    # Setting follow_symlinks=False in case this bug is ever fixed
    # upstream-- we want this function to continue supporting NOT following
    # symlinks.
    try:
        os.link(source_path, destination, follow_symlinks=False)
    except FileNotFoundError as err:
        raise errors.CopyFileNotFound(source) from err


def copy(
    source: str,
    destination: str,
    *,
    follow_symlinks: bool = False,
    permissions: list[Permissions] | None = None,
) -> None:
    """Copy source and destination files.

    This function overwrites the destination if it already exists, and also
    tries to copy ownership information.

    :param source: The source to be copied to destination.
    :param destination: Where to put the copy.
    :param follow_symlinks: Whether or not symlinks should be followed.
    :param permissions: The permissions definitions that should be applied to the
        new file.

    :raises CopyFileNotFound: If source doesn't exist.
    """
    # If os.link raised an I/O error, it may have left a file behind. Skip on
    # OSError in case it doesn't exist or is a directory.
    with contextlib.suppress(OSError):
        os.unlink(destination)  # noqa: PTH108

    try:
        shutil.copy2(source, destination, follow_symlinks=follow_symlinks)
    except FileNotFoundError as err:
        raise errors.CopyFileNotFound(source) from err

    uid = os.stat(source, follow_symlinks=follow_symlinks).st_uid  # noqa: PTH116
    gid = os.stat(source, follow_symlinks=follow_symlinks).st_gid  # noqa: PTH116

    try:
        os.chown(destination, uid, gid, follow_symlinks=follow_symlinks)
    except PermissionError as err:
        logger.debug("Unable to chown %s: %s", destination, err)

    if permissions:
        apply_permissions(destination, permissions)


def link_or_copy_tree(
    source_tree: str,
    destination_tree: str,
    ignore: Callable[[str, list[str]], list[str]] | None = None,
    copy_function: Callable[..., None] = link_or_copy,
) -> None:
    """Copy a source tree into a destination, hard-linking if possible.

    :param source_tree: Source directory to be copied.
    :param destination_tree: Destination directory. If this directory
        already exists, the files in `source_tree` will take precedence.
    :param ignore: If given, called with two params, source dir and dir contents,
        for every dir copied. Should return list of contents to NOT copy.
    :param copy_function: Callable that actually copies.
    """
    if not os.path.isdir(source_tree):  # noqa: PTH112
        raise errors.CopyTreeError(f"{source_tree!r} is not a directory")

    if not os.path.isdir(destination_tree) and (  # noqa: PTH112
        os.path.exists(destination_tree) or os.path.islink(destination_tree)  # noqa: PTH110, PTH114
    ):
        raise errors.CopyTreeError(
            f"cannot overwrite non-directory {destination_tree!r} with "
            f"directory {source_tree!r}"
        )

    create_similar_directory(source_tree, destination_tree)

    destination_basename = os.path.basename(destination_tree)  # noqa: PTH119

    for root, directories, files in os.walk(source_tree, topdown=True):
        ignored: set[str] = set()
        if ignore is not None:
            ignored = set(ignore(root, directories + files))

        # Don't recurse into destination tree if it's a subdirectory of the
        # source tree.
        if os.path.relpath(destination_tree, root) == destination_basename:
            ignored.add(destination_basename)

        if ignored:
            # Prune our search appropriately given an ignore list, i.e. don't
            # walk into directories that are ignored.
            directories[:] = [d for d in directories if d not in ignored]

        for directory in directories:
            source = os.path.join(root, directory)  # noqa: PTH118
            # os.walk doesn't by default follow symlinks (which is good), but
            # it includes symlinks that are pointing to directories in the
            # directories list. We want to treat it as a file, here.
            if os.path.islink(source):  # noqa: PTH114
                files.append(directory)
                continue

            destination = os.path.join(  # noqa: PTH118
                destination_tree, os.path.relpath(source, source_tree)
            )

            create_similar_directory(source, destination)

        for file_name in set(files) - ignored:
            source = os.path.join(root, file_name)  # noqa: PTH118
            destination = os.path.join(  # noqa: PTH118
                destination_tree, os.path.relpath(source, source_tree)
            )

            copy_function(source, destination)


def move(source: str, destination: str) -> None:
    """Move regular files, directories, or special files from source to destination.

    :param source: Directory from which to move the file or directory.
    :param destination: Directory where the file or directory will be moved to.
    """
    src_path = Path(source)
    dest_path = Path(destination)

    src_stat = src_path.stat(follow_symlinks=False)
    src_mode = src_stat.st_mode

    if stat.S_ISCHR(src_mode) or stat.S_ISBLK(src_mode):
        os.mknod(dest_path, src_mode, src_stat.st_rdev)
        shutil.copystat(src_path, dest_path)
        os.chown(dest_path, src_stat.st_uid, src_stat.st_gid)
        src_path.unlink()
        return

    shutil.move(src_path, dest_path)


def create_similar_directory(
    source: str, destination: str, permissions: list[Permissions] | None = None
) -> None:
    """Create a directory with the same permission bits and owner information.

    :param source: Directory from which to copy name, permission bits, and
         owner information.
    :param destination: Directory to create and to which the ``source``
         information will be copied.
    :param permissions: The permission definitions to apply to the new directory.
        If omitted, the new directory will have the same permissions and ownership
        of ``source``.
    """
    stat = os.stat(source, follow_symlinks=False)  # noqa: PTH116
    uid = stat.st_uid
    gid = stat.st_gid
    os.makedirs(destination, exist_ok=True)  # noqa: PTH103

    # Windows does not have "os.chown" implementation and copystat
    # is unlikely to be useful, so just bail after creating directory.
    if sys.platform == "win32":
        return

    try:
        os.chown(destination, uid, gid, follow_symlinks=False)
    except PermissionError as exception:
        logger.debug("Unable to chown %s: %s", destination, exception)

    shutil.copystat(source, destination, follow_symlinks=False)

    if permissions:
        apply_permissions(destination, permissions)


def calculate_hash(filename: Path, *, algorithm: str) -> str:
    """Calculate the hash of the given file.

    :param filename: The path to the file to digest.
    :param algorithm: The algorithm to use, as defined by ``hashlib``.

    :return: The file hash.

    :raise ValueError: If the algorithm is unsupported.
    """
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"unsupported algorithm {algorithm!r}")

    hasher = hashlib.new(algorithm)

    for block in _file_reader_iter(filename):
        hasher.update(block)
    return hasher.hexdigest()


def _file_reader_iter(
    path: Path, block_size: int = 2**20
) -> Generator[bytes, None, None]:
    """Read a file in blocks.

    :param path: The path to the file to read.
    :param block_size: The size of the block to read, default is 1MiB.
    """
    with path.open("rb") as file:
        block = file.read(block_size)
        while len(block) > 0:
            yield block
            block = file.read(block_size)
