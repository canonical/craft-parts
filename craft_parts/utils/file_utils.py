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
import itertools
import logging
import os
import pathlib
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
        os.close(self._fd)


def link_or_copy(
    source: Path,
    destination: Path,
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
        if permissions or (not follow_symlinks and source.is_symlink()):
            copy(source, destination)
        else:
            link(source, destination, follow_symlinks=follow_symlinks)
    except OSError as err:
        if err.errno == errno.EEXIST and not destination.is_dir():
            # os.link will fail if the destination already exists, so let's
            # remove it and try again.
            destination.unlink()
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


def link(
    source: Path,
    destination: Path,
    *,
    follow_symlinks: bool = False,
) -> None:
    """Hard-link source and destination files.

    :param source: The source to which destination will be linked.
    :param destination: The destination to be linked to source.
    :param follow_symlinks: Whether or not symlinks should be followed.

    :raises CopyFileNotFound: If source doesn't exist.
    """
    # Note that follow_symlinks doesn't seem to work for os.link, so we'll
    # implement this logic ourselves using realpath.
    if follow_symlinks:
        source = source.resolve()

    if not destination.parent.exists():
        create_similar_directory(source.parent, destination.parent)

    # Setting follow_symlinks=False in case this bug is ever fixed
    # upstream-- we want this function to continue supporting NOT following
    # symlinks.
    try:
        os.link(source, destination, follow_symlinks=False)
    except FileNotFoundError as err:
        raise errors.CopyFileNotFound(str(source)) from err


def copy(
    source: Path | str,
    destination: Path | str,
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
    source = Path(source)
    destination = Path(destination)

    # If os.link raised an I/O error, it may have left a file behind. Skip on
    # OSError in case it doesn't exist or is a directory.
    with contextlib.suppress(OSError):
        destination.unlink()

    try:
        src_stat = os.stat(source, follow_symlinks=follow_symlinks)  # noqa: PTH116
    except FileNotFoundError as err:
        raise errors.CopyFileNotFound(str(source)) from err

    src_mode = src_stat.st_mode

    if stat.S_ISFIFO(src_mode):
        os.mkfifo(destination, stat.S_IMODE(src_mode))
        shutil.copystat(source, destination, follow_symlinks=follow_symlinks)
    elif stat.S_ISCHR(src_mode) or stat.S_ISBLK(src_mode):
        os.mknod(destination, src_mode, src_stat.st_rdev)
        shutil.copystat(source, destination, follow_symlinks=follow_symlinks)
    else:
        shutil.copy2(source, destination, follow_symlinks=follow_symlinks)

    uid = src_stat.st_uid
    gid = src_stat.st_gid

    try:
        os.chown(destination, uid, gid, follow_symlinks=follow_symlinks)
    except PermissionError as err:
        logger.debug("Unable to chown %s: %s", destination, err)

    if permissions:
        apply_permissions(destination, permissions)


def link_or_copy_tree(
    source_tree: Path,
    destination_tree: Path,
    ignore: Callable[[str, list[str]], list[str]] | None = None,
    copy_function: Callable[..., None] = link_or_copy,
    *,
    overwrite_metadata: bool = True,
) -> None:
    """Copy a source tree into a destination, hard-linking if possible.

    :param source_tree: Source directory to be copied.
    :param destination_tree: Destination directory. If this directory
        already exists, the files in `source_tree` will take precedence.
    :param ignore: If given, called with two params, source dir and dir contents,
        for every dir copied. Should return list of contents to NOT copy.
    :param copy_function: Callable that actually copies.
    :param overwrite_metadata: Whether to overwrite metadata (mode, ownership)
        of existing destination directories.
    """
    if not source_tree.is_dir():
        raise errors.CopyTreeError(f"{source_tree.as_posix()!r} is not a directory")

    if not destination_tree.is_dir() and (
        destination_tree.exists() or destination_tree.is_symlink()
    ):
        raise errors.CopyTreeError(
            f"cannot overwrite non-directory {destination_tree.as_posix()!r} with "
            f"directory {source_tree.as_posix()!r}"
        )

    create_similar_directory(
        source_tree, destination_tree, overwrite_metadata=overwrite_metadata
    )

    destination_basename = destination_tree.name

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
            source = Path(root, directory)
            # os.walk doesn't by default follow symlinks (which is good), but
            # it includes symlinks that are pointing to directories in the
            # directories list. We want to treat it as a file, here.
            if source.is_symlink():
                files.append(directory)
                continue

            destination = Path(destination_tree, source.relative_to(source_tree))

            create_similar_directory(
                source, destination, overwrite_metadata=overwrite_metadata
            )

        for file_name in set(files) - ignored:
            source = Path(root, file_name)
            destination = Path(destination_tree, source.relative_to(source_tree))

            copy_function(source, destination)


def move(source: Path, destination: Path) -> None:
    """Move regular files, directories, or special files from source to destination.

    :param source: Directory from which to move the file or directory.
    :param destination: Directory where the file or directory will be moved to.
    """
    src_stat = source.stat(follow_symlinks=False)
    src_mode = src_stat.st_mode

    if stat.S_ISCHR(src_mode) or stat.S_ISBLK(src_mode):
        os.mknod(destination, src_mode, src_stat.st_rdev)
        shutil.copystat(source, destination)
        os.chown(destination, src_stat.st_uid, src_stat.st_gid)
        source.unlink()
        return

    shutil.move(source, destination)


def create_similar_directory(
    source: Path,
    destination: Path,
    permissions: list[Permissions] | None = None,
    *,
    overwrite_metadata: bool = True,
) -> None:
    """Create a directory with the same permission bits and owner information.

    :param source: Directory from which to copy name, permission bits, and
         owner information.
    :param destination: Directory to create and to which the ``source``
         information will be copied.
    :param permissions: The permission definitions to apply to the new directory.
        If omitted, the new directory will have the same permissions and ownership
        of ``source``.
    :param overwrite_metadata: Whether to overwrite metadata (mode, ownership)
        of existing destination directories.
    """
    exists = destination.exists()
    destination.mkdir(parents=True, exist_ok=True)

    if exists and not overwrite_metadata:
        return

    stat = source.stat(follow_symlinks=False)
    uid = stat.st_uid
    gid = stat.st_gid

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


def _get_file_type_str(result: os.stat_result) -> str:
    """Get the type of a file pointed to by path, as a string."""
    if stat.S_ISDIR(result.st_mode):
        file_type = "dir"
    elif stat.S_ISLNK(result.st_mode):
        file_type = "symlink"
    elif stat.S_ISFIFO(result.st_mode):
        file_type = "fifo"
    elif stat.S_ISBLK(result.st_mode):
        file_type = "blk"
    elif stat.S_ISCHR(result.st_mode):
        file_type = "chr"
    elif stat.S_ISSOCK(result.st_mode):
        file_type = "socket"
    elif stat.S_ISREG(result.st_mode):
        file_type = "file"
    elif hasattr(stat, "S_ISWHT") and stat.S_ISWHT(result.st_mode):
        file_type = "whiteout"
    else:
        file_type = "unknown"
    return file_type


def get_path_differences(  # noqa: PLR0912
    a: Path, b: Path
) -> list[str]:
    """Get a list of differences between two paths.

    This is a more forgiving test than ``Path.samefile()``, checking whether the
    files referenced by these two paths are equivalent for the purpose of organizing.
    If either file does not exist, they are considered to be equivalent.

    To be equivalent, they must:
    - Be of the same type (or one must be a symlink to the other).
    - Have the same owner and group
    - Have the same mode.

    For regular files, they must also:
    - Have the same size
    - Have the same contents

    :returns: A list of differences. An empty list means the paths are equivalent.
    """
    try:
        if a.samefile(b):
            return []
    except FileNotFoundError:
        # Broken symlinks will get a FileNotFoundError, but for our use case a broken
        # symlink is considered to be an extant file. For example, a broken symlink
        # could point to /snap/<project>/current/usr/bin/true
        if not a.is_symlink() and not b.is_symlink():
            return []

    a_stat = a.stat(follow_symlinks=False)
    b_stat = b.stat(follow_symlinks=False)

    # Mode is in the lower 12 bits, type is in the upper 4 bits.
    a_mode = a_stat.st_mode & 0o7777
    b_mode = b_stat.st_mode & 0o7777
    a_type = _get_file_type_str(a_stat)
    b_type = _get_file_type_str(b_stat)

    differences: list[str] = []

    if a_type != b_type:
        differences.append(f"different types ({a_type}, {b_type})")

    if a_stat.st_uid != b_stat.st_uid:
        differences.append(f"different uids ({a_stat.st_uid}, {b_stat.st_uid})")

    if a_stat.st_gid != b_stat.st_gid:
        differences.append(f"different gids ({a_stat.st_gid}, {b_stat.st_gid})")

    if differences:
        return differences

    if stat.S_ISLNK(a_stat.st_mode) and stat.S_ISLNK(b_stat.st_mode):
        a_target = a.readlink()
        b_target = b.readlink()
        if a_target != b_target:
            differences.append(f"different symlink targets ({a_target}, {b_target})")

    if a_mode != b_mode:
        differences.append(f"different modes ({a_mode:o}, {b_mode:o})")

    if (
        a.is_file()
        and b.is_file()
        and not (stat.S_ISLNK(a_stat.st_mode) or stat.S_ISLNK(b_stat.st_mode))
    ):
        if a_stat.st_size != b_stat.st_size:
            differences.append(f"different sizes ({a_stat.st_size}, {b_stat.st_size})")
        elif stat.S_ISREG(a_stat.st_mode) and stat.S_ISREG(b_stat.st_mode):
            with a.open("rb") as a_f, b.open("rb") as b_f:
                while True:
                    a_read = a_f.read(2**24)  # 16 MiB
                    b_read = b_f.read(2**24)  # 16 MiB
                    if not a_read and not b_read:
                        break
                    if a_read != b_read:
                        differences.append("different contents")
                        break

    return differences


def find_merge_conflicts(
    src_root: Path, dst_root: Path, *, strict: bool = False
) -> dict[pathlib.Path, list[str]]:
    """Check that the given directories can be merged.

    Checks that the two directories provided can be merged without overwriting files.

    :param strict: if True, errors if overwriting a file, even if it's identical.
    """
    conflicts: dict[pathlib.Path, list[str]] = {}
    for source_path in itertools.chain(src_root.rglob("*"), (src_root,)):
        relative_path = source_path.relative_to(src_root)
        dest_path = dst_root / relative_path
        # exists() follows symlinks and returns False for broken symlinks, so
        # we also check is_symlink() to ensure broken-link destinations are not
        # silently skipped as if they were absent.
        if not dest_path.exists() and not dest_path.is_symlink():
            continue
        try:
            if dest_path.samefile(source_path):
                continue
        except FileNotFoundError:
            # samefile() follows symlinks and raises if either path is a broken
            # symlink. Fall through so get_path_differences() can compare them.
            pass

        if strict and dest_path.is_file():
            conflicts.setdefault(relative_path, []).append("exists")
        else:
            msg = get_path_differences(source_path, dest_path)
            if msg:
                conflicts.setdefault(relative_path, []).extend(msg)

    return conflicts
