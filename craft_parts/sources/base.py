# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2024 Canonical Ltd.
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
import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

import pydantic
import requests
from overrides import overrides

from craft_parts.dirs import ProjectDirs
from craft_parts.utils import os_utils, url_utils

from . import errors
from .cache import FileCache
from .checksum import verify_checksum

logger = logging.getLogger(__name__)


def get_json_extra_schema(type_pattern: str) -> dict[str, dict[str, Any]]:
    """Get extra values for this source type's JSON schema.

    This extra schema allows any source string if source-type is provided, but requires
    the given regex pattern if source-type is not declared. A user's IDE will thus
    warn that they need "source-type" only if the source type cannot be inferred.

    :param type_pattern: A (string) regular expression to use in determining whether
        the source string is sufficient to infer source-type.
    :returns: A dictionary to pass into a source model's config ``json_schema_extra``
    """
    return {
        "if": {"not": {"required": ["source-type"]}},
        "then": {"properties": {"source": {"pattern": type_pattern}}},
    }


def get_model_config(
    json_schema_extra: dict[str, Any] | None = None,
) -> pydantic.ConfigDict:
    """Get a config for a model with minor changes from the default."""
    return pydantic.ConfigDict(
        alias_generator=lambda s: s.replace("_", "-"),
        json_schema_extra=json_schema_extra,
        extra="forbid",
    )


class BaseSourceModel(pydantic.BaseModel, frozen=True):  # type: ignore[misc]
    """A base model for source types."""

    model_config = get_model_config()
    source_type: str
    """The name of this source type.

    Sources must define this with a type hint of a Literal type of its name
    and a value of its name.
    """
    source: str
    pattern: ClassVar[str | None] = None
    """A regular expression for inferring this source type.

    If pattern is None (the default), the source type cannot be inferred and must
    always be explicitly written in the source-type field of a part.
    """


class BaseFileSourceModel(BaseSourceModel, frozen=True):
    """A base model for file-based source types."""

    source_checksum: str | None = None


class SourceHandler(abc.ABC):
    """The base class for source type handlers.

    Methods :meth:`check_if_outdated` and :meth:`update_source` can be
    overridden by subclasses to implement verification and update of
    source files.
    """

    source_model: ClassVar[type[BaseSourceModel]]

    def __init__(
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        ignore_patterns: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if not ignore_patterns:
            ignore_patterns = []

        invalid_options = []
        model_params = {key.replace("_", "-"): value for key, value in kwargs.items()}
        model_params["source"] = source
        properties = self.source_model.model_json_schema()["properties"]
        for option, value in kwargs.items():
            option_alias = option.replace("_", "-")
            if option_alias not in properties:
                if not value:
                    del model_params[option_alias]
                else:
                    invalid_options.append(option_alias)
        if len(invalid_options) > 1:
            raise errors.InvalidSourceOptions(
                source_type=properties["source-type"]["default"],
                options=invalid_options,
            )
        if len(invalid_options) == 1:
            raise errors.InvalidSourceOption(
                source_type=properties["source-type"]["default"],
                option=invalid_options[0],
            )

        self._data = self.source_model.model_validate(model_params)

        self.source = source
        self.part_src_dir = part_src_dir
        self._cache_dir = cache_dir
        self.source_details: dict[str, str | None] | None = None
        self._dirs = project_dirs
        self._checked = False
        self._ignore_patterns = ignore_patterns.copy()

        self.outdated_files: list[str] | None = None
        self.outdated_dirs: list[str] | None = None

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 (this must be dynamic)
        return getattr(self._data, name)

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
    def _run(cls, command: list[str], **kwargs: Any) -> None:
        try:
            os_utils.process_run(command, logger.debug, **kwargs)
        except subprocess.CalledProcessError as err:
            raise errors.PullError(command=command, exit_code=err.returncode) from err

    @classmethod
    def _run_output(cls, command: Sequence) -> str:
        try:
            return subprocess.check_output(command, text=True).strip()
        except subprocess.CalledProcessError as err:
            raise errors.PullError(command=command, exit_code=err.returncode) from err


class FileSourceHandler(SourceHandler):
    """Base class for file source types."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        source_checksum: str | None = None,
        command: str | None = None,
        ignore_patterns: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_checksum=source_checksum,
            command=command,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
            **kwargs,
        )
        self._file = Path()

    # pylint: enable=too-many-arguments

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
        is_source_url = url_utils.is_url(self.source)

        # First check if it is a url and download and if not
        # it is probably locally referenced.
        if is_source_url:
            source_file = self.download()
        else:
            basename = os.path.basename(self.source)
            source_file = Path(self.part_src_dir, basename)
            # We make this copy as the provisioning logic can delete
            # this file and we don't want that.
            try:
                shutil.copy2(self.source, source_file)
            except FileNotFoundError as err:
                raise errors.SourceNotFound(self.source) from err

        # Verify before provisioning
        if self.source_checksum:
            verify_checksum(self.source_checksum, source_file)

        self.provision(self.part_src_dir, src=source_file)

    def download(self, filepath: Path | None = None) -> Path:
        """Download the URL from a remote location.

        :param filepath: the destination file to download to.
        """
        if filepath is None:
            self._file = Path(self.part_src_dir, os.path.basename(self.source))
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

        # if not we download and store
        if url_utils.get_url_scheme(self.source) == "ftp":
            raise NotImplementedError("ftp download not implemented")

        try:
            request = requests.get(
                self.source, stream=True, allow_redirects=True, timeout=3600
            )
            request.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == requests.codes.not_found:
                raise errors.SourceNotFound(source=self.source) from err

            raise errors.HttpRequestError(
                status_code=err.response.status_code,
                reason=err.response.reason,
                source=self.source,
            ) from err
        except requests.exceptions.RequestException as err:
            raise errors.NetworkRequestError(
                message=f"network request failed (request={err.request!r}, "
                f"response={err.response!r})",
                source=self.source,
            ) from err

        url_utils.download_request(request, str(self._file))

        # if source_checksum is defined cache the file for future reuse
        if self.source_checksum:
            verify_checksum(self.source_checksum, self._file)
            file_cache.cache(filename=str(self._file), key=self.source_checksum)
        return self._file
