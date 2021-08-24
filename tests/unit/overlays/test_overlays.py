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

from pathlib import Path

import pytest

from craft_parts.overlays import overlays


class TestHelpers:
    """OCI special files translation and verification."""

    def test_is_oci_opaque_dir(self, new_dir):
        dir1 = Path("dir1")
        dir1.mkdir()
        Path("dir1/.wh..wh..opq").touch()

        assert overlays.is_oci_opaque_dir(dir1)

    def test_is_oci_opaque_dir_nomarker(self, new_dir):
        dir1 = Path("dir1")
        dir1.mkdir()

        assert overlays.is_oci_opaque_dir(dir1) is False

    def test_is_oci_opaque_dir_symlink(self, new_dir):
        dir1 = Path("dir1")
        dir1.mkdir()
        Path("dir1/.wh..wh..opq").touch()

        dir2 = Path("dir2")
        dir2.symlink_to(dir1)

        assert overlays.is_oci_opaque_dir(dir1)
        assert overlays.is_oci_opaque_dir(dir2) is False

    @pytest.mark.parametrize(
        "name,oci_name", [("foo", ".wh.foo"), ("/path/foo", "/path/.wh.foo")]
    )
    def test_oci_whiteout(self, name, oci_name):
        assert overlays.oci_whiteout(Path(name)) == Path(oci_name)

    @pytest.mark.parametrize(
        "name,oci_name",
        [("foo", "foo/.wh..wh..opq"), ("/path/foo", "/path/foo/.wh..wh..opq")],
    )
    def test_oci_opaque_dir(self, name, oci_name):
        assert overlays.oci_opaque_dir(Path(name)) == Path(oci_name)

    def test_is_path_visible(self, new_dir):
        deepfile = Path("dir1/dir2/dir3/dir4/foo")
        deepfile.parent.mkdir(parents=True)
        deepfile.touch()
        assert overlays._is_path_visible(new_dir, deepfile)

    def test_is_path_visible_first_whited_out(self, new_dir):
        deepfile = Path("dir1/dir2/dir3/dir4/foo")
        Path(".wh.dir1").touch()
        assert overlays._is_path_visible(new_dir, deepfile) is False

    def test_is_path_visible_last_whited_out(self, new_dir):
        deepfile = Path("dir1/dir2/dir3/dir4/foo")
        Path("dir1/dir2/dir3").mkdir(parents=True)
        Path("dir1/dir2/dir3/.wh.dir4").touch()
        assert overlays._is_path_visible(new_dir, deepfile) is False

    def test_is_path_visible_first_opaque(self, new_dir):
        deepfile = Path("dir1/dir2/dir3/dir4/foo")
        deepfile.parent.mkdir(parents=True)
        Path("dir1/.wh..wh..opq").touch()
        assert overlays._is_path_visible(new_dir, deepfile) is False

    def test_is_path_visible_last_opaque(self, new_dir):
        deepfile = Path("dir1/dir2/dir3/dir4/foo")
        deepfile.parent.mkdir(parents=True)
        Path("dir1/dir2/dir3/dir4/.wh..wh..opq").touch()
        assert overlays._is_path_visible(new_dir, deepfile) is False


class TestVisibility:
    """File visibility in a directory layer."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        Path("srcdir").mkdir()
        Path("srcdir/a").touch()
        Path("srcdir/dir1").mkdir()
        Path("srcdir/dir1/b").touch()
        Path("srcdir/dir1/c").touch()
        Path("destdir").mkdir()

    def test_visible_in_layer(self, new_dir):
        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a", "dir1/b", "dir1/c"}
        assert dirs == {"dir1"}

    def test_visible_in_layer_whited_out_file(self, new_dir):
        Path("destdir/dir1").mkdir()
        Path("destdir/dir1/.wh.b").touch()

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a", "dir1/c"}
        assert dirs == set()

    def test_visible_in_layer_opaque_dir(self, new_dir):
        Path("destdir/dir1").mkdir()
        Path("destdir/dir1/.wh..wh..opq").touch()

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a"}
        assert dirs == set()

    def test_visible_in_layer_whiteout_in_opaque_dir(self, new_dir):
        Path("destdir/dir1").mkdir()
        Path("destdir/dir1/.wh..wh..opq").touch()
        Path("destdir/dir1/.wh.b").touch()

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a"}
        assert dirs == set()

    def test_visible_in_layer_symlink(self, new_dir):
        Path("srcdir/dir2").symlink_to("dir1")

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a", "dir1/b", "dir1/c", "dir2"}
        assert dirs == {"dir1"}

    def test_visible_in_layer_deep_file(self, new_dir):
        deepfile = Path("srcdir/dir2/dir3/dir4/d")
        deepfile.parent.mkdir(parents=True)
        deepfile.touch()

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a", "dir1/b", "dir1/c", "dir2/dir3/dir4/d"}
        assert dirs == {"dir1", "dir2", "dir2/dir3", "dir2/dir3/dir4"}

    def test_visible_in_layer_deep_file_whiteout_dir(self, new_dir):
        deepfile = Path("srcdir/dir2/dir3/dir4/d")
        deepfile.parent.mkdir(parents=True)
        deepfile.touch()

        Path("destdir/.wh.dir2").touch()

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a", "dir1/b", "dir1/c"}
        assert dirs == {"dir1"}

    def test_visible_in_layer_deep_file_opaque_dir(self, new_dir):
        deepfile = Path("srcdir/dir2/dir3/dir4/d")
        deepfile.parent.mkdir(parents=True)
        deepfile.touch()

        Path("destdir/dir2/dir3").mkdir(parents=True)
        Path("destdir/dir2/dir3/.wh..wh..opq").touch()

        files, dirs = overlays.visible_in_layer(Path("srcdir"), Path("destdir"))
        assert files == {"a", "dir1/b", "dir1/c"}
        assert dirs == {"dir1"}
