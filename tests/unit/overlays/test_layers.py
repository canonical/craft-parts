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
from craft_parts.overlays.layers import LayerHash, LayerStateManager
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

    def test_hex_hash_bytes(self):
        value = bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        h = LayerHash(value)
        assert h.digest == value
        assert h.hex() == "0a141e28323c46505a64"

    @pytest.mark.parametrize(
        ("pkgs", "files", "script", "result"),
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
        h1 = LayerHash.for_part(p1, previous_layer_hash=LayerHash(b""))
        assert h1.hex() == result

        h2 = LayerHash.for_part(p1, previous_layer_hash=h1)
        assert h2.hex() != result

    def test_previous_hash(self):
        p1 = Part("p1", {"overlay-packages": [], "overlay": [], "overlay-script": None})
        h1 = LayerHash.for_part(p1, previous_layer_hash=LayerHash(b""))
        assert h1.hex() == "80324ed2458e5d51e851972d092a0996dc038e8b"

        h2 = LayerHash.for_part(p1, previous_layer_hash=h1)
        assert h2.hex() == "bb6d57381ec9fb85207c85b865ef6d709930f291"

    def test_load(self, new_dir):
        hash_file = Path("parts/p1/state/layer_hash")
        hash_file.parent.mkdir(parents=True)
        hash_file.write_text(b"some value".hex())

        p1 = Part("p1", {})
        h = LayerHash.load(part=p1)
        assert h is not None
        assert h.hex() == "736f6d652076616c7565"

    def test_load_missing_file(self, new_dir):
        p1 = Part("p1", {})
        h = LayerHash.load(p1)
        assert h is None

    def test_save(self, new_dir):
        Path("parts/p1/state").mkdir(parents=True)
        p1 = Part("p1", {})
        h = LayerHash(b"some value")
        h.save(part=p1)
        assert Path("parts/p1/state/layer_hash").read_text() == "736f6d652076616c7565"


@pytest.mark.usefixtures("new_dir")
class TestLayerStateManager:
    """Verify in-memory layer state management operations."""

    def test_get_layer_hash(self):
        p1 = Part("p1", {})
        p2 = Part("p2", {})
        base_layer_hash = LayerHash(b"base hash value")

        Path("parts/p1/state").mkdir(parents=True)
        layer_hash = LayerHash(
            bytes.fromhex("a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f")
        )
        layer_hash.save(p1)

        lsm = LayerStateManager([p1, p2], base_layer_hash)
        p1_layer_hash = lsm.get_layer_hash(p1)
        assert p1_layer_hash is not None
        assert p1_layer_hash.hex() == "a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f"

        p2_layer_hash = lsm.get_layer_hash(p2)
        assert p2_layer_hash is None

    def test_set_layer_hash(self):
        p1 = Part("p1", {})
        base_layer_hash = LayerHash(b"base hash value")

        lsm = LayerStateManager([p1], base_layer_hash)
        assert lsm.get_layer_hash(p1) is None

        layer_hash = LayerHash(
            bytes.fromhex("a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f")
        )
        lsm.set_layer_hash(p1, layer_hash)

        p1_layer_hash = lsm.get_layer_hash(p1)
        assert p1_layer_hash is not None
        assert p1_layer_hash.hex() == "a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f"

    @pytest.mark.parametrize(
        ("params", "digest"),
        [
            ({}, "a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f"),
            ({"overlay-script": "true"}, "fa8a0be828daebe4fd503d14fa9d6307ae0b01ae"),
            ({"overlay-packages": ["pkg"]}, "1d1f4f14a6809e389bdb6c6d0fb58fa5491c7981"),
            ({"overlay": ["/etc"]}, "b4d14ee52c4ba9c5d5c7610c5e2bce06f2f34b2b"),
        ],
    )
    def test_compute_layer_hash(self, params, digest):
        p1 = Part("p1", params)
        base_layer_hash = LayerHash(b"base hash value")

        lsm = LayerStateManager([p1], base_layer_hash)
        assert lsm.compute_layer_hash(p1).hex() == digest

    @pytest.mark.parametrize(
        ("params", "digest"),
        [
            ({}, "a15e326327c3456bc5547a69fe2996bcf8088cba"),
            ({"overlay-script": "true"}, "a992882dc823bde22d93b0fe4ea6282926b5cfa9"),
            ({"overlay-packages": ["pkg"]}, "c890ac631a1cde929edefb1b27b10d9ba848d548"),
            ({"overlay": ["/etc"]}, "c1b0caeabdfc607110dbcbb1c58a320127b61622"),
        ],
    )
    def test_compute_layer_hash_new_base(self, params, digest):
        p1 = Part("p1", params)
        base_layer_hash = LayerHash(b"other base hash value")

        lsm = LayerStateManager([p1], base_layer_hash)
        assert lsm.compute_layer_hash(p1).hex() == digest

    def test_compute_layer_hash_multiple_parts(self):
        p1 = Part("p1", {})
        p2 = Part("p2", {})
        base_layer_hash = LayerHash(b"base hash value")

        layer_hash = LayerHash(
            bytes.fromhex("a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f")
        )

        lsm = LayerStateManager([p1, p2], base_layer_hash)
        lsm.set_layer_hash(p1, layer_hash)

        p2_layer_hash = lsm.compute_layer_hash(p2)
        assert p2_layer_hash.hex() == "c6e659c5a430c093a120bb17868ade39e91e00b8"

    def test_compute_layer_hash_multiple_parts_new_base(self):
        p1 = Part("p1", {})
        p2 = Part("p2", {})
        base_layer_hash = LayerHash(b"other base hash value")

        layer_hash = LayerHash(
            bytes.fromhex("a15e326327c3456bc5547a69fe2996bcf8088cba")
        )

        lsm = LayerStateManager([p1, p2], base_layer_hash)
        lsm.set_layer_hash(p1, layer_hash)

        p2_layer_hash = lsm.compute_layer_hash(p2)
        assert p2_layer_hash.hex() == "c522dd71ef33a7eee9b8122ff8f4482152a99a12"

    def test_get_overlay_hash(self):
        p1 = Part("p1", {})
        p2 = Part("p2", {})
        base_layer_hash = LayerHash(b"base hash value")

        p1_layer_hash = LayerHash(
            bytes.fromhex("a42a1d8ac7fdcfc4752e28aba0b0ee905e7cf96f")
        )
        p2_layer_hash = LayerHash(
            bytes.fromhex("c6e659c5a430c093a120bb17868ade39e91e00b8")
        )

        lsm = LayerStateManager([p1, p2], base_layer_hash)
        lsm.set_layer_hash(p1, p1_layer_hash)
        lsm.set_layer_hash(p2, p2_layer_hash)

        assert lsm.get_overlay_hash() == p2_layer_hash.digest
