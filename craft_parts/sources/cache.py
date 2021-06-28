# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""Cache base and file cache."""

import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileCache:
    """Cache files based on the supplied key."""

    def __init__(self, cache_dir: Path, *, namespace: str = "files") -> None:
        """Create a FileCache under namespace.

        :param str namespace: The namespace for the cache (default is "files").
        """
        self.file_cache = Path(cache_dir, namespace)

    def cache(self, *, filename: str, key: str) -> Optional[Path]:
        """Cache a file revision with hash in XDG cache, unless it already exists.

        :param filename: The path to the file to cache.
        :param key: The key to cache the file under.

        :return: The path to the cached file, or None if the file was not cached.
        """
        cached_file_path = self.file_cache / key
        cached_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if not cached_file_path.is_file():
                shutil.copyfile(filename, cached_file_path)
        except OSError:
            logger.warning("Unable to cache file %s.", cached_file_path)
            return None
        return cached_file_path

    def get(self, *, key: str) -> Optional[Path]:
        """Get the filepath which matches the hash calculated with algorithm.

        :param key: The key used to cache the file.

        :return: The path to cached file, or None if the file is not cached.
        """
        cached_file_path = self.file_cache / key
        if cached_file_path.is_file():
            logger.debug("Cache hit for key %s", key)
            return cached_file_path

        return None

    def clean(self):
        """Remove all files from the cache namespace."""
        shutil.rmtree(self.file_cache)
