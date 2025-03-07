# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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
            ([], [], None, "de1b879d934299b3f03f0a5cdb99c50bdc5cb4ea"),
            ([], ["*"], None, "a3700a380077e2a4306b64628707ad87588040f2"),
            ([], [], "*", "44a97a466dc271278457e876811d29092d4d6548"),
            ([], ["bin"], None, "e8840727bd9f6c2f349fdfd5184ce020e3bb4b1a"),
            (["bin"], [], None, "38f0170996429f0e052ae7bb96503536ff5433cf"),
            (["pkg"], ["*"], None, "ac6c933ee9026a0138f55d02cb6a5f9825e6241f"),
            ([], ["*"], "ls", "c34c6c804be958015d3eeb08e48cb4f510db151a"),
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
        assert h1.hex() == "de1b879d934299b3f03f0a5cdb99c50bdc5cb4ea"

        h2 = LayerHash.for_part(p1, previous_layer_hash=h1)
        assert h2.hex() == "4f63b8db261be70583f8087b45751ba736245555"

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
            ({}, "3d8c26b77e6283c3e210c588ec19c987c7dc7a9f"),
            ({"overlay-script": "true"}, "b69cd7845011bfd85fdcd38e3ada4c089f6b2a05"),
            ({"overlay-packages": ["pkg"]}, "388f8ab69c396a8e5fffce327cf1f305d574f7ab"),
            ({"overlay": ["/etc"]}, "4e469622a748e0f443d3ff8a06e4a4d90705064f"),
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
            ({}, "4ed3533f46ecaade7ada8b4faa4d8bbd788d1dff"),
            ({"overlay-script": "true"}, "a1b8c832eb43b3ed644cd9f7b3c32f99878c51dd"),
            ({"overlay-packages": ["pkg"]}, "d970b40822b6fd7c431133bc054a61ad51ada1fe"),
            ({"overlay": ["/etc"]}, "969e90e8869a8ac6b5f5ec01ba4429d6e54766b0"),
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
        assert p2_layer_hash.hex() == "dd59cf89fc34b540c99ad85738b11b08db160e38"

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
        assert p2_layer_hash.hex() == "9376078c2087328a386b056b97ffa6c2a558daca"

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
