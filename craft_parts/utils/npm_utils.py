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
import shlex
from glob import escape
from pathlib import Path
from textwrap import dedent
from typing import Any, cast


def _get_npm_basename(pkg_name: str) -> str:
    # scoped packages eg. @scope/my-package
    # are packed as scope-my-package-version.tgz
    if pkg_name.startswith("@"):
        scope, name = pkg_name[1:].split("/", 1)
        return f"{scope}-{name}"
    return pkg_name


def _find_tarballs(
    dependencies: dict[str, str], cache_dir: Path
) -> list[tuple[str, str, list[str]]]:
    """Find tarballs in cache directory.

    Returns a list of (dependency, specified_version, available_versions)
    """
    found: list[tuple[str, str, list[str]]] = []

    for dep, specified_version in dependencies.items():
        basename = _get_npm_basename(dep)
        if not (tarballs := sorted(cache_dir.glob(f"{escape(basename)}-*.tgz"))):
            raise RuntimeError(
                f"Error: could not resolve dependency '{dep} ({specified_version})'"
            )

        available_versions = [
            t.name.removeprefix(f"{basename}-").removesuffix(".tgz") for t in tarballs
        ]
        found.append((basename, specified_version, available_versions))

    return found


def _read_pkg(pkg_path: Path) -> dict[str, Any]:
    """Read and return contents of json file."""
    if not pkg_path.exists():
        raise RuntimeError(f"Error: could not find '{pkg_path}'.")
    with pkg_path.open() as f:
        return cast(dict[str, Any], json.load(f))


def _write_pkg(pkg_path: Path, pkg: dict[str, Any]) -> None:
    """Write json file."""
    with pkg_path.open("w") as f:
        json.dump(pkg, f)


def _get_install_dependencies_commands(
    dependencies: dict[str, Any], cache_dir: Path
) -> list[str]:
    deps_to_resolve = _find_tarballs(dependencies, cache_dir=cache_dir)
    cmd: list[str] = [
        dedent(
            """\
            # find semver.js bundled with node
            SEMVER_BIN=""
            NODE_LIBS="$(dirname "$(dirname "$(realpath "$(command -v node)")")")/lib/node_modules"
            if [ -f "$NODE_LIBS/npm/node_modules/semver/bin/semver.js" ]; then
                # semver.js path in snap
                SEMVER_BIN="$NODE_LIBS/npm/node_modules/semver/bin/semver.js"
            elif [ -f "/usr/share/nodejs/semver/bin/semver.js" ]; then
                # semver.js path in deb pkg
                SEMVER_BIN="/usr/share/nodejs/semver/bin/semver.js"
            fi

            if [ -z "$SEMVER_BIN" ]; then
                echo "Error: semver.js not found" >&2
                exit 1
            fi"""
        )
    ]

    cmd.append("TARBALLS=")
    for dependency, specified_version, available_versions in deps_to_resolve:
        cmd.append(
            dedent(
                f"""\
                # find version that satisfies {dependency} ({specified_version})
                BEST_VERSION=$("$SEMVER_BIN" -r {shlex.quote(specified_version)} {" ".join(available_versions)} | tail -1)
                if [ -z "$BEST_VERSION" ]; then
                    echo "Error: could not resolve dependency '{dependency} ({specified_version})'" >&2
                    exit 1
                fi
                TARBALLS="$TARBALLS {cache_dir}/{dependency}-$BEST_VERSION.tgz\""""
            )
        )

    # all tarballs need to be included in one command
    # or npm will try to search registry
    cmd.append("npm install --offline --include=dev --no-package-lock $TARBALLS")
    return cmd


def get_install_from_local_tarballs_commands(
    pkg_path: Path, bundled_pkg_path: Path, cache_dir: Path
) -> list[str]:
    """Return a list of commands to install dependencies required by self-contained builds."""
    pkg = _read_pkg(pkg_path)
    dependencies = pkg.get("dependencies", {})
    dev_dependencies = pkg.get("devDependencies", {})

    if all_dependencies := {**dependencies, **dev_dependencies}:
        # if dependencies are installed from local tarballs,
        # npm rewrites package.json with { dep: file:tarball-path } for each dep
        # on `npm install`, resulting in a corrupted tarball after `npm pack`.
        # overwrite package.json after install command and before packing

        # first modify package.json to bundle non-dev dependencies with tarball
        # so that npm doesn't search registry when subsequent parts install this tarball
        if dependencies:
            pkg["bundledDependencies"] = list(
                {*pkg.get("bundledDependencies", []), *dependencies}
            )
        # write a copy of package.json without tarball paths and with bundled dependencies
        bundled_pkg_path.parent.mkdir(parents=True, exist_ok=True)
        _write_pkg(bundled_pkg_path, pkg)

        # get commands to install tarballs from local directory
        cmd = _get_install_dependencies_commands(
            dependencies=all_dependencies,
            cache_dir=cache_dir,
        )

        # add command to overwrite package.json without tarball paths
        cmd.append(f"cp {bundled_pkg_path} package.json")
        return cmd
    return []
