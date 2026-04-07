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

"""Handle part files organization.

Installed part files can be reorganized according to a mapping specified
under the `organize` entry in a part definition. In the key/value pair,
the key represents the path of a file inside the part and the value
represents how the file is going to be staged.
"""

from __future__ import annotations
from craft_parts.utils.file_utils import find_merge_conflicts, get_path_differences

import contextlib
import os
import pathlib
import shutil
from glob import iglob
from typing import TYPE_CHECKING

from craft_parts import errors
from craft_parts.errors import FileOrganizeError
from craft_parts.utils import file_utils, path_utils
from craft_parts.utils.partition_utils import DEFAULT_PARTITION

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def _render_merge_conflicts(
    key: str,
    map_value: str,
    dst_root: str,
    conflicts: Mapping[Path, list[str]],
) -> str:
    if len(conflicts) == 1:
        ((conflict_path, issues), *_) = conflicts.items()
        dst_path = dst_root / conflict_path
        if len(issues) == 1:
            issue = issues[0]
            return (
                f"trying to organize directory {key!r} to {map_value!r}, but "
                f"{dst_path.as_posix()!r} already exists and {issue}"
            )
        issue_list = "\n".join(f" - {issue}" for issue in issues)
        return (
            f"trying to organize directory {key!r} to {map_value!r}, but "
            f"{dst_path.as_posix()!r} already exists and:\n{issue_list}"
        )
    return "I fucked up"


def organize_files(  # noqa: PLR0912
    *,
    part_name: str,
    file_map: dict[str, str],
    install_dir_map: Mapping[str | None, Path],
    overwrite: bool,
    default_partition: str,
) -> None:
    """Rearrange files for part staging.

    If partitions are enabled, source filepaths must be in the default partition.
    The default partition can be referenced by the provided default_partition name
    or by the DEFAULT_PARTITION value.

    :param part_name: The name of the part to organize files for.
    :param file_map: A mapping of source filepaths to destination filepaths.
    :param install_dir_map: A mapping of partition names to their install directories.
    :param overwrite: Whether existing files should be overwritten. This is
        only used in build updates, when a part may organize over files
        it previously organized.

    :raises FileOrganizeError: If the destination file already exists or multiple files
        are organized to the same destination.
    :raises FileOrganizeError: If partitions are enabled and the source file is not from
        the default partition.
    """
    for key in sorted(file_map, key=lambda x: ["*" in x, x]):
        src = get_src_path(key, part_name, install_dir_map, default_partition)
        dst, dst_string = get_dst_path(
            key, file_map, install_dir_map, default_partition
        )
        dst_path = pathlib.Path(dst)

        sources = iglob(src, recursive=True)  # noqa: PTH207

        # Keep track of the number of glob expansions so we can properly error if more
        # than one tries to organize to the same file
        src_count = 0
        for src in sources:
            src_path = pathlib.Path(src)
            src_count += 1

            # Organize a symlink to its target
            if src_path.is_symlink() and src_path.readlink().samefile(dst):
                src_path.unlink()
                continue
            # Organize a symlink's target to the link
            if dst_path.is_symlink() and dst_path.readlink().samefile(src_path):
                dst_path.unlink()
                file_utils.move(src, dst)
                continue

            # Organize a dir to a dir
            if os.path.isdir(src):  # noqa: PTH112
                if dst_path.exists() and dst_path.samefile(src):
                    continue
                if "*" in key:
                    real_dst = dst_path / src_path.name
                else:
                    real_dst = dst_path
                if not overwrite:
                    conflicts = find_merge_conflicts(src_path, real_dst)
                    if conflicts:
                        raise errors.FileOrganizeError(
                            part_name=part_name,
                            message=_render_merge_conflicts(
                                key,
                                file_map[key],
                                dst_string,
                                conflicts,
                            ),
                        )
                file_utils.link_or_copy_tree(src, real_dst.as_posix())
                shutil.rmtree(src)
                continue

            # Organize a "not dir" (file, character device, etc.) to a "not dir"
            if os.path.isfile(dst):  # noqa: PTH113
                if os.path.abspath(dst) == os.path.abspath(src):  # noqa: PTH100
                    # Trying to organize a file to the same place, skipping
                    continue
                if overwrite and src_count <= 1:
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(dst)  # noqa: PTH107
                elif src_count > 1:
                    raise errors.FileOrganizeError(
                        part_name=part_name,
                        message=(
                            "multiple files to be organized into "
                            f"{dst_string!r}. If this is "
                            "supposed to be a directory, end it with a slash."
                        ),
                    )
                else:
                    if get_path_differences(pathlib.Path(src), pathlib.Path(dst)):
                        raise errors.FileOrganizeError(
                            part_name=part_name,
                            message=(
                                f"trying to organize file {key!r} to "
                                f"{file_map[key]!r}, but "
                                f"{dst_string!r} already exists"
                            ),
                        )

            # Organize a "not dir" to a dir
            if os.path.isdir(dst):  # noqa: PTH112
                real_dst = os.path.join(dst, os.path.basename(src))  # noqa: PTH118, PTH119
                if os.path.abspath(real_dst) == os.path.abspath(src):  # noqa: PTH100
                    # Trying to organize a file to the same place, skipping
                    continue
                if overwrite:
                    if os.path.isdir(real_dst):  # noqa: PTH112
                        shutil.rmtree(real_dst)
                    else:
                        with contextlib.suppress(FileNotFoundError):
                            os.remove(real_dst)  # noqa: PTH107
                elif os.path.exists(real_dst):  # noqa: PTH110
                    if not get_path_differences(src_path, pathlib.Path(real_dst)):
                        src_path.unlink()
                        continue
                    rel_dst_string = os.path.join(dst_string, os.path.basename(src))  # noqa: PTH118, PTH119
                    raise errors.FileOrganizeError(
                        part_name=part_name,
                        message=(
                            f"trying to organize {key!r} to "
                            f"{file_map[key]!r}, but "
                            f"{rel_dst_string!r} already exists"
                        ),
                    )

            os.makedirs(os.path.dirname(dst), exist_ok=True)  # noqa: PTH103, PTH120
            file_utils.move(src, dst)


def get_src_path(
    key: str,
    part_name: str,
    install_dir_map: Mapping[str | None, Path],
    default_partition: str,
) -> str:
    """Return the full path for a relative source."""
    src_partition, src_inner_path = path_utils.get_partition_and_path(
        key, default_partition
    )

    if src_partition and src_partition not in [
        default_partition,
        DEFAULT_PARTITION,
    ]:
        raise errors.FileOrganizeError(
            part_name=part_name,
            message=(
                f"Cannot organize files from {src_partition!r} partition. "
                f"Files can only be organized from the {default_partition!r} partition"
            ),
        )
    # Replace default partition default name with alias name to allow
    # using (default) in paths even with aliased default partition
    if src_partition == DEFAULT_PARTITION:
        src_partition = default_partition

    return os.path.join(install_dir_map[src_partition], src_inner_path)  # noqa: PTH118


def get_dst_path(
    key: str,
    file_map: dict[str, str],
    install_dir_map: Mapping[str | None, Path],
    default_partition: str,
) -> tuple[str, str]:
    """Return the full destination path and log-friendly representation of a destination."""
    # Remove the leading slash so the path actually joins
    # Also trailing slash is significant, be careful if using pathlib!
    dst_partition, dst_inner_path = path_utils.get_partition_and_path(
        file_map[key].lstrip("/"),
        default_partition,
    )

    # Replace default partition default name with alias name to allow
    # using (default) in paths even with aliased default partition
    if dst_partition == DEFAULT_PARTITION:
        dst_partition = default_partition

    # prefix the partition to the log-friendly version of the destination
    if dst_partition and dst_partition != default_partition:
        dst_string = f"({dst_partition})/{dst_inner_path}"
    else:
        dst_string = str(dst_inner_path)

    return os.path.join(install_dir_map[dst_partition], dst_inner_path), dst_string  # noqa: PTH118
