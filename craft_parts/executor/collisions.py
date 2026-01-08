# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2025 Canonical Ltd.
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
from dataclasses import dataclass
from pathlib import Path

from craft_parts import errors, overlays, permissions
from craft_parts.features import Features
from craft_parts.overlays import overlay_fs
from craft_parts.parts import Part
from craft_parts.permissions import Permissions, permissions_are_compatible

from . import filesets


def check_for_stage_collisions(
    part_list: list[Part], partitions: list[str] | None
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


@dataclass
class StageCandidate:
    """Representation of a set of files and directories that want to be staged."""

    # Name of the part that produced these files and directories
    part_name: str
    # The actual files and directories, relative to ``source_dir``
    contents: set[str]
    # The directory that contains ``contents``
    source_dir: Path
    # The permissions that apply to ``contents``
    permissions: list[Permissions]
    # Whether this set comes from a part's overlay (used for error reporting)
    is_overlay: bool


def _get_candidate_from_install_dir(
    part: Part, partition: str | None
) -> StageCandidate | None:
    """Create a StageCandidate from a part's install dir contents."""
    stage_files = part.spec.stage_files
    if not stage_files:
        return None

    stage_fileset = filesets.Fileset(stage_files, name="stage")
    srcdir = str(part.part_install_dirs[partition])
    part_files, part_directories = filesets.migratable_filesets(
        stage_fileset,
        srcdir,
        part.default_partition,
        partition,
    )
    part_contents = part_files | part_directories

    return StageCandidate(
        part_name=part.name,
        contents=part_contents,
        source_dir=part.part_install_dirs[partition],
        permissions=part.spec.permissions,
        is_overlay=False,
    )


def _get_overlay_layer_contents(source: Path) -> tuple[set[str], set[str]]:
    """Get the files and directories from a directory, relative to that directory."""
    concrete_files: set[Path] = set()
    concrete_dirs: set[Path] = set()
    for root, directories, files in os.walk(source, topdown=True):
        for file_name in files:
            path = Path(root, file_name)
            # A whiteout file means that the file is to be removed from the stack, and
            # so won't conflict with incoming files from install dirs.
            if not overlay_fs.is_whiteout_file(path):
                concrete_files.add(path)

        for directory in directories:
            path = Path(root, directory)
            if path.is_symlink():
                concrete_files.add(path)
            else:
                concrete_dirs.add(path)

    return (
        {str(f.relative_to(source)) for f in concrete_files},
        {str(d.relative_to(source)) for d in concrete_dirs},
    )


def _get_candidates_from_overlay(
    part_list: list[Part], partition: str | None
) -> list[StageCandidate]:
    """Get candidate contents coming from the overlay.

    If overlays are not enabled, this function returns an empty list; otherwise, the
    function computes the contents that each overlay-enabled part in ``part_list`` wants
    to stage from the overlay, taking into account the overlay visibility.
    """
    if not Features().enable_overlay:
        return []

    candidates: list[StageCandidate] = []
    parts_with_overlay = [p for p in part_list if p.has_overlay]
    for i, part in enumerate(parts_with_overlay):
        part_layer_dir = part.part_layer_dirs[partition]

        # Start with all files and directories from that part's layer...
        files, dirs = _get_overlay_layer_contents(part_layer_dir)

        # ... and progressively remove the items that are hidden by "higher" layers.
        for upper_part in parts_with_overlay[i + 1 :]:
            upper_layer_dir = upper_part.part_layer_dirs[partition]
            visible_files, visible_dirs = overlays.visible_in_layer(
                part_layer_dir,
                upper_layer_dir,
            )
            files &= visible_files
            dirs &= visible_dirs

        candidates.append(
            StageCandidate(
                part_name=part.name,
                contents=files | dirs,
                permissions=[],
                source_dir=part_layer_dir,
                is_overlay=True,
            )
        )

    return candidates


def _check_for_stage_collisions_per_partition(
    part_list: list[Part],
    partition: str | None,
) -> None:
    """Verify whether parts have conflicting files for a stage directory in a partition.

    If no partition is provided, then the default stage directory is checked.

    :param part_list: The list of parts to check.
    :param partition: If the partitions feature is enabled, then the name of the
        partition containing the stage directory to check.

    :raises PartConflictError: If conflicts between build content are found.
    :raises OverlayStageConflict: If conflicts between build and overlay content are
      found.
    """
    # Start by describing the candidates from the overlay, since by definition they
    # don't conflict with each other.
    all_candidates: list[StageCandidate] = _get_candidates_from_overlay(
        part_list, partition
    )

    for part in part_list:
        candidate = _get_candidate_from_install_dir(part, partition)
        if candidate is None:
            continue

        # Scan previous candidates for collisions. Since ``all_candidates`` contains
        # candidates from the overlay, this will also check for collisions between
        # install dirs and layers.
        for other_candidate in all_candidates:
            # Our files that are also in a different part.
            common = candidate.contents & other_candidate.contents

            conflict_files: list[str] = []
            for item in common:
                this = Path(candidate.source_dir, item)
                other = Path(other_candidate.source_dir, item)

                permissions_this = permissions.filter_permissions(
                    item, candidate.permissions
                )

                permissions_other = permissions.filter_permissions(
                    item, other_candidate.permissions
                )

                if paths_collide(
                    this,
                    other,
                    permissions_this,
                    permissions_other,
                    rel_dirname=Path(item).parent.as_posix(),
                    path1_is_overlay=candidate.is_overlay,
                    path2_is_overlay=other_candidate.is_overlay,
                ):
                    conflict_files.append(item)

            if conflict_files:
                if other_candidate.is_overlay:
                    raise errors.OverlayStageConflict(
                        part_name=candidate.part_name,
                        overlay_part_name=other_candidate.part_name,
                        conflicting_files=conflict_files,
                        partition=partition,
                    )
                raise errors.PartFilesConflict(
                    part_name=candidate.part_name,
                    other_part_name=other_candidate.part_name,
                    conflicting_files=conflict_files,
                    partition=partition,
                )

        # And add our candidate to the list.
        all_candidates.append(candidate)


def paths_collide(
    path1: Path | str,
    path2: Path | str,
    permissions_path1: list[Permissions] | None = None,
    permissions_path2: list[Permissions] | None = None,
    *,
    rel_dirname: str = "",
    path1_is_overlay: bool = False,
    path2_is_overlay: bool = False,
) -> bool:
    """Check whether the provided paths conflict to each other.

    If both paths have Permissions definitions, they are considered to be conflicting
    if the permissions are incompatible (as defined by
    ``permissions.permissions_are_compatible()``).

    :param path1: Path of the first element to compare.
    :param path2: Path of the second element to compare.
    :param permissions_path1: The list of ``Permissions`` that affect ``path1``.
    :param permissions_path2: The list of ``Permissions`` that affect ``path2``.
    :param rel_dirname: relative path of the directory the item is.
    :param path1_is_overlay: Indicates if path1 comes from the overlay.
    :param path2_is_overlay: Indicates if path2 comes from the overlay.
    """
    path1, path2 = Path(path1), Path(path2)
    if not (os.path.lexists(path1) and os.path.lexists(path2)):
        return False

    # Paths collide if they're both symlinks, but pointing to different places.
    path1_is_link = path1.is_symlink()
    path2_is_link = path2.is_symlink()
    if path1_is_link and path2_is_link:
        path1_target = path1.readlink()
        path2_target = path2.readlink()

        # Symlinks targeting relative path must be normalized if they
        # are compared with symlinks from the overlay.
        if (
            not path1_target.is_absolute()
            and path2_target.is_absolute()
            and path2_is_overlay
        ):
            path1_target = Path(normalize_symlink(path1_target, rel_dirname))

        if (
            not path2_target.is_absolute()
            and path1_target.is_absolute()
            and path1_is_overlay
        ):
            path2_target = Path(normalize_symlink(path2_target, rel_dirname))

        return path1_target != path2_target

    # Paths collide if one is a symlink, but not the other.
    if path1_is_link or path2_is_link:
        return True

    # Paths collide if one is a directory, but not the other.
    path1_is_dir = path1.is_dir()
    path2_is_dir = path2.is_dir()
    if path1_is_dir != path2_is_dir:
        return True

    # Paths collide if neither path is a directory, and the files have
    # different contents.
    if not (path1_is_dir and path2_is_dir) and _file_collides(path1, path2):
        return True

    # Otherwise, paths conflict if they have incompatible permissions.
    return not permissions_are_compatible(permissions_path1, permissions_path2)


def _file_collides(file_this: Path, file_other: Path) -> bool:
    if file_this.suffix != ".pc":
        return not filecmp.cmp(file_this, file_other, shallow=False)

    # pkgconfig files need special handling, only prefix line may be different.
    with file_this.open() as pc_file_1, file_other.open() as pc_file_2:
        for line_pc_1, line_pc_2 in zip(pc_file_1, pc_file_2):
            if line_pc_1.startswith("prefix=") and line_pc_2.startswith("prefix="):
                continue
            if line_pc_1 != line_pc_2:
                return True

    return False


def normalize_symlink(path: str | Path, rel_dirname: str | Path) -> str:
    """Simulate a symlink resolution (only one level).

    We do not want to really resolve the symlink with os.path.realpath() since it
    might point to another symlink (and so on).

    Convert the path as if were under rel_dirname and rel_dirname were at the
    root.

    """
    return os.path.normpath(Path("/", rel_dirname, path))
