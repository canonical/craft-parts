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

"""Handle the execution of built-in or user specified step commands."""

import logging
import os
from pathlib import Path
from typing import Dict, Set

from craft_parts.state_manager.states import StepState
from craft_parts.utils import file_utils

logger = logging.getLogger(__name__)


def migrate_files(
    *,
    files: Set[str],
    dirs: Set[str],
    srcdir: str,
    destdir: str,
    missing_ok: bool = False,
    follow_symlinks: bool = False,
    fixup_func=lambda *args: None,
) -> None:
    """Copy or link files from a directory to another.

    Files and directories are migrated from one step to the next during
    the lifecycle processing. Whenever possible, files are hard-linked
    instead of copied.

    :param files: The set of files to migrate.
    :param dirs: The set of directories to migrate.
    :param srcdir: The directory containing entries to migrate.
    :param destdir: The directory to migrate entries to.
    :param missing_ok: Ignore entries that don't exist.
    :param follow_symlinks: Migrate symlink targets.
    :param fixup_func: A function to run on each migrated file.
    """
    for dirname in sorted(dirs):
        src = os.path.join(srcdir, dirname)
        dst = os.path.join(destdir, dirname)

        file_utils.create_similar_directory(src, dst)

    for filename in sorted(files):
        src = os.path.join(srcdir, filename)
        dst = os.path.join(destdir, filename)

        if missing_ok and not os.path.exists(src):
            continue

        # If the file is already here and it's a symlink, leave it alone.
        if os.path.islink(dst):
            continue

        # Otherwise, remove and re-link it.
        if os.path.exists(dst):
            os.remove(dst)

        file_utils.link_or_copy(src, dst, follow_symlinks=follow_symlinks)

        fixup_func(dst)


def clean_shared_area(
    *, part_name: str, shared_dir: Path, part_states: Dict[str, StepState]
) -> None:
    """Clean files added by a part to a shared directory.

    :param part_name: The name of the part that added the files.
    :param shared_dir: The shared directory to remove files from.
    :param part_states: A dictionary containing the each part's state for the
        step being processed.
    """
    # no state defined for this part, we won't remove files
    if part_name not in part_states:
        return

    state = part_states[part_name]
    files = state.files
    directories = state.directories

    # We want to make sure we don't remove a file or directory that's
    # being used by another part. So we'll examine the state for all parts
    # in the project and leave any files or directories found to be in
    # common.
    for other_name, other_state in part_states.items():
        if other_state and other_name != part_name:
            files -= other_state.files
            directories -= other_state.directories

    # Finally, clean the files and directories that are specific to this
    # part.
    _clean_migrated_files(files, directories, shared_dir)


def _clean_migrated_files(files: Set[str], dirs: Set[str], directory: Path) -> None:
    """Remove files and directories migrated from part install to a common directory.

    :param files: A set of files to remove.
    :param dirs: A set of directories to remove.
    :param directory: The path to remove files and directories from.
    """
    for each_file in files:
        try:
            Path(directory, each_file).unlink()
        except FileNotFoundError:
            logger.warning(
                "Attempted to remove file %r, but it didn't exist. Skipping...",
                each_file,
            )

    # Directories may not be ordered so that subdirectories come before
    # parents, and we want to be able to remove directories if possible, so
    # we'll sort them in reverse here to get subdirectories before parents.

    for each_dir in sorted(dirs, reverse=True):
        migrated_directory = os.path.join(directory, each_dir)
        try:
            if not os.listdir(migrated_directory):
                os.rmdir(migrated_directory)
        except FileNotFoundError:
            logger.warning(
                "Attempted to remove directory '%s', but it didn't exist. "
                "Skipping...",
                each_dir,
            )
