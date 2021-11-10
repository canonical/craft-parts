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

"""Implement the git source handler."""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import SourceHandler


class GitSource(SourceHandler):
    """The git source handler.

    Retrieve part sources from a git repository. Branch, depth, commit
    and tag can be specified using part properties ``source-branch``,
    ``source-depth``, `source-commit`` and ``source-tag``.
    """

    @classmethod
    def version(cls) -> str:
        """Get git version information."""
        return subprocess.check_output(
            ["git", "version"], universal_newlines=True, stderr=subprocess.DEVNULL
        ).strip()

    @classmethod
    def check_command_installed(cls) -> bool:
        """Check if git is installed."""
        try:
            cls.version()
        except FileNotFoundError:
            return False
        return True

    @classmethod
    def generate_version(cls, *, part_src_dir=None) -> str:
        """Return the latest git tag from PWD or defined part_src_dir.

        The output depends on the use of annotated tags and will return
        something like: '2.28+git.10.abcdef' where '2.28 is the
        tag, '+git' indicates there are commits ahead of the tag, in
        this case it is '10' and the latest commit hash begins with
        'abcdef'. If there are no tags or the revision cannot be
        determined, this will return 0 as the tag and only the commit
        hash of the latest commit.
        """
        if not part_src_dir:
            part_src_dir = os.getcwd()

        encoding = sys.getfilesystemencoding()
        try:
            output = (
                subprocess.check_output(
                    ["git", "-C", part_src_dir, "describe", "--dirty"],
                    stderr=subprocess.DEVNULL,
                )
                .decode(encoding)
                .strip()
            )
        except subprocess.CalledProcessError as err:
            # If we fall into this exception it is because the repo is not
            # tagged at all.
            proc = subprocess.Popen(  # pylint: disable=consider-using-with
                ["git", "-C", part_src_dir, "describe", "--dirty", "--always"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                # This most likely means the project we are in is not driven
                # by git.
                raise errors.VCSError(message=stderr.decode(encoding).strip()) from err
            return "0+git.{}".format(stdout.decode(encoding).strip())

        match = re.search(
            r"^(?P<tag>[a-zA-Z0-9.+~-]+)-"
            r"(?P<revs_ahead>\d+)-"
            r"g(?P<commit>[0-9a-fA-F]+(?:-dirty)?)$",
            output,
        )

        if not match:
            # This means we have a pure tag
            return output

        tag = match.group("tag")
        revs_ahead = match.group("revs_ahead")
        commit = match.group("commit")

        return "{}+git{}.{}".format(tag, revs_ahead, commit)

    def __init__(  # pylint: disable=too-many-arguments
        self,
        source,
        part_src_dir,
        *,
        cache_dir: Path,
        source_tag: str = None,
        source_commit: str = None,
        source_branch: str = None,
        source_depth: Optional[int] = None,
        source_checksum: str = None,
        project_dirs: ProjectDirs = None,
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
            command="git",
        )

        if not self.command:
            raise RuntimeError("command not specified")

        if source_tag and source_branch:
            raise errors.IncompatibleSourceOptions(
                "git", ["source-tag", "source-branch"]
            )
        if source_tag and source_commit:
            raise errors.IncompatibleSourceOptions(
                "git", ["source-tag", "source-commit"]
            )
        if source_branch and source_commit:
            raise errors.IncompatibleSourceOptions(
                "git", ["source-branch", "source-commit"]
            )
        if source_checksum:
            raise errors.InvalidSourceOption(
                source_type="git", option="source-checksum"
            )

    def _fetch_origin_commit(self):
        """Fetch from origin, using source-commit if defined."""
        command = [
            self.command,
            "-C",
            self.part_src_dir,
            "fetch",
            "origin",
        ]
        if self.source_commit:
            command.append(self.source_commit)

        self._run(command)

    def _pull_existing(self):
        """Pull from origin, using branch, tag or commit if defined."""
        refspec = "HEAD"
        if self.source_branch:
            refspec = "refs/heads/" + self.source_branch
        elif self.source_tag:
            refspec = "refs/tags/" + self.source_tag
        elif self.source_commit:
            refspec = self.source_commit
            self._fetch_origin_commit()

        reset_spec = refspec if refspec != "HEAD" else "origin/master"

        command = [
            self.command,
            "-C",
            self.part_src_dir,
            "fetch",
            "--prune",
            "--recurse-submodules=yes",
        ]
        self._run(command)

        command = [self.command, "-C", self.part_src_dir, "reset", "--hard"]
        if reset_spec:
            command.append(reset_spec)

        self._run(command)

        # Merge any updates for the submodules (if any).
        command = [
            self.command,
            "-C",
            self.part_src_dir,
            "submodule",
            "update",
            "--recursive",
            "--force",
        ]
        self._run(command)

    def _clone_new(self):
        """Clone a git repository, using branch and depth if defined."""
        command = [self.command, "clone", "--recursive"]
        if self.source_tag or self.source_branch:
            command.extend(["--branch", self.source_tag or self.source_branch])
        if self.source_depth:
            command.extend(["--depth", str(self.source_depth)])
        self._run(command + [self.source, self.part_src_dir])

        if self.source_commit:
            self._fetch_origin_commit()
            command = [
                self.command,
                "-C",
                self.part_src_dir,
                "checkout",
                self.source_commit,
            ]
            self._run(command)

    def is_local(self) -> bool:
        """Verify whether the git repository is on the local filesystem."""
        return os.path.exists(os.path.join(self.part_src_dir, ".git"))

    def pull(self) -> None:
        """Retrieve the local or remote source files."""
        if self.is_local():
            self._pull_existing()
        else:
            self._clone_new()
        self.source_details = self._get_source_details()

    def _get_source_details(self):
        """Return a dictionary containing current source parameters."""
        tag = self.source_tag
        commit = self.source_commit
        branch = self.source_branch
        source = self.source
        checksum = self.source_checksum

        if not tag and not branch and not commit:
            commit = self._run_output(
                ["git", "-C", self.part_src_dir, "rev-parse", "HEAD"]
            )

        return {
            "source-commit": commit,
            "source-branch": branch,
            "source": source,
            "source-tag": tag,
            "source-checksum": checksum,
        }
