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

"""Handle part files organization.

Installed part files can be reorganized according to a mapping specified
under the `organize` entry in a part definition. In the key/value pair,
the key represents the path of a file inside the part and the value
represents how the file is going to be staged.
"""

import contextlib
import shutil
from pathlib import Path

from craft_parts import errors
from craft_parts.utils import file_utils, path_utils


def organize_files(
    *, part_name: str, mapping: dict[str, str], base_dir: Path, overwrite: bool
) -> None:
    """Rearrange files for part staging.

    :param fileset: A fileset containing the `organize` file mapping.
    :param base_dir: Where the installed files are located.
    :param overwrite: Whether existing files should be overwritten. This is
        only used in build updates, when a part may organize over files
        it previously organized.
    """
    for key in sorted(mapping, key=lambda x: ["*" in x, x]):
        src = base_dir / path_utils.get_partitioned_path(key)

        # Remove the leading slash so the path actually joins
        # Also trailing slash is significant, be careful if using pathlib!
        partition, inner_path = path_utils.get_partition_and_path(
            mapping[key].lstrip("/")
        )
        if partition:
            dst = base_dir / partition / inner_path
            partition_path = Path(f"({partition})") / inner_path
        else:
            dst = base_dir / inner_path
            partition_path = Path(inner_path)

        sources = src.rglob("*")

        # Keep track of the number of glob expansions so we can properly error if more
        # than one tries to organize to the same file
        src_count = 0
        for src in sources:
            src_count += 1

            if src.is_dir() and "*" not in key:
                file_utils.link_or_copy_tree(src, dst)
                shutil.rmtree(src)
                continue

            if dst.is_file():
                if overwrite and src_count <= 1:
                    with contextlib.suppress(FileNotFoundError):
                        dst.unlink()
                elif src_count > 1:
                    raise errors.FileOrganizeError(
                        part_name=part_name,
                        message=(
                            f"multiple files to be organized into "
                            f"{partition_path!r}. If this is "
                            f"supposed to be a directory, end it with a slash."
                        ),
                    )
                else:
                    raise errors.FileOrganizeError(
                        part_name=part_name,
                        message=(
                            f"trying to organize file {key!r} to "
                            f"{mapping[key]!r}, but "
                            f"{partition_path!r} already exists"
                        ),
                    )

            if dst.is_dir() and overwrite:
                real_dst = dst / src.name
                if real_dst.is_dir():
                    shutil.rmtree(real_dst)
                else:
                    with contextlib.suppress(FileNotFoundError):
                        real_dst.unlink()

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
