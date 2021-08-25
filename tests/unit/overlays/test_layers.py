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

from pathlib import Path

import pytest

from craft_parts.overlays.layers import LayerHash
from craft_parts.parts import Part


class TestLayerHash:
    """Verify LayerHash definition and operations."""

    def test_layerhash_repr(self):
        h = LayerHash(b"some value")
        assert f"{h!r}" == "736f6d652076616c7565"

    def test_layerhash_eq(self):
        h1 = LayerHash(b"some value")
        h2 = LayerHash(b"some value")
        h3 = LayerHash(b"other value")
        assert h1 == h2
        assert h1 != h3

    def test_hex_bytes(self):
        value = bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        h = LayerHash(value)
        assert h.hex() == "0a141e28323c46505a64"
        assert h.bytes() == value

    @pytest.mark.parametrize(
        "pkgs,files,script,result",
        [
            ([], [], None, "80324ed2458e5d51e851972d092a0996dc038e8b"),
            ([], ["*"], None, "6554e32fa718d54160d0511b36f81458e4cb2357"),
            ([], [], "*", "8d272addf312552ba12cd7b4dd89c4d9544366a7"),
            ([], ["bin"], None, "0aeef6012aca34bf245609066ae16cb477d22f42"),
            (["bin"], [], None, "9aad6e7062ab06181086b9c27aa3013d892adc34"),
            (["pkg"], ["*"], None, "ac0ab0b4ff2bbbdd362a3719bf8311f3d73d43bc"),
            ([], ["*"], "ls", "9dd8cfd54b554c3a23858ce9ef717f23dd7cae7b"),
        ],
    )
    def test_compute(self, pkgs, files, script, result):
        p1 = Part(
            "p1", {"overlay-packages": pkgs, "overlay": files, "overlay-script": script}
        )
        h = LayerHash.for_part(p1, previous_layer_hash=LayerHash())
        assert h.hex() == result

    def test_load(self, new_dir):
        hash_file = Path("parts/p1/state/layer_hash")
        hash_file.parent.mkdir(parents=True)
        hash_file.write_text(b"some value".hex())

        p1 = Part("p1", {})
        h = LayerHash.load(part=p1)
        assert h.hex() == "736f6d652076616c7565"

    def test_load_missing_file(self, new_dir):
        p1 = Part("p1", {})
        h = LayerHash.load(p1)
        assert h.hex() == ""

    def test_save(self, new_dir):
        Path("parts/p1/state").mkdir(parents=True)
        p1 = Part("p1", {})
        h = LayerHash(b"some value")
        h.save(part=p1)
        assert Path("parts/p1/state/layer_hash").read_text() == "736f6d652076616c7565"
