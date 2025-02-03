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

import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, cast

import pydantic
from overrides import overrides
from typing_extensions import Self

from craft_parts.utils.git import get_git_command

from . import errors
from .base import (
    BaseSourceModel,
    SourceHandler,
    get_json_extra_schema,
    get_model_config,
)

logger = logging.getLogger(__name__)


class GitSourceModel(BaseSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for a git-based source."""

    pattern = r"(^git(\+.+:|[@:])|\.git$)"
    model_config = get_model_config(get_json_extra_schema(r"(^git[+@:]|\.git$)"))
    source_type: Literal["git"] = "git"
    source: str
    source_tag: str | None = None
    source_commit: str | None = None
    source_branch: str | None = None
    source_depth: int = 0
    source_submodules: list[str] | None = None

    # TODO: make these mutually exclusive fields declarative with a jsonschema too.
    @pydantic.model_validator(mode="after")
    def _validate_mutually_exclusive_fields(self) -> Self:
        if self.source_tag and self.source_branch:
            raise errors.IncompatibleSourceOptions(
                self.model_fields["source_type"].default,
                ["source-tag", "source-branch"],
            )
        if self.source_tag and self.source_commit:
            raise errors.IncompatibleSourceOptions(
                self.model_fields["source_type"].default,
                ["source-tag", "source-commit"],
            )
        if self.source_branch and self.source_commit:
            raise errors.IncompatibleSourceOptions(
                self.model_fields["source_type"].default,
                ["source-branch", "source-commit"],
            )
        return self


class GitSource(SourceHandler):
    """The git source handler.

    Retrieve part sources from a git repository. Branch, depth, commit
    and tag can be specified using part properties ``source-branch``,
    ``source-depth``, `source-commit``, ``source-tag``, and ``source-submodules``.
    """

    source_model = GitSourceModel

    @classmethod
    def version(cls) -> str:
        """Get git version information."""
        return subprocess.check_output(
            [get_git_command(), "version"],
            universal_newlines=True,
            stderr=subprocess.DEVNULL,
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
    def generate_version(cls, *, part_src_dir: Path | None = None) -> str:
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
            part_src_dir = Path.cwd()

        encoding = sys.getfilesystemencoding()
        try:
            output = (
                subprocess.check_output(
                    [get_git_command(), "-C", str(part_src_dir), "describe", "--dirty"],
                    stderr=subprocess.DEVNULL,
                )
                .decode(encoding)
                .strip()
            )
        except subprocess.CalledProcessError as err:
            # If we fall into this exception it is because the repo is not
            # tagged at all.
            proc = subprocess.Popen(  # pylint: disable=consider-using-with
                [
                    get_git_command(),
                    "-C",
                    str(part_src_dir),
                    "describe",
                    "--dirty",
                    "--always",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                # This most likely means the project we are in is not driven
                # by git.
                raise errors.VCSError(message=stderr.decode(encoding).strip()) from err
            return f"0+git.{stdout.decode(encoding).strip()}"

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

        return f"{tag}+git{revs_ahead}.{commit}"

    def __init__(  # pylint: disable=too-many-arguments
        self,
        source: str,
        part_src_dir: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(source, part_src_dir, **kwargs)

    def _fetch_origin_commit(self) -> None:
        """Fetch from origin, using source-commit if defined."""
        command = [get_git_command(), "-C", str(self.part_src_dir), "fetch", "origin"]
        if self.source_commit:
            command.append(self.source_commit)

        self._run(command)

    def _get_current_branch(self) -> str:
        """Get current git branch."""
        command = [
            get_git_command(),
            "-C",
            str(self.part_src_dir),
            "branch",
            "--show-current",
        ]

        return self._run_output(command)

    def _pull_existing(self) -> None:
        """Pull data for an existing repository.

        For an existing (initialized) local git repository, pull from origin
        using branch, tag, or commit if defined.

        `git reset --hard` is preferred over `git pull` to avoid
        merge and rebase conflicts.

        If no branch, tag, or commit is defined, then pull from origin/<current-branch>.
        """
        refspec = "HEAD"
        if self.source_branch:
            refspec = "refs/remotes/origin/" + self.source_branch
        elif self.source_tag:
            refspec = "refs/tags/" + self.source_tag
        elif self.source_commit:
            refspec = self.source_commit
            self._fetch_origin_commit()
        else:
            refspec = "refs/remotes/origin/" + self._get_current_branch()

        command_prefix = [get_git_command(), "-C", str(self.part_src_dir)]
        command = [*command_prefix, "fetch", "--prune"]

        if self.source_submodules is None or len(self.source_submodules) > 0:
            command.append("--recurse-submodules=yes")
        self._run(command)

        command = [*command_prefix, "reset", "--hard", refspec]

        self._run(command)

        if self.source_submodules is None or len(self.source_submodules) > 0:
            command = [*command_prefix, "submodule", "update", "--recursive", "--force"]
            if self.source_submodules:
                for submodule in self.source_submodules:
                    command.append(submodule)
            self._run(command)

    def _clone_new(self) -> None:
        """Clone a git repository, using submodules, branch, and depth if defined."""
        command = [get_git_command(), "clone"]
        if self.source_submodules is None:
            command.append("--recursive")
        else:
            command.extend(
                ["--recursive=" + submodule for submodule in self.source_submodules]
            )
        if self.source_tag or self.source_branch:
            command.extend(
                ["--branch", cast(str, self.source_tag or self.source_branch)]
            )
        if self.source_depth:
            command.extend(["--depth", str(self.source_depth)])

        # reformat source string
        command.append(self._format_source())

        logger.debug("Executing: %s", " ".join([str(i) for i in command]))
        self._run([*command, str(self.part_src_dir)])

        if self.source_commit:
            self._fetch_origin_commit()
            command = [
                get_git_command(),
                "-C",
                str(self.part_src_dir),
                "checkout",
                self.source_commit,
            ]
            logger.debug("Executing: %s", " ".join([str(i) for i in command]))
            self._run(command)

    def is_local(self) -> bool:
        """Verify whether the git repository is on the local filesystem."""
        return Path(self.part_src_dir, ".git").exists()

    def _format_source(self) -> str:
        """Format source to a git-compatible format.

        Protocols for git are http[s]://, ftp[s]://, git://, ssh://, git+ssh://, and
        file://. Additionally, scp-style syntax is also valid: [user@]host:path/to/repo)

        Local sources are formatted as file:///absolute/path/to/local/source
        This is done because `git clone --depth=1 path/to/local/source` is invalid
        """
        protocol_pattern = re.compile(r"^[\w\-.@+]+:")

        if protocol_pattern.search(self.source):
            return self.source

        return f"file://{Path(self.source).resolve()}"

    @overrides
    def pull(self) -> None:
        """Retrieve the local or remote source files."""
        if self.is_local():
            self._pull_existing()
        else:
            self._clone_new()
        self.source_details = self._get_source_details()

    def _get_source_details(self) -> dict[str, str | None]:
        """Return a dictionary containing current source parameters."""
        tag = self.source_tag
        commit = self.source_commit
        branch = self.source_branch
        source = self.source

        if not tag and not branch and not commit:
            commit = self._run_output(
                [get_git_command(), "-C", str(self.part_src_dir), "rev-parse", "HEAD"]
            )

        return {
            "source-commit": commit,
            "source-branch": branch,
            "source": source,
            "source-tag": tag,
        }
