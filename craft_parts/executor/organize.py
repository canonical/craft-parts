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

"""Handle part files organization.

Installed part files can be reorganized according to a mapping specified
under the `organize` entry in a part definition. In the key/value pair,
the key represents the path of a file inside the part and the value
represents how the file is going to be staged.
"""

import contextlib
import os
import shutil
from glob import iglob
from pathlib import Path
from typing import Dict, Mapping, Optional

from craft_parts import errors
from craft_parts.utils import file_utils, path_utils


def organize_files(
    *,
    part_name: str,
    file_map: Dict[str, str],
    install_dir_map: Mapping[Optional[str], Path],
    overwrite: bool,
) -> None:
    """Rearrange files for part staging.

    If partitions are enabled, source filepaths must be in the default partition.

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
        src_partition, src_inner_path = path_utils.get_partition_and_path(key)

        if src_partition and src_partition != "default":
            raise errors.FileOrganizeError(
                part_name=part_name,
                message=(
                    f"Cannot organize files from {src_partition!r} partition. "
                    "Files can only be organized from the 'default' partition"
                ),
            )

        src = os.path.join(install_dir_map[src_partition], src_inner_path)

        # Remove the leading slash so the path actually joins
        # Also trailing slash is significant, be careful if using pathlib!
        dst_partition, dst_inner_path = path_utils.get_partition_and_path(
            file_map[key].lstrip("/")
        )

        dst = os.path.join(install_dir_map[dst_partition], dst_inner_path)

        # prefix the partition to the log-friendly version of the destination
        if dst_partition and dst_partition != "default":
            dst_string = f"({dst_partition})/{dst_inner_path}"
        else:
            dst_string = str(dst_inner_path)

        sources = iglob(src, recursive=True)

        # Keep track of the number of glob expansions so we can properly error if more
        # than one tries to organize to the same file
        src_count = 0
        for src in sources:
            src_count += 1

            if os.path.isdir(src) and "*" not in key:
                file_utils.link_or_copy_tree(src, dst)
                shutil.rmtree(src)
                continue

            if os.path.isfile(dst):
                if overwrite and src_count <= 1:
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(dst)
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
                    raise errors.FileOrganizeError(
                        part_name=part_name,
                        message=(
                            f"trying to organize file {key!r} to "
                            f"{file_map[key]!r}, but "
                            f"{dst_string!r} already exists"
                        ),
                    )

            if os.path.isdir(dst) and overwrite:
                real_dst = os.path.join(dst, os.path.basename(src))
                if os.path.isdir(real_dst):
                    shutil.rmtree(real_dst)
                else:
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(real_dst)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
