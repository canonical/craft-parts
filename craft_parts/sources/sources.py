# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
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

Note that plugins might well define their own semantics for the 'source'
keywords, because they handle specific build systems, and many languages
have their own built-in packaging systems (think CPAN, PyPI, NPM). In those
cases you want to refer to the documentation for the specific plugin.
"""

from typing import Dict, Type

from .base import SourceHandler
from .local_source import LocalSource

SourceHandlerType = Type[SourceHandler]


_source_handler: Dict[str, SourceHandlerType] = {
    "local": LocalSource,
}
