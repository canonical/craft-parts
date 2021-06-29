# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Helpers to compute and verify file checksums."""

from pathlib import Path
from typing import Tuple

from craft_parts.utils import file_utils

from . import errors


def split_checksum(source_checksum: str) -> Tuple:
    """Split the given source checksum into algorithm and hash.

    :param source_checksum: Source checksum in algorithm/hash format.

    :return: a tuple consisting of the algorithm and the hash.

    :raise ValueError: If the checksum is not in the expected format.
    """
    try:
        algorithm, digest = source_checksum.split("/", 1)
    except ValueError as err:
        raise ValueError(f"invalid checksum format: {source_checksum!r}") from err

    return (algorithm, digest)


def verify_checksum(source_checksum: str, checkfile: Path) -> Tuple:
    """Verify that checkfile corresponds to the given source checksum.

    :param source_checksum: Source checksum in algorithm/hash format.
    :param checkfile: The file to calculate the sum for with the algorithm
        defined in source_checksum.

    :return: A tuple consisting of the algorithm and the hash.

    :raise ValueError: If source_checksum is not of the form algorithm/hash.
    :raise ChecksumMismatch: If checkfile does not match the expected hash
        calculated with the algorithm defined in source_checksum.
    """
    algorithm, digest = split_checksum(source_checksum)

    calculated_digest = file_utils.calculate_hash(checkfile, algorithm=algorithm)
    if digest != calculated_digest:
        raise errors.ChecksumMismatch(expected=digest, obtained=calculated_digest)

    return (algorithm, digest)
