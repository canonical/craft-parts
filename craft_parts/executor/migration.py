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
from typing import Dict, Optional, Set, Tuple

from craft_parts import overlays
from craft_parts.state_manager.states import MigrationState, StepState
from craft_parts.utils import file_utils

logger = logging.getLogger(__name__)


def migrate_files(
    *,
    files: Set[str],
    dirs: Set[str],
    srcdir: Path,
    destdir: Path,
    missing_ok: bool = False,
    follow_symlinks: bool = False,
    oci_translation: bool = False,
    fixup_func=lambda *args: None,
) -> Tuple[Set[str], Set[str]]:
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
    :param oci_translation: Convert to OCI whiteout files and opaque dirs.
    :param fixup_func: A function to run on each migrated file.

    :returns: A tuple containing sets of migrated files and directories.
    """
    migrated_files: Set[str] = set()
    migrated_dirs: Set[str] = set()

    for dirname in sorted(dirs):
        src = srcdir / dirname
        dst = destdir / dirname

        # If migrating a whited out directory from stage (OCI) using layer (overlayfs)
        # as reference, use the OCI whiteout file names.
        if not src.exists() and overlays.oci_whiteout(src).exists():
            src = overlays.oci_whiteout(src)
            dst = overlays.oci_whiteout(dst)

        file_utils.create_similar_directory(str(src), str(dst))
        migrated_dirs.add(dirname)

        # If source is an opaque dir (overlayfs or OCI), create an OCI opaque
        # directory marker file in destination and add it to the list of migrated
        # files so it can be removed when cleaning.
        if oci_translation and _is_opaque_dir(src):
            oci_opaque_marker = overlays.oci_opaque_dir(Path(dirname))
            oci_dst = Path(destdir, oci_opaque_marker)
            logger.debug("create OCI opaque dir marker '%s'", str(oci_dst))
            oci_dst.touch()
            migrated_files.add(str(oci_opaque_marker))

    for filename in sorted(files):
        src = srcdir / filename
        dst = destdir / filename

        if not src.exists():
            # If migrating a whited out file from stage (OCI) using layer (overlayfs)
            # as reference, use the OCI whiteout file names.
            if overlays.oci_whiteout(src).exists():
                src = overlays.oci_whiteout(src)
                dst = overlays.oci_whiteout(dst)
            elif missing_ok:
                continue

        # If the file is already here and it's a symlink, leave it alone.
        if dst.is_symlink():
            continue

        # Otherwise, remove and re-link it.
        if dst.exists():
            dst.unlink()

        # If source is a whiteout file (overlayfs or OCI), create an OCI whiteout file
        # in destination and add it to the list of migrated files so it can be removed
        # when cleaning.
        if oci_translation and _is_whiteout_file(src):
            oci_whiteout = overlays.oci_whiteout(Path(filename))
            oci_dst = Path(destdir, oci_whiteout)
            logger.debug("create OCI whiteout file '%s'", str(oci_dst))
            oci_dst.touch()
            migrated_files.add(str(oci_whiteout))
        else:
            file_utils.link_or_copy(str(src), str(dst), follow_symlinks=follow_symlinks)
            fixup_func(str(dst))
            migrated_files.add(str(filename))

    return migrated_files, migrated_dirs


def _is_whiteout_file(path: Path) -> bool:
    return overlays.is_whiteout_file(path) or overlays.is_oci_whiteout_file(path)


def _is_opaque_dir(path: Path) -> bool:
    return overlays.is_opaque_dir(path) or overlays.is_oci_opaque_dir(path)


def clean_shared_area(
    *,
    part_name: str,
    shared_dir: Path,
    part_states: Dict[str, StepState],
    overlay_migration_state: Optional[MigrationState],
) -> None:
    """Clean files added by a part to a shared directory.

    :param part_name: The name of the part that added the files.
    :param shared_dir: The shared directory to remove files from.
    :param part_states: A dictionary mapping each part to the part's state for
        the step corresponding to the area being cleaned.
    :param overlay_migration_state: The state of the overlay migration to step.
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

    # If overlay has been migrated, also take overlay files into account
    if overlay_migration_state:
        files -= overlay_migration_state.files
        directories -= overlay_migration_state.directories

    # Finally, clean the files and directories that are specific to this
    # part.
    _clean_migrated_files(files, directories, shared_dir)


def clean_shared_overlay(
    *,
    shared_dir: Path,
    part_states: Dict[str, StepState],
    overlay_migration_state: Optional[MigrationState],
) -> None:
    """Remove migrated overlay files from a shared directory.

    :param state_file: The migration state file.
    :param shared_dir: The shared directory to remove files from.
    :param part_states: A dictionary mapping each part to the part's state for
        the step corresponding to the area being cleaned.
    """
    # no overlay staging state defined, we won't remove files
    if not overlay_migration_state:
        return

    files = overlay_migration_state.files
    directories = overlay_migration_state.directories

    # Don't remove entries that also belong to a part.
    for other_state in part_states.values():
        if other_state:
            files -= other_state.files
            directories -= other_state.directories

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


def filter_dangling_whiteouts(
    files: Set[str], dirs: Set[str], *, base_dir: Optional[Path]
) -> Set[str]:
    """Remove dangling whiteout file and directory names.

    Names corresponding to dangling files and directories (i.e. without a
    backing file in the base layer to be whited out) are to be removed from
    the provided sets of files and directory names.

    :param files: The set of files to be verified.
    :param dirs: The set of directories to be verified.
    :return: The set of filtered out whiteout files.
    """
    # Whiteouts are meaningless if no base dir is specified, ignore them
    if not base_dir:
        return set()

    whiteouts: Set[str] = set()

    # Remove whiteout files if no backing file exists in the base dir.
    for file in list(files):
        if overlays.is_oci_whiteout_file(Path(file)):
            backing_file = base_dir / overlays.oci_whited_out_file(Path(file))
            if not backing_file.exists():
                logger.debug("filter whiteout file '%s'", file)
                files.remove(file)
                whiteouts.add(file)

    # Do the same for opaque directory markers
    for directory in list(dirs):
        opaque_marker = str(overlays.oci_opaque_dir(Path(directory)))
        if opaque_marker in files:
            backing_file = base_dir / directory
            if not backing_file.exists():
                logger.debug("filter whiteout file '%s'", opaque_marker)
                files.remove(opaque_marker)
                whiteouts.add(opaque_marker)

    return whiteouts
