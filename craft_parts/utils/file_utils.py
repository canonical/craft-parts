# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""File-related utilities."""

import hashlib
from typing import Generator


def calculate_hash(filename: str, *, algorithm: str) -> str:
    """Calculate the hash of the given file.

    :param filename: The path to the file to digest.
    :param algorithm: The algorithm to use, as defined by ``hashlib``.
    """
    # This will raise an AttributeError if algorithm is unsupported
    hasher = getattr(hashlib, algorithm)()

    for block in _file_reader_iter(filename):
        hasher.update(block)
    return hasher.hexdigest()


def _file_reader_iter(
    path: str, block_size: int = 2 ** 20
) -> Generator[bytes, None, None]:
    """Read a file in blocks.

    :param path: The path to the file to read.
    :param block_size: The size of the block to read, default is 1MiB.
    """
    with open(path, "rb") as file:
        block = file.read(block_size)
        while len(block) > 0:
            yield block
            block = file.read(block_size)
