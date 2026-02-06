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

"""Utility functions for NPM plugin."""

import json
from glob import escape
from pathlib import Path
from typing import Any, cast


def _get_npm_basename(pkg_name: str) -> str:
    # scoped packages eg. @comanpy/my-package
    # are packed as company-my-package-version.tgz
    if pkg_name.startswith("@"):
        scope, name = pkg_name[1:].split("/", 1)
        return f"{scope}-{name}"
    return pkg_name


def find_tarballs(
    dependencies: dict[str, str], cache_dir: Path
) -> list[tuple[str, str, list[str]]]:
    """Find tarballs in cache directory.

    Returns a list of (dependency, specified_version, available_versions)
    """
    needs_resolution: list[tuple[str, str, list[str]]] = []

    for dep, specified_version in dependencies.items():
        basename = _get_npm_basename(dep)
        if not (tarballs := sorted(cache_dir.glob(f"{escape(basename)}-*.tgz"))):
            raise RuntimeError(
                f"Error: could not resolve dependency '{dep} ({specified_version})'"
            )

        available_versions = [
            t.name.removeprefix(f"{basename}-").removesuffix(".tgz") for t in tarballs
        ]
        needs_resolution.append((basename, specified_version, available_versions))

    return needs_resolution


def read_pkg(pkg_path: Path) -> dict[str, Any]:
    """Read and return contents of json file."""
    if not pkg_path.exists():
        raise RuntimeError(f"Error: could not find '{pkg_path}'.")
    with pkg_path.open() as f:
        return cast(dict[str, Any], json.load(f))


def write_pkg(pkg_path: Path, pkg: dict[str, Any]) -> None:
    """Write json file."""
    with pkg_path.open("w") as f:
        json.dump(pkg, f)
