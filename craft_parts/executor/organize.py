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

import contextlib
import os
import pathlib
import shutil
from glob import iglob
from pathlib import Path
from typing import TYPE_CHECKING

from craft_parts import errors
from craft_parts.utils import file_utils, path_utils
from craft_parts.utils.partition_utils import (
    DEFAULT_PARTITION,
    OVERLAY_PARTITION,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


def _check_overlay_equivalence(
    *,
    part_name: str,
    key: str,
    file_map: dict[str, str],
    src_path: pathlib.Path,
    dst_path: pathlib.Path,
    dst_string: str,
) -> None:
    """Check if source and destination are equivalent on the overlay partition.

    If equivalent, removes the source (or merges if it's a directory).
    If not equivalent, raises FileOrganizeError.

    :param part_name: The name of the part being organized.
    :param key: The organize key (source pattern).
    :param file_map: The organize file map.
    :param src_path: The source path.
    :param dst_path: The destination path.
    :param dst_string: A display string for the destination.
    :raises FileOrganizeError: If the paths are not equivalent.
    """
    msg = file_utils.get_path_differences(src_path, dst_path)
    if not msg or (
        not src_path.is_symlink() and src_path.is_dir() and dst_path.is_dir()
    ):
        if not src_path.is_symlink() and src_path.is_dir():
            file_utils.link_or_copy_tree(src_path, dst_path, overwrite_metadata=False)
            shutil.rmtree(src_path)
        else:
            src_path.unlink()
        return
    raise errors.FileOrganizeError(
        part_name=part_name,
        message=(
            f"trying to organize file {key!r} to "
            f"{file_map[key]!r} but {dst_string!r} already "
            f"exists and the files have {', '.join(msg)}"
        ),
    )


def organize_files(  # noqa: PLR0912, PLR0915
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
        src_root = install_dir_map.get(None) or install_dir_map[default_partition]

        # Remove the leading slash so the path actually joins
        # Also trailing slash is significant, be careful if using pathlib!
        dst_partition_pair = path_utils.get_partition_and_path(
            file_map[key].lstrip("/"), default_partition
        )
        dst, dst_string = get_dst_path(
            key, file_map, install_dir_map, default_partition
        )
        dst_path = pathlib.Path(dst)

        # If the destination is a symlink to itself, unlink it and we'll replace it
        # with the real thing.
        if (
            dst_path.is_symlink()
            and (dst_path.parent / dst_path.readlink()) == dst_path
        ):
            dst_path.unlink()

        sources = iglob(src, recursive=True)  # noqa: PTH207

        # Keep track of the number of glob expansions so we can properly error if more
        # than one tries to organize to the same file
        src_count = 0
        for src in sources:
            src_count += 1
            src_path = pathlib.Path(src)

            # Organizing a symlink to the overlay partition simply deletes the link.
            if (
                dst_partition_pair.partition == OVERLAY_PARTITION
                and src_path.is_symlink()
            ):
                try:
                    # resolve() follows the symlink; relative_to() raises ValueError
                    # if the target lies outside src_root (e.g. absolute symlinks
                    # such as /usr/bin/true). Fall through to normal organise in
                    # that case.
                    relative_src_target = src_path.resolve().relative_to(src_root)
                except ValueError:
                    pass
                else:
                    dst_target = (
                        install_dir_map[OVERLAY_PARTITION] / relative_src_target
                    )
                    if dst_path in install_dir_map.values():
                        real_dst_path = dst_path / src_path.name
                    else:
                        real_dst_path = dst_path

                    if dst_target.exists() and (
                        dst_target.samefile(dst_path) or real_dst_path.is_dir()
                    ):
                        src_path.unlink()
                        continue
                    if real_dst_path.is_symlink() and real_dst_path.readlink() in (
                        dst_target,
                        relative_src_target,
                    ):
                        src_path.unlink()
                        continue
                    if src_path.readlink().is_absolute():
                        real_dst_path.symlink_to(dst_target)
                    else:
                        real_dst_path.symlink_to(relative_src_target)
                    src_path.unlink()
                    continue

            # Organize a dir to a dir
            if not src_path.is_symlink() and src_path.is_dir():
                if "*" not in key:  # Key is explicit
                    if dst_path.is_symlink():
                        real_dst_path = dst_path.resolve()
                    else:
                        real_dst_path = dst_path
                    file_utils.link_or_copy_tree(src, real_dst_path)
                    shutil.rmtree(src)
                    continue
                # Key is a glob
                # Organizing to the root of a partition in overwrite mode.
                if (
                    dst_path in install_dir_map.values()
                    or dst_partition_pair.partition == OVERLAY_PARTITION
                ):
                    if dst_path in install_dir_map.values():
                        real_dst_path = dst_path / src_path.name
                    else:
                        real_dst_path = dst_path
                    if not overwrite:
                        conflicts = file_utils.find_merge_conflicts(
                            src_path,
                            real_dst_path,
                            strict=dst_partition_pair.partition != OVERLAY_PARTITION,
                        )
                        if conflicts:
                            if dst_partition_pair.partition == OVERLAY_PARTITION:
                                conflicts = {
                                    p: msg
                                    for p, msg in conflicts.items()
                                    if not (
                                        (src_path / p).is_dir()
                                        and not (src_path / p).is_symlink()
                                        and (real_dst_path / p).is_dir()
                                        and not (real_dst_path / p).is_symlink()
                                    )
                                }
                            if conflicts:
                                raise errors.FileOrganizeError.from_merge_conflicts(
                                    part_name=part_name,
                                    key=key,
                                    destination=file_map[key],
                                    conflicts=conflicts,
                                )
                    # Where the key is a glob, we get the contents of the dir to
                    # organize, so we need to add the source's name back in.
                    file_utils.link_or_copy_tree(
                        src_path,
                        real_dst_path,
                        overwrite_metadata=(
                            dst_partition_pair.partition != OVERLAY_PARTITION
                        ),
                    )
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
                elif dst_partition_pair.partition == OVERLAY_PARTITION:
                    _check_overlay_equivalence(
                        part_name=part_name,
                        key=key,
                        file_map=file_map,
                        src_path=src_path,
                        dst_path=dst_path,
                        dst_string=dst_string,
                    )
                    continue
                else:
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
                    rel_dst_string = os.path.join(dst_string, os.path.basename(src))  # noqa: PTH118, PTH119
                    if dst_partition_pair.partition == OVERLAY_PARTITION:
                        _check_overlay_equivalence(
                            part_name=part_name,
                            key=key,
                            file_map=file_map,
                            src_path=pathlib.Path(src),
                            dst_path=pathlib.Path(real_dst),
                            dst_string=dst_string,
                        )
                        continue
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

    base_dir = Path(install_dir_map[src_partition]).resolve()
    src_path = base_dir / src_inner_path

    # Resolve only the parent path so symlinks being organized are preserved.
    # Resolving the full source path would follow the final symlink target and
    # reject valid symlinks that point outside the install directory.
    if not src_path.parent.resolve().is_relative_to(base_dir):
        raise errors.FileOrganizeError(
            part_name=part_name,
            message=(
                f"trying to organize from {key!r}, but source paths must stay within "
                f"the install directory"
            ),
        )

    return str(src_path)


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
