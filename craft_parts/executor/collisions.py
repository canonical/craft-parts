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

"""Helpers to detect conflicting staging files from multiple parts."""

import filecmp
import os
from typing import Any, Dict, List

from craft_parts import errors
from craft_parts.executor import filesets
from craft_parts.executor.filesets import Fileset
from craft_parts.parts import Part


def check_for_stage_collisions(part_list: List[Part]) -> None:
    """Verify whether parts have conflicting files to stage.

    :param part_list: The list of parts to be tested.
    :raises PartConflictError: If conflicts are found.
    """
    all_parts_files: Dict[str, Dict[str, Any]] = {}
    for part in part_list:
        stage_files = part.spec.stage_files
        if not stage_files:
            continue

        # Gather our own files up.
        stage_fileset = Fileset(stage_files, name="stage")
        srcdir = str(part.part_install_dir)
        part_files, part_directories = filesets.migratable_filesets(
            stage_fileset, srcdir
        )
        part_contents = part_files | part_directories

        # Scan previous parts for collisions.
        for other_part_name, other_part_files in all_parts_files.items():
            # Our files that are also in a different part.
            common = part_contents & other_part_files["files"]

            conflict_files = []
            for file in common:
                this = os.path.join(part.part_install_dir, file)
                other = os.path.join(other_part_files["installdir"], file)

                if paths_collide(this, other):
                    conflict_files.append(file)

            if conflict_files:
                raise errors.PartFilesConflict(
                    part_name=part.name,
                    other_part_name=other_part_name,
                    conflicting_files=conflict_files,
                )

        # And add our files to the list.
        all_parts_files[part.name] = {
            "files": part_contents,
            "installdir": part.part_install_dir,
        }


def paths_collide(path1: str, path2: str) -> bool:
    """Check whether the provided paths conflict to each other."""
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

    # Otherwise, paths do not conflict.
    return False


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
