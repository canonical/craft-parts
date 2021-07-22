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

"""Implement the tar source handler."""

import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import FileSourceHandler


# pylint: disable=too-many-arguments
class TarSource(FileSourceHandler):
    """The tar source handler."""

    def __init__(
        self,
        source,
        part_src_dir,
        *,
        cache_dir: Path,
        source_tag: Optional[str] = None,
        source_commit: Optional[str] = None,
        source_branch: Optional[str] = None,
        source_depth: Optional[int] = None,
        source_checksum: Optional[str] = None,
        project_dirs: Optional[ProjectDirs] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_tag=source_tag,
            source_commit=source_commit,
            source_branch=source_branch,
            source_depth=source_depth,
            source_checksum=source_checksum,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )
        if source_tag:
            raise errors.InvalidSourceOption(source_type="tar", option="source-tag")

        if source_commit:
            raise errors.InvalidSourceOption(source_type="tar", option="source-commit")

        if source_branch:
            raise errors.InvalidSourceOption(source_type="tar", option="source-branch")

        if source_depth:
            raise errors.InvalidSourceOption(source_type="tar", option="source-depth")

    def provision(self, dst, clean_target=True, keep=False, src=None):
        """Extract tarball contents to the part source dir."""
        # TODO add unit tests.
        if src:
            tarball = src
        else:
            tarball = os.path.join(self.part_src_dir, os.path.basename(self.source))

        if clean_target:
            with tempfile.NamedTemporaryFile() as tmp_file:
                tmp_tarball = tmp_file.name
                shutil.move(tarball, tmp_tarball)
                shutil.rmtree(dst)
                os.makedirs(dst)
                shutil.move(tmp_tarball, tarball)

        _extract(tarball, dst)

        if not keep:
            os.remove(tarball)


def _extract(tarball: str, dst: str) -> None:
    with tarfile.open(tarball) as tar:

        def filter_members(tar):
            """Strip common prefix and ban dangerous names."""
            members = tar.getmembers()
            common = os.path.commonprefix([m.name for m in members])

            # commonprefix() works a character at a time and will
            # consider "d/ab" and "d/abc" to have common prefix "d/ab";
            # check all members either start with common dir
            for member in members:
                if not (
                    member.name.startswith(common + "/")
                    or member.isdir()
                    and member.name == common
                ):
                    # commonprefix() didn't return a dir name; go up one
                    # level
                    common = os.path.dirname(common)
                    break

            for member in members:
                if member.name == common:
                    continue
                _strip_prefix(common, member)
                # We mask all files to be writable to be able to easily
                # extract on top.
                member.mode = member.mode | 0o200
                yield member

        # ignore type, members expect List but we're providing Generator
        tar.extractall(members=filter_members(tar), path=dst)  # type: ignore


def _strip_prefix(common: str, member: tarfile.TarInfo) -> None:
    if member.name.startswith(common + "/"):
        member.name = member.name[len(common + "/") :]
    # strip leading '/', './' or '../' as many times as needed
    member.name = re.sub(r"^(\.{0,2}/)*", r"", member.name)
    # do the same for linkname if this is a hardlink
    if member.islnk() and not member.issym():
        if member.linkname.startswith(common + "/"):
            member.linkname = member.linkname[len(common + "/") :]
        member.linkname = re.sub(r"^(\.{0,2}/)*", r"", member.linkname)
