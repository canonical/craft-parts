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

"""Overlay handling helpers.

Relevant OCI documentation available at:
https://github.com/opencontainers/image-spec/blob/main/layer.md
"""

import logging
import os
from pathlib import Path
from typing import Set, Tuple

logger = logging.getLogger(__name__)


def visible_in_layer(srcdir: Path, destdir: Path) -> Tuple[Set[str], Set[str]]:
    """Determine the files and directories that are visible in a layer.

    Given a source and destination directories, list the files and directories that
    would be visible in an overlay stack if the destination directory is the upper
    layer and the source directory is the lower layer.

    :param srcdir: The source directory.
    :param destdir: The destination directory.

    :returns: A tuple containing the sets of files and directories that are visible.
    """
    visible_files: Set[str] = set()
    visible_dirs: Set[str] = set()

    logger.debug("check layer visibility in %s", srcdir)
    for (root, directories, files) in os.walk(srcdir, topdown=True):
        for file_name in files:
            path = Path(root, file_name)
            relpath = path.relative_to(srcdir)
            if not _is_path_visible(destdir, relpath):
                continue

            destpath = destdir / relpath
            if not destpath.exists() and not oci_whiteout(destpath).exists():
                visible_files.add(str(relpath))

        for directory in directories:
            path = Path(root, directory)
            relpath = path.relative_to(srcdir)
            if not _is_path_visible(destdir, relpath):
                continue

            destpath = destdir / relpath
            if not destpath.exists():
                if path.is_symlink():
                    visible_files.add(str(relpath))
                else:
                    visible_dirs.add(str(relpath))
            elif is_oci_opaque_dir(destpath):
                logger.debug("is opaque dir: %s", relpath)
                # Don't descend into this directory, overridden by opaque
                directories.remove(directory)

    logger.debug("files=%r, dirs=%r", visible_files, visible_dirs)
    return visible_files, visible_dirs


def _is_path_visible(root: Path, relpath: Path) -> bool:
    """Verify if any element of the given path is not whited out.

    :param root: The root directory, not included in the verification.
    :param relpath: The relative path to verify.

    :returns: Whether the final element of the path is visible.
    """
    logger.debug("check if path is visible: root=%s, relpath=%s", root, relpath)
    levels = len(relpath.parts)

    for level in range(levels):
        path = Path(root, os.path.join(*relpath.parts[: level + 1]))
        if oci_whiteout(path).exists() or is_oci_opaque_dir(path):
            logger.debug("is whiteout or opaque: %s", path)
            return False

    return True


def is_oci_opaque_dir(path: Path) -> bool:
    """Verify if the given path corresponds to an opaque directory.

    :param path: The path of the file to verify.

    :returns: Whether the given path is an overlayfs opaque directory.
    """
    if not path.is_dir() or path.is_symlink():
        return False

    return oci_opaque_dir(path).exists()


def oci_whiteout(path: Path) -> Path:
    """Convert the given path to an OCI whiteout file name.

    :param path: The file path to white out.

    :returns: The corresponding OCI whiteout file name.
    """
    return path.parent / (".wh." + path.name)


def oci_opaque_dir(path: Path) -> Path:
    """Return the OCI opaque directory marker.

    :param path: The directory to mark as opaque.

    :returns: The corresponding OCI opaque directory marker path.
    """
    return path / ".wh..wh..opq"
