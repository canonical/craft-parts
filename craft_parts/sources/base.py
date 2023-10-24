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

"""Base classes for source type handling."""

import abc
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import requests
from overrides import overrides

from craft_parts.dirs import ProjectDirs
from craft_parts.utils import os_utils, url_utils

from . import errors
from .cache import FileCache
from .checksum import verify_checksum

logger = logging.getLogger(__name__)


class SourceHandler(abc.ABC):
    """The base class for source type handlers.

    Methods :meth:`check_if_outdated` and :meth:`update_source` can be
    overridden by subclasses to implement verification and update of
    source files.
    """

    def __init__(  # noqa: PLR0913
        self,
        source: Path | str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        source_tag: str | None = None,
        source_commit: str | None = None,
        source_branch: str | None = None,
        source_depth: int | None = None,
        source_checksum: str | None = None,
        source_submodules: list[str] | None = None,
        command: str | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        if not ignore_patterns:
            ignore_patterns = []

        self.source = source
        self.part_src_dir = part_src_dir
        self._cache_dir = cache_dir
        self.source_tag = source_tag
        self.source_commit = source_commit
        self.source_branch = source_branch
        self.source_depth = source_depth
        self.source_checksum = source_checksum
        self.source_details: dict[str, str | Path | None] | None = None
        self.source_submodules = source_submodules
        self.command = command
        self._dirs = project_dirs
        self._checked = False
        self._ignore_patterns = ignore_patterns.copy()

        self.outdated_files: list[str] | None = None
        self.outdated_dirs: list[str] | None = None

    @abc.abstractmethod
    def pull(self) -> None:
        """Retrieve the source file."""

    def check_if_outdated(
        self, target: str, *, ignore_files: list[str] | None = None  # noqa: ARG002
    ) -> bool:
        """Check if pulled sources have changed since target was created.

        :param target: Path to target file.
        :param ignore_files: Files excluded from verification.

        :return: Whether the sources are outdated.

        :raise errors.SourceUpdateUnsupported: If the source handler can't check if
            files are outdated.
        """
        raise errors.SourceUpdateUnsupported(self.__class__.__name__)

    def get_outdated_files(self) -> tuple[list[str], list[str]]:
        """Obtain lists of outdated files and directories.

        :return: The lists of outdated files and directories.

        :raise errors.SourceUpdateUnsupported: If the source handler can't check if
            files are outdated.
        """
        raise errors.SourceUpdateUnsupported(self.__class__.__name__)

    def update(self) -> None:
        """Update pulled source.

        :raise errors.SourceUpdateUnsupported: If the source can't update its files.
        """
        raise errors.SourceUpdateUnsupported(self.__class__.__name__)

    @classmethod
    def _run(cls, command: list[str], **kwargs: Any) -> None:  # noqa: ANN401
        try:
            os_utils.process_run(command, logger.debug, **kwargs)
        except subprocess.CalledProcessError as err:
            raise errors.PullError(command=command, exit_code=err.returncode) from err

    @classmethod
    def _run_output(cls, command: list[str]) -> str:
        try:
            return subprocess.check_output(command, text=True).strip()
        except subprocess.CalledProcessError as err:
            raise errors.PullError(command=command, exit_code=err.returncode) from err


class FileSourceHandler(SourceHandler):
    """Base class for file source types."""

    def __init__(  # noqa: PLR0913
        self,
        source: Path | str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        source_tag: str | None = None,
        source_commit: str | None = None,
        source_branch: str | None = None,
        source_depth: int | None = None,
        source_checksum: str | None = None,
        source_submodules: list[str] | None = None,
        command: str | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_tag=source_tag,
            source_commit=source_commit,
            source_branch=source_branch,
            source_depth=source_depth,
            source_checksum=source_checksum,
            source_submodules=source_submodules,
            command=command,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )
        self._file = Path()

    @abc.abstractmethod
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Process the source file to extract its payload."""

    @overrides
    def pull(self) -> None:
        """Retrieve this source from its origin."""
        source_file = None
        # First check if it is a url and download and if not
        # it is probably locally referenced.
        if not isinstance(self.source, Path):
            if url_utils.is_url(self.source):
                source_file = self.download()
            else:
                raise errors.SourceNotFound(self.source)
        else:
            source_file = Path(self.part_src_dir, self.source.name)
            # We make this copy as the provisioning logic can delete
            # this file and we don't want that.
            try:
                shutil.copy2(self.source, source_file)
            except FileNotFoundError as err:
                raise errors.SourceNotFound(str(self.source)) from err

        # Verify before provisioning
        if self.source_checksum:
            verify_checksum(self.source_checksum, source_file)

        self.provision(self.part_src_dir, src=source_file)

    def download(self, filepath: Path | None = None) -> Path:
        """Download the URL from a remote location.

        :param filepath: the destination file to download to.
        """
        if filepath is None:
            self._file = Path(self.part_src_dir, Path(self.source).name)
        else:
            self._file = filepath

        # check if we already have the source file cached
        file_cache = FileCache(self._cache_dir)
        if self.source_checksum:
            cache_file = file_cache.get(key=self.source_checksum)
            if cache_file:
                # We make this copy as the provisioning logic can delete
                # this file and we don't want that.
                shutil.copy2(cache_file, self._file)
                return self._file

        if not isinstance(self.source, str):
            raise errors.SourceNotFound(str(self.source))

        # if not we download and store
        if url_utils.get_url_scheme(self.source) == "ftp":
            raise NotImplementedError("ftp download not implemented")

        try:
            request = requests.get(
                self.source, stream=True, allow_redirects=True, timeout=3600
            )
            request.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise errors.NetworkRequestError(
                message=f"network request failed (request={err.request!r}, "
                f"response={err.response!r})"
            ) from err

        url_utils.download_request(request, self._file)

        # if source_checksum is defined cache the file for future reuse
        if self.source_checksum:
            verify_checksum(self.source_checksum, self._file)
            file_cache.cache(filename=str(self._file), key=self.source_checksum)
        return self._file
