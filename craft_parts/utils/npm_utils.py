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


def _find_tarballs_dict(
    dependencies: dict[str, str], cache_dir: Path
) -> dict[str, list[str]]:
    """Find tarballs in cache directory.

    Returns a dictionary of {"dependency": [available_versions]}
    """
    found: dict[str, list[str]] = {}

    for dep, specified_version in dependencies.items():
        basename = _get_npm_basename(dep)
        if not (tarballs := sorted(cache_dir.glob(f"{escape(basename)}-*.tgz"))):
            raise RuntimeError(
                f"Error: could not resolve dependency '{dep} ({specified_version})'"
            )

        available_versions = [
            t.name.removeprefix(f"{basename}-").removesuffix(".tgz") for t in tarballs
        ]

        found[dep] = available_versions

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


def _find_semver_command() -> str:
    return dedent(
        """\
            # find semver.js bundled with node
            SEMVER_BIN=""
            SNAP_NODE_LIBS="/snap/node/current/lib/node_modules"
            if [ -f "$SNAP_NODE_LIBS/npm/node_modules/semver/bin/semver.js" ]; then
                # semver.js path in snap
                SEMVER_BIN="$SNAP_NODE_LIBS/npm/node_modules/semver/bin/semver.js"
            elif [ -f "/usr/share/nodejs/semver/bin/semver.js" ]; then
                # semver.js path in deb pkg
                SEMVER_BIN="/usr/share/nodejs/semver/bin/semver.js"
            fi

            if [ -z "$SEMVER_BIN" ]; then
                echo "Error: semver.js not found" >&2
                exit 1
            fi"""
    )


def _find_best_version_command(
    dependency: str, specified_version: str, available_versions: list[str]
) -> str:
    return f"""
            # find version that satisfies {dependency} ({specified_version})
            BEST_VERSION=$("$SEMVER_BIN" -r {shlex.quote(specified_version)} {" ".join(available_versions)} | tail -1)
            if [ -z "$BEST_VERSION" ]; then
                echo "Error: could not resolve dependency '{dependency} ({specified_version})'" >&2
                exit 1
            fi"""


def _install_dependencies_commands(
    dependencies: dict[str, Any],
    cache_dir: Path,
    available_tarballs: dict[str, list[str]],
) -> list[str]:
    if not dependencies:
        return []

    cmd: list[str] = ["TARBALLS="]
    for dependency, specified_version in dependencies.items():
        cmd.append(
            dedent(
                f"""\
                {_find_best_version_command(dependency, specified_version, available_tarballs[dependency])}
                TARBALLS="$TARBALLS {cache_dir}/{dependency}-$BEST_VERSION.tgz"
                """
            )
        )
    # all tarballs need to be included in one command
    # or npm will try to search registry
    cmd.append("npm install --offline --no-package-lock $TARBALLS")

    return cmd


def _install_dev_dependencies_commands(
    dev_dependencies: dict[str, Any],
    dev_npm_prefix: Path,
    cache_dir: Path,
    available_tarballs: dict[str, list[str]],
) -> list[str]:
    cmd: list[str] = []
    for dependency, specified_version in dev_dependencies.items():
        cmd.append(
            dedent(
                f"""\
                {_find_best_version_command(dependency, specified_version, available_tarballs[dependency])}
                npm install --offline -g --prefix {dev_npm_prefix} {cache_dir}/{dependency}-$BEST_VERSION.tgz
                """
            )
        )

    return cmd


def get_install_from_local_tarballs_commands(
    pkg_path: Path,
    bundled_pkg_path: Path,
    cache_dir: Path,
    dev_npm_prefix: Path,
    user_specified_dev_dependencies: list[str],
) -> list[str]:
    """Return a list of commands to install dependencies required by self-contained builds."""
    pkg = _read_pkg(pkg_path)
    dependencies = pkg.get("dependencies", {})
    pkg_dev_dependencies = pkg.get("devDependencies", {})
    dev_dependencies = {
        dep: pkg_dev_dependencies[dep] for dep in user_specified_dev_dependencies
    }
    if not (all_dependencies := {**dependencies, **dev_dependencies}):
        return []

    available_tarballs = _find_tarballs_dict(all_dependencies, cache_dir=cache_dir)
    cmd: list[str] = [_find_semver_command()]
    if dependencies:
        # if dependencies are installed from local tarballs,
        # npm rewrites package.json with { dep: file:tarball-path } for each dep
        # on `npm install`, resulting in a corrupted tarball after `npm pack`.
        # overwrite package.json after install command and before packing

        # first modify package.json to bundle non-dev dependencies with tarball
        # so that npm doesn't search registry when subsequent parts install this tarball
        pkg["bundledDependencies"] = list(
            {*pkg.get("bundledDependencies", []), *dependencies}
        )
        # get commands to install tarballs from local directory
        cmd.append("TARBALLS=")
        for dependency, specified_version in dependencies.items():
            cmd.append(
                dedent(
                    f"""\
                    {_find_best_version_command(dependency, specified_version, available_tarballs[dependency])}
                    TARBALLS="$TARBALLS {cache_dir}/{dependency}-$BEST_VERSION.tgz"
                    """
                )
            )
        # all tarballs need to be included in one command
        # or npm will try to search registry
        cmd.append("npm install --offline --no-package-lock $TARBALLS")

    # write a copy of package.json without tarball paths and with bundled dependencies
    bundled_pkg_path.parent.mkdir(parents=True, exist_ok=True)
    _write_pkg(bundled_pkg_path, pkg)

    for dependency, specified_version in dev_dependencies.items():
        cmd.append(
            dedent(
                f"""\
                {_find_best_version_command(dependency, specified_version, available_tarballs[dependency])}
                npm install --offline -g --prefix {dev_npm_prefix} {cache_dir}/{dependency}-$BEST_VERSION.tgz
                """
            )
        )

    # add command to overwrite package.json without tarball paths
    cmd.append(f"cp {bundled_pkg_path} package.json")
    return cmd
