# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021,2024 Canonical Ltd.
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

"""Helpers to detect conflicting staging files from multiple parts."""

import filecmp
import os
from typing import Any, Dict, List, Optional

from craft_parts import errors, permissions
from craft_parts.executor import filesets
from craft_parts.executor.filesets import Fileset
from craft_parts.features import Features
from craft_parts.parts import Part
from craft_parts.permissions import Permissions, permissions_are_compatible


def check_for_stage_collisions(
    part_list: List[Part], partitions: Optional[List[str]]
) -> None:
    """Verify whether parts have conflicting files to stage.

    If the partitions feature is enabled, then check if parts have conflicting files to
        stage for each partition.
    If the partitions feature is disabled, only check for conflicts in the default
        stage directory.

    :param part_list: The list of parts to check.
    :param partitions: An optional list of partition names.

    :raises PartConflictError: If conflicts are found.
    :raises FeatureError: If partitions are specified but the feature is not enabled or
        if partitions are not specified and the feature is enabled.
    """
    if partitions and not Features().enable_partitions:
        raise errors.FeatureError(
            "Partitions specified but partitions feature is not enabled."
        )

    if partitions is None and Features().enable_partitions:
        raise errors.FeatureError(
            "Partitions feature is enabled but no partitions specified."
        )

    for partition in partitions or [None]:  # type: ignore[list-item]
        _check_for_stage_collisions_per_partition(part_list, partition)


def _check_for_stage_collisions_per_partition(
    part_list: List[Part], partition: Optional[str]
) -> None:
    """Verify whether parts have conflicting files for a stage directory in a partition.

    If no partition is provided, then the default stage directory is checked.

    :param part_list: The list of parts to check.
    :param partition: If the partitions feature is enabled, then the name of the
        partition containing the stage directory to check.

    :raises PartConflictError: If conflicts are found.
    """
    all_parts_files: Dict[str, Dict[str, Any]] = {}
    for part in part_list:
        stage_files = part.spec.stage_files
        if not stage_files:
            continue

        # Gather our own files up.
        stage_fileset = Fileset(stage_files, name="stage")
        srcdir = str(part.part_install_dirs[partition])
        part_files, part_directories = filesets.migratable_filesets(
            stage_fileset, srcdir, partition
        )
        part_contents = part_files | part_directories

        # Scan previous parts for collisions.
        for other_part_name, other_part_files in all_parts_files.items():
            # Our files that are also in a different part.
            common = part_contents & other_part_files["files"]

            conflict_files = []
            for file in common:
                this = os.path.join(part.part_install_dirs[partition], file)
                other = os.path.join(other_part_files["installdir"], file)

                permissions_this = permissions.filter_permissions(
                    file, part.spec.permissions
                )

                permissions_other = permissions.filter_permissions(
                    file, other_part_files["part"].spec.permissions
                )

                if paths_collide(this, other, permissions_this, permissions_other):
                    conflict_files.append(file)

            if conflict_files:
                raise errors.PartFilesConflict(
                    part_name=part.name,
                    other_part_name=other_part_name,
                    conflicting_files=conflict_files,
                    partition=partition,
                )

        # And add our files to the list.
        all_parts_files[part.name] = {
            "files": part_contents,
            "installdir": part.part_install_dirs[partition],
            "part": part,
        }


def paths_collide(
    path1: str,
    path2: str,
    permissions_path1: Optional[List[Permissions]] = None,
    permissions_path2: Optional[List[Permissions]] = None,
) -> bool:
    """Check whether the provided paths conflict to each other.

    If both paths have Permissions definitions, they are considered to be conflicting
    if the permissions are incompatible (as defined by
    ``permissions.permissions_are_compatible()``).

    :param permissions_path1: The list of ``Permissions`` that affect ``path1``.
    :param permissions_path2: The list of ``Permissions`` that affect ``path2``.

    """
    if not (os.path.lexists(path1) and os.path.lexists(path2)):
        return False

    path1_is_dir = os.path.isdir(path1)
    path2_is_dir = os.path.isdir(path2)
    path1_is_link = os.path.islink(path1)
    path2_is_link = os.path.islink(path2)

    # Paths collide if they're both symlinks, but pointing to different places.
    if path1_is_link and path2_is_link:
        return os.readlink(path1) != os.readlink(path2)

    # Paths collide if one is a symlink, but not the other.
    if path1_is_link or path2_is_link:
        return True

    # Paths collide if one is a directory, but not the other.
    if path1_is_dir != path2_is_dir:
        return True

    # Paths collide if neither path is a directory, and the files have
    # different contents.
    if not (path1_is_dir and path2_is_dir) and _file_collides(path1, path2):
        return True

    # Otherwise, paths conflict if they have incompatible permissions.
    return not permissions_are_compatible(permissions_path1, permissions_path2)


def _file_collides(file_this: str, file_other: str) -> bool:
    if not file_this.endswith(".pc"):
        return not filecmp.cmp(file_this, file_other, shallow=False)

    # pkgconfig files need special handling, only prefix line may be different.
    with open(file_this) as pc_file_1, open(file_other) as pc_file_2:
        for line_pc_1, line_pc_2 in zip(pc_file_1, pc_file_2):
            if line_pc_1.startswith("prefix=") and line_pc_2.startswith("prefix="):
                continue
            if line_pc_1 != line_pc_2:
                return True

    return False
