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

"""Source handle utilities.

Unless the part plugin overrides this behaviour, a part can use these
'source' keys in its definition. They tell Craft Parts where to pull source
code for that part, and how to unpack it if necessary.

  - source: url-or-path

    A URL or path to some source tree to build. It can be local
    ('./src/foo') or remote ('https://foo.org/...'), and can refer to a
    directory tree or a tarball or a revision control repository
    ('git:...').

  - source-type: git, bzr, hg, svn, tar, deb, rpm, or zip

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
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import SourceHandler
from .deb_source import DebSource
from .git_source import GitSource
from .local_source import LocalSource
from .snap_source import SnapSource
from .tar_source import TarSource
from .zip_source import ZipSource

if TYPE_CHECKING:
    from craft_parts.parts import Part

SourceHandlerType = Type[SourceHandler]


_source_handler: Dict[str, SourceHandlerType] = {
    "local": LocalSource,
    "tar": TarSource,
    "git": GitSource,
    "snap": SnapSource,
    "zip": ZipSource,
    "deb": DebSource,
}


def get_source_handler(
    cache_dir: Path,
    part: "Part",
    project_dirs: ProjectDirs,
    ignore_patterns: Optional[List[str]] = None,
) -> Optional[SourceHandler]:
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


def _get_source_handler_class(source, *, source_type: str = "") -> SourceHandlerType:
    """Return the appropriate handler class for the given source.

    :param source: The source specification.
    :param source_type: The source type to use. If not specified, the
        type will be inferred from the source specification.
    """
    if not source_type:
        source_type = get_source_type_from_uri(source)

    if source_type not in _source_handler:
        raise errors.InvalidSourceType(source)

    return _source_handler.get(source_type, LocalSource)


_tar_type_regex = re.compile(r".*\.((tar(\.(xz|gz|bz2))?)|tgz)$")


def get_source_type_from_uri(
    source: str, ignore_errors: bool = False
) -> str:  # noqa: C901
    """Return the source type based on the given source URI.

    :param source: The source specification.
    :param ignore_errors: Don't raise InvalidSourceType if the source
        type could not be determined.

    :raise InvalidSourceType: If the source type is unknown.
    """
    for extension in ["zip", "deb", "rpm", "7z", "snap"]:
        if source.endswith(f".{extension}"):
            return extension
    source_type = ""
    if source.startswith("bzr:") or source.startswith("lp:"):
        source_type = "bzr"
    elif (
        source.startswith("git:")
        or source.startswith("git@")
        or source.endswith(".git")
    ):
        source_type = "git"
    elif source.startswith("svn:"):
        source_type = "subversion"
    elif _tar_type_regex.match(source):
        source_type = "tar"
    elif os.path.isdir(source):
        source_type = "local"
    elif not ignore_errors:
        raise errors.InvalidSourceType(source)

    return source_type
