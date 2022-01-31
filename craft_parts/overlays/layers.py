# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""Layer management and helpers."""

import hashlib
import logging
from typing import Dict, List, Optional

from craft_parts.parts import Part

logger = logging.getLogger(__name__)


class LayerHash:
    """The layer validation hash for a part."""

    def __init__(self, layer_hash: bytes):
        self.digest = layer_hash

    def __repr__(self):
        return self.hex()

    def __eq__(self, other):
        if not isinstance(other, LayerHash):
            return False

        return self.digest == other.digest

    @classmethod
    def for_part(
        cls, part: Part, *, previous_layer_hash: Optional["LayerHash"]
    ) -> "LayerHash":
        """Obtain the validation hash for a part.

        :param part: The part being processed.
        :param previous_layer_hash: The validation hash of the previous
            layer in the overlay stack.

        :returns: The validation hash computed for the layer corresponding
            to the given part.
        """
        hasher = hashlib.sha1()
        if previous_layer_hash:
            hasher.update(previous_layer_hash.digest)
        for entry in part.spec.overlay_packages:
            hasher.update(entry.encode())
        digest = hasher.digest()

        hasher = hashlib.sha1()
        hasher.update(digest)
        for entry in part.spec.overlay_files:
            hasher.update(entry.encode())
        digest = hasher.digest()

        hasher = hashlib.sha1()
        hasher.update(digest)
        if part.spec.overlay_script:
            hasher.update(part.spec.overlay_script.encode())
        return cls(hasher.digest())

    @classmethod
    def load(cls, part: Part) -> Optional["LayerHash"]:
        """Read the part layer validation hash from persistent state.

        :param part: The part whose layer hash will be loaded.

        :return: A layer hash object containing the loaded validaton hash,
            or None if the file doesn't exist.
        """
        hash_file = part.part_state_dir / "layer_hash"
        if not hash_file.exists():
            return None

        with open(hash_file) as file:
            hex_string = file.readline()

        return cls(bytes.fromhex(hex_string))

    def save(self, part: Part) -> None:
        """Save the part layer validation hash to persistent storage.

        :param part: The part whose layer hash will be saved.
        """
        hash_file = part.part_state_dir / "layer_hash"
        hash_file.write_text(self.hex())

    def hex(self) -> str:
        """Return the current hash value as a hexadecimal string."""
        return self.digest.hex()


class LayerStateManager:
    """An in-memory layer state management helper for action planning.

    :param part_list: The list of parts in the project.
    :param base_layer_hash: The verification hash of the overlay base layer.
    """

    def __init__(self, part_list: List[Part], base_layer_hash: Optional[LayerHash]):
        self._part_list = part_list
        self._base_layer_hash = base_layer_hash

        self._layer_hash: Dict[str, Optional[LayerHash]] = {}
        for part in part_list:
            self.set_layer_hash(part, LayerHash.load(part))

    def get_layer_hash(self, part: Part) -> Optional[LayerHash]:
        """Obtain the layer hash for the given part."""
        return self._layer_hash.get(part.name)

    def set_layer_hash(self, part: Part, layer_hash: Optional[LayerHash]) -> None:
        """Store the value of the layer hash for the given part."""
        self._layer_hash[part.name] = layer_hash

    def compute_layer_hash(self, part: Part) -> LayerHash:
        """Calculate the layer validation hash for the given part.

        :param part: The part being processed.

        :return: The validation hash of the layer corresponding to the
            given part.
        """
        index = self._part_list.index(part)

        if index > 0:
            previous_layer_hash = self.get_layer_hash(self._part_list[index - 1])
        else:
            previous_layer_hash = self._base_layer_hash

        return LayerHash.for_part(part, previous_layer_hash=previous_layer_hash)

    def get_overlay_hash(self) -> bytes:
        """Obtain the overlay validation hash."""
        last_part = self._part_list[-1]
        overlay_hash = self.get_layer_hash(last_part)
        if not overlay_hash:
            return b""
        return overlay_hash.digest
