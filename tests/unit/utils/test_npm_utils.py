# Copyright 2026 Canonical Ltd.
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

"""Unit tests for the npm plugin utilities."""

import json

import pytest
from craft_parts.utils.npm_utils import get_install_from_local_tarballs_commands


def test_get_install_commands_with_dependencies(tmp_path):
    pkg_path = tmp_path / "package.json"
    pkg_path.write_text('{"dependencies": {"my-dep": "^1.0.0"}}')
    bundled_pkg_path = tmp_path / ".parts" / "package.bundled.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "my-dep-1.0.0.tgz").touch()

    cmd = get_install_from_local_tarballs_commands(
        pkg_path, bundled_pkg_path, cache_dir
    )

    assert "SEMVER_BIN" in cmd[0]
    assert cmd[1] == "TARBALLS="
    assert "my-dep-$BEST_VERSION.tgz" in cmd[2]
    assert cmd[-2:] == [
        "npm install --offline --include=dev --no-package-lock $TARBALLS",
        f"cp {bundled_pkg_path} package.json",
    ]

    bundled = json.loads(bundled_pkg_path.read_text())
    assert bundled["bundledDependencies"] == ["my-dep"]


def test_get_install_commands_multiple_versions(tmp_path):
    pkg_path = tmp_path / "package.json"
    pkg_path.write_text('{"dependencies": {"my-dep": "^1.0.0"}}')
    bundled_pkg_path = tmp_path / ".parts" / "package.bundled.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "my-dep-1.0.0.tgz").touch()
    (cache_dir / "my-dep-2.0.0.tgz").touch()

    cmd = get_install_from_local_tarballs_commands(
        pkg_path, bundled_pkg_path, cache_dir
    )

    assert "'^1.0.0' 1.0.0 2.0.0" in cmd[2]


def test_get_install_commands_with_dev_dependencies(tmp_path):
    pkg_path = tmp_path / "package.json"
    pkg_path.write_text(
        '{"dependencies": {"my-dep": "^1.0.0"}, "devDependencies": {"dev-dep": "~2.0.0"}}'
    )
    bundled_pkg_path = tmp_path / ".parts" / "package.bundled.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "my-dep-1.0.0.tgz").touch()
    (cache_dir / "dev-dep-2.0.0.tgz").touch()

    cmd = get_install_from_local_tarballs_commands(
        pkg_path, bundled_pkg_path, cache_dir
    )

    assert "my-dep" in cmd[2]
    assert "dev-dep" in cmd[3]

    bundled = json.loads(bundled_pkg_path.read_text())
    assert bundled["bundledDependencies"] == ["my-dep"]


def test_get_install_commands_only_dev_dependencies(tmp_path):
    pkg_path = tmp_path / "package.json"
    pkg_path.write_text('{"devDependencies": {"dev-dep": "~2.0.0"}}')
    bundled_pkg_path = tmp_path / ".parts" / "package.bundled.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "dev-dep-2.0.0.tgz").touch()

    cmd = get_install_from_local_tarballs_commands(
        pkg_path, bundled_pkg_path, cache_dir
    )

    assert "dev-dep" in cmd[2]

    bundled = json.loads(bundled_pkg_path.read_text())
    # there should be no bundled dependencies
    assert "bundledDependencies" not in bundled


def test_get_install_commands_no_dependencies(tmp_path):
    pkg_path = tmp_path / "package.json"
    pkg_path.write_text('{"name": "test"}')
    bundled_pkg_path = tmp_path / ".parts" / "package.bundled.json"
    cache_dir = tmp_path / "cache"

    cmd = get_install_from_local_tarballs_commands(
        pkg_path, bundled_pkg_path, cache_dir
    )

    assert cmd == []


def test_find_tarballs_missing_raises(tmp_path):
    pkg_path = tmp_path / "package.json"
    pkg_path.write_text('{"dependencies": {"missing-dep": "^1.0.0"}}')
    bundled_pkg_path = tmp_path / ".parts" / "package.bundled.json"
    cache_dir = tmp_path / "cache"
    with pytest.raises(RuntimeError, match="could not resolve dependency 'missing-dep"):
        get_install_from_local_tarballs_commands(pkg_path, bundled_pkg_path, cache_dir)
