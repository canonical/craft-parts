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

import os
import stat
from pathlib import Path
from textwrap import dedent

import pytest
from craft_parts.packages.base import DummyRepository
from craft_parts.packages.normalize import fix_pkg_config, normalize


@pytest.fixture
def pkg_config_file():
    """Fixture for writing a pkg-config (.pc) files."""

    def _pkg_config_file(filename: Path, prefix: str) -> None:
        """Writes a pkg-config file.

        :param filename: filename of pkg-config file
        :param prefix: value of prefix parameter
        """
        with open(filename, "w", encoding="utf-8") as file:
            file.write(
                dedent(
                    f"""\
                    prefix={prefix}
                    exec_prefix=${{prefix}}
                    libdir=${{prefix}}/lib
                    includedir=${{prefix}}/include

                    Name: granite
                    Description: elementary\'s Application Framework
                    Version: 0.4
                    Libs: -L${{libdir}} -lgranite
                    Cflags: -I${{includedir}}/granite
                    Requires: cairo gee-0.8 glib-2.0 gio-unix-2.0 gobject-2.0
                    """
                )
            )

    return _pkg_config_file


@pytest.fixture
def expected_pkg_config_content():
    """Returns a string containing the expected content of the pkg-config fixture."""

    def _expected_pkg_config_content(prefix: str) -> str:
        """Returns the expected contents of a pkg-config file.

        :param prefix: value of the prefix parameter
        """
        return dedent(
            f"""\
            prefix={prefix}
            exec_prefix=${{prefix}}
            libdir=${{prefix}}/lib
            includedir=${{prefix}}/include

            Name: granite
            Description: elementary's Application Framework
            Version: 0.4
            Libs: -L${{libdir}} -lgranite
            Cflags: -I${{includedir}}/granite
            Requires: cairo gee-0.8 glib-2.0 gio-unix-2.0 gobject-2.0
            """
        )

    return _expected_pkg_config_content


@pytest.mark.parametrize(
    "tc",
    [
        [  # fix_xml2_config
            {
                "path": os.path.join("root", "usr", "bin", "xml2-config"),
                "content": "prefix=/usr/foo",
                "expected": "prefix=root/usr/foo",
            }
        ],
        [  # no_fix_xml2_config
            {
                "path": os.path.join("root", "usr", "bin", "xml2-config"),
                "content": "prefix=/foo",
                "expected": "prefix=/foo",
            }
        ],
        [  # fix_xslt_config
            {
                "path": os.path.join("root", "usr", "bin", "xslt-config"),
                "content": "prefix=/usr/foo",
                "expected": "prefix=root/usr/foo",
            }
        ],
        [  # no_fix_xslt_config
            {
                "path": os.path.join("root", "usr", "bin", "xslt-config"),
                "content": "prefix=/foo",
                "expected": "prefix=/foo",
            }
        ],
        [  # fix_xml2_xslt_config
            {
                "path": os.path.join("root", "usr", "bin", "xml2-config"),
                "content": "prefix=/usr/foo",
                "expected": "prefix=root/usr/foo",
            },
            {
                "path": os.path.join("root", "usr", "bin", "xslt-config"),
                "content": "prefix=/usr/foo",
                "expected": "prefix=root/usr/foo",
            },
        ],
        [  # no_fix_xml2_xslt_config
            {
                "path": os.path.join("root", "usr", "bin", "xml2-config"),
                "content": "prefix=/foo",
                "expected": "prefix=/foo",
            },
            {
                "path": os.path.join("root", "usr", "bin", "xslt-config"),
                "content": "prefix=/foo",
                "expected": "prefix=/foo",
            },
        ],
    ],
)
@pytest.mark.usefixtures("new_dir")
class TestFixXmlTools:
    """Check the normalization of pathnames in XML tools."""

    def test_fix_xmltools(self, tc):
        for test_file in tc:
            path = test_file["path"]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(test_file["content"])

        normalize(Path("root"), repository=DummyRepository)

        for test_file in tc:
            with open(test_file["path"]) as f:
                assert f.read() == test_file["expected"]


@pytest.mark.usefixtures("new_dir")
class TestFixShebang:
    """Check the normalization of script interpreter lines."""

    scenarios = [
        (
            "python bin dir",
            {
                "file_path": os.path.join("root", "bin", "a"),
                "content": "#!/usr/bin/python\nimport this",
                "expected": "#!/usr/bin/env python\nimport this",
            },
        ),
        (
            "python3 bin dir",
            {
                "file_path": os.path.join("root", "bin", "d"),
                "content": "#!/usr/bin/python3\nimport this",
                "expected": "#!/usr/bin/env python3\nimport this",
            },
        ),
        (
            "sbin dir",
            {
                "file_path": os.path.join("root", "sbin", "b"),
                "content": "#!/usr/bin/python\nimport this",
                "expected": "#!/usr/bin/env python\nimport this",
            },
        ),
        (
            "usr/bin dir",
            {
                "file_path": os.path.join("root", "usr", "bin", "c"),
                "content": "#!/usr/bin/python\nimport this",
                "expected": "#!/usr/bin/env python\nimport this",
            },
        ),
        (
            "usr/sbin dir",
            {
                "file_path": os.path.join("root", "usr", "sbin", "d"),
                "content": "#!/usr/bin/python\nimport this",
                "expected": "#!/usr/bin/env python\nimport this",
            },
        ),
        (
            "opt/bin dir",
            {
                "file_path": os.path.join("root", "opt", "bin", "e"),
                "content": "#!/usr/bin/python\nraise Exception()",
                "expected": "#!/usr/bin/env python\nraise Exception()",
            },
        ),
    ]

    def test_fix_shebang(self):
        for _, data in self.scenarios:
            os.makedirs(os.path.dirname(data["file_path"]), exist_ok=True)
            with open(data["file_path"], "w") as fd:
                fd.write(data["content"])

        normalize(Path("root"), repository=DummyRepository)

        for _, data in self.scenarios:
            with open(data["file_path"]) as fd:
                assert fd.read() == data["expected"]


@pytest.mark.usefixtures("new_dir")
class TestRemoveUselessFiles:
    """Check the removal of unnecessary files."""

    def create(self, file_path: str) -> str:
        path = os.path.join("root", file_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()

        return path

    def test_remove(self):
        paths = [
            self.create(p)
            for p in [
                os.path.join("usr", "lib", "python3.5", "sitecustomize.py"),
                os.path.join("usr", "lib", "python2.7", "sitecustomize.py"),
                os.path.join("usr", "lib", "python", "sitecustomize.py"),
            ]
        ]
        normalize(Path("root"), repository=DummyRepository)

        for p in paths:
            assert os.path.exists(p) is False

    def test_no_remove(self):
        path = self.create(os.path.join("opt", "python3.5", "sitecustomize.py"))
        normalize(Path("root"), repository=DummyRepository)

        assert os.path.exists(path)


class TestFixPkgConfig:
    """Check the normalization of pkg-config files."""

    @pytest.mark.parametrize(
        ("prefix", "fixed_prefix"),
        [
            # possible prefixes from snaps built via launchpad
            ("/build/mir-core20/stage", ""),
            ("/build/mir-core20/stage/usr", "/usr"),
            ("/build/stage/stage", ""),
            ("/build/stage/stage/usr/stage", "/usr/stage"),
            ("/build/my-stage-snap/stage", ""),
            ("/build/my-stage-snap/stage/usr/stage", "/usr/stage"),
            # possible prefixes from snaps built via a provider
            ("/root/stage", ""),
            ("/root/stage/usr", "/usr"),
            ("/root/stage/usr/stage", "/usr/stage"),
        ],
    )
    def test_fix_pkg_config_trim_prefix_from_snap(
        self,
        tmpdir,
        prefix,
        fixed_prefix,
        pkg_config_file,
        expected_pkg_config_content,
    ):
        """Verify prefixes from snaps are trimmed."""
        pc_file = tmpdir / "my-file.pc"
        pkg_config_file(pc_file, prefix)

        fix_pkg_config(tmpdir, pc_file)

        assert pc_file.read_text(encoding="utf-8") == expected_pkg_config_content(
            f"{tmpdir}{fixed_prefix}"
        )

    @pytest.mark.parametrize(
        ("prefix", "prefix_trim", "fixed_prefix"),
        [
            ("/test/build/dir/stage", "/test/build/dir/stage", ""),
            ("/test/build/dir/stage/usr", "/test/build/dir/stage", "/usr"),
            ("/fake/dir/1", "/fake/dir/2", "/fake/dir/1"),
        ],
    )
    def test_fix_pkg_config_trim_prefix(
        self,
        tmpdir,
        prefix,
        prefix_trim,
        fixed_prefix,
        pkg_config_file,
        expected_pkg_config_content,
    ):  # pylint: disable=too-many-arguments
        """Verify prefixes from the `prefix_trim` argument are trimmed."""
        pc_file = tmpdir / "my-file.pc"
        pkg_config_file(pc_file, prefix)

        fix_pkg_config(tmpdir, pc_file, Path(prefix_trim))

        assert pc_file.read_text(encoding="utf-8") == expected_pkg_config_content(
            f"{tmpdir}{fixed_prefix}"
        )

    @pytest.mark.parametrize(
        "prefix",
        [
            "",
            "/",
            "/usr",
            "/build/test/test/stage",
            "/root/test/stage",
            "/test/path/stage",
            "/test/path/stage/usr",
            "/test/path/stage/usr/stage",
        ],
    )
    def test_fix_pkg_config_no_trim(
        self,
        tmpdir,
        prefix,
        pkg_config_file,
        expected_pkg_config_content,
    ):
        """Verify valid prefixes are not trimmed."""
        pc_file = tmpdir / "my-file.pc"
        pkg_config_file(pc_file, prefix)

        fix_pkg_config(tmpdir, pc_file)

        assert pc_file.read_text(encoding="utf-8") == expected_pkg_config_content(
            f"{tmpdir}{prefix}"
        )

    def test_normalize_fix_pkg_config(
        self, tmpdir, pkg_config_file, expected_pkg_config_content
    ):
        """Verify normalization fixes pkg-config files."""
        pc_file = tmpdir / "my-file.pc"
        pkg_config_file(pc_file, "/root/stage/usr")
        normalize(tmpdir, repository=DummyRepository)

        assert pc_file.read_text(encoding="utf-8") == expected_pkg_config_content(
            f"{tmpdir}/usr"
        )

    def test_fix_pkg_config_is_dir(self, tmpdir):
        """Verify directories ending in .pc do not raise an error."""
        pc_file = tmpdir / "granite.pc"
        pc_file.mkdir()

        # this shouldn't crash
        normalize(tmpdir, repository=DummyRepository)


@pytest.mark.parametrize(
    ("src", "dst", "result"),
    [
        ("a", "rel-to-a", "a"),
        ("/a", "abs-to-a", "a"),
        ("/1", "a/abs-to-1", "../1"),
    ],
)
class TestFixSymlinks:
    """Check the normalization of symbolic links."""

    def test_fix_symlinks(self, src, dst, result, new_dir):
        os.makedirs("a")
        open("1", mode="w").close()

        os.symlink(src, dst)
        normalize(new_dir, repository=DummyRepository)

        assert os.readlink(dst) == result


class TestFixSUID:
    """Check the normalization of suid bits in file mode."""

    @pytest.mark.parametrize(
        ("key", "test_mod", "expected_mod"),
        [
            ("suid_file", 0o4765, 0o0765),
            ("guid_file", 0o2777, 0o0777),
            ("suid_guid_file", 0o6744, 0o0744),
            ("suid_guid_sticky_file", 0o7744, 0o1744),
        ],
    )
    def test_mode(self, key, test_mod, expected_mod, tmpdir):
        f = os.path.join(tmpdir, key)
        open(f, mode="w").close()
        os.chmod(f, test_mod)

        normalize(tmpdir, repository=DummyRepository)

        assert stat.S_IMODE(os.stat(f).st_mode) == expected_mod
