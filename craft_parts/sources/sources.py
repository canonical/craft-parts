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

"""Source handle utilities.

Unless the part plugin overrides this behaviour, a part can use these
'source' keys in its definition. They tell Craft Parts where to pull source
code for that part, and how to unpack it if necessary.

  - source: url-or-path

    A URL or path to some source tree to build. It can be local
    ('./src/foo') or remote ('https://foo.org/...'), and can refer to a
    directory tree or a tarball or a revision control repository
    ('git:...').

  - source-type: git, tar, deb, rpm, or zip

    In some cases the source string is not enough to identify the version
    control system or compression algorithm. The source-type key can tell
    Craft Parts exactly how to treat that content.

  - source-checksum: <algorithm>/<digest>

    Craft Parts will use the digest specified to verify the integrity of the
    source. The source-type needs to be a file (tar, zip, deb or rpm) and
    the algorithm either md5, sha1, sha224, sha256, sha384, sha512, sha3_256,
    sha3_384 or sha3_512.

  - source-depth: <integer>

    By default clones or branches with full history, specifying a depth
    will truncate the history to the specified number of commits.

  - source-branch: <branch-name>

    Craft Parts will checkout a specific branch from the source tree. This
    only works on multi-branch repositories from git and hg (mercurial).

  - source-commit: <commit>

    Craft Parts will checkout the specific commit from the source tree revision
    control system.

  - source-tag: <tag>

    Craft Parts will checkout the specific tag from the source tree revision
    control system.

  - source-subdir: path

    When building, Snapcraft will set the working directory to be this
    subdirectory within the source.

  - source-submodules: <list-of-submodules>

    Configure which submodules to fetch from the source tree.
    If source-submodules in defined and empty, no submodules are fetched.
    If source-submodules is not defined, all submodules are fetched (default
    behavior).

Note that plugins might well define their own semantics for the 'source'
keywords, because they handle specific build systems, and many languages
have their own built-in packaging systems (think CPAN, PyPI, NPM). In those
cases you want to refer to the documentation for the specific plugin.
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pydantic_core

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import BaseSourceModel, SourceHandler
from .deb_source import DebSource
from .file_source import FileSource
from .git_source import GitSource
from .local_source import LocalSource
from .rpm_source import RpmSource
from .sevenzip_source import SevenzipSource
from .snap_source import SnapSource
from .tar_source import TarSource
from .zip_source import ZipSource

if TYPE_CHECKING:
    from craft_parts.parts import Part

SourceHandlerType = type[SourceHandler]

_MANDATORY_SOURCES: dict[str, SourceHandlerType] = {
    "local": LocalSource,
    "tar": TarSource,
    "git": GitSource,
    "snap": SnapSource,
    "zip": ZipSource,
    "deb": DebSource,
    "file": FileSource,
    "rpm": RpmSource,
    "7z": SevenzipSource,
}

_SOURCES: dict[str, SourceHandlerType] = {}


def _get_type_name_from_model(model: type[BaseSourceModel]) -> str:
    source_type = model.model_fields["source_type"]
    if (default := source_type.get_default()) is not pydantic_core.PydanticUndefined:
        return str(default)
    if source_type.annotation is None:
        raise TypeError("Source type needs an annotation.")
    return str(source_type.annotation.__args__[0])


def register(source: SourceHandlerType, /) -> None:
    """Register source handlers.

    :param source: a SourceHandler class to register.
    :raises: ValueError if the source handler overrides a built-in source type.
    """
    source_name = _get_type_name_from_model(source.source_model)
    if source_name in _MANDATORY_SOURCES:
        raise ValueError(f"Built-in source types cannot be overridden: {source_name!r}")
    _SOURCES[source_name] = source


def unregister(source: str, /) -> None:
    """Unregister a source handler by name."""
    if source in _MANDATORY_SOURCES:
        raise ValueError(f"Built-in source types cannot be unregistered: {source!r}")
    try:
        del _SOURCES[source]
    except KeyError:
        raise ValueError(f"Source type not registered: {source!r}") from None


def get_source_handler(
    cache_dir: Path,
    part: "Part",
    project_dirs: ProjectDirs,
    ignore_patterns: list[str] | None = None,
) -> SourceHandler | None:
    """Return the appropriate handler for the given source.

    :param application_name: The name of the application using Craft Parts.
    :param part: The part to get a source handler for.
    :param project_dirs: The project's work directories.
    """
    source_handler = None
    if part.spec.source:
        handler_class = _get_source_handler_class(
            part.spec.source,
            source_type=part.spec.source_type,
        )
        source_handler = handler_class(
            cache_dir=cache_dir,
            source=part.spec.source,
            part_src_dir=part.part_src_dir,
            source_checksum=part.spec.source_checksum,
            source_branch=part.spec.source_branch,
            source_tag=part.spec.source_tag,
            source_depth=part.spec.source_depth,
            source_commit=part.spec.source_commit,
            source_submodules=part.spec.source_submodules,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )

    return source_handler


def _get_source_handler_class(
    source: str, *, source_type: str = ""
) -> SourceHandlerType:
    """Return the appropriate handler class for the given source.

    :param source: The source specification.
    :param source_type: The source type to use. If not specified, the
        type will be inferred from the source specification.
    """
    if not source_type:
        source_type = get_source_type_from_uri(source)

    if source_type in _MANDATORY_SOURCES:
        return _MANDATORY_SOURCES[source_type]
    if source_type in _SOURCES:
        return _SOURCES[source_type]

    raise errors.InvalidSourceType(source, source_type=source_type)


def get_source_type_from_uri(
    source: str, ignore_errors: bool = False  # noqa: FBT001, FBT002
) -> str:
    """Return the source type based on the given source URI.

    :param source: The source specification.
    :param ignore_errors: Don't raise InvalidSourceType if the source
        type could not be determined.
    :returns: a string matching the registered source type.

    :raise InvalidSourceType: If the source type is unknown.
    """
    for source_cls in (*_MANDATORY_SOURCES.values(), *_SOURCES.values()):
        source_model = source_cls.source_model
        if source_model.pattern and re.search(source_model.pattern, source):
            return _get_type_name_from_model(source_model)
    # Special case for the "local" source for backwards compatibility.
    if os.path.isdir(source):
        return "local"
    if ignore_errors:
        return ""
    raise errors.InvalidSourceType(source)
