# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022,2024 Canonical Ltd.
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

"""The npm plugin."""

import json
import logging
import os
from pathlib import Path
import platform
import re
from textwrap import dedent
from typing import Any, Literal, cast

import requests
from overrides import override
from pydantic import model_validator
from typing_extensions import Self

from craft_parts.errors import InvalidArchitecture

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)

_NODE_ARCH_FROM_SNAP_ARCH = {
    "i386": "x86",
    "amd64": "x64",
    "armhf": "armv7l",
    "arm64": "arm64",
    "ppc64el": "ppc64le",
    "s390x": "s390x",
}
_NODE_ARCH_FROM_PLATFORM = {"x86_64": {"32bit": "x86", "64bit": "x64"}}


class NpmPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the npm plugin."""

    plugin: Literal["npm"] = "npm"

    # part properties required by the plugin
    npm_include_node: bool = False
    npm_node_version: str | None = None
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    @model_validator(mode="after")
    def node_version_defined(self) -> Self:
        """If npm-include-node is true, then npm-node-version must be defined."""
        if self.npm_include_node and not self.npm_node_version:
            raise ValueError("npm-node-version is required if npm-include-node is true")
        if self.npm_node_version and not self.npm_include_node:
            raise ValueError(
                "npm-node-version has no effect if npm-include-node is false"
            )
        return self


class NpmPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the npm plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build npm applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        options = cast(NpmPluginProperties, self._options)
        if options.npm_include_node:
            return

        for dependency in ["node", "npm"]:
            self.validate_dependency(
                dependency=dependency,
                plugin_name="npm",
                part_dependencies=part_dependencies,
            )


class NpmPlugin(Plugin):
    """A plugin for npm projects.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:
        - npm-include-node
          (bool; default: False)
          If true, download and include the node binary and its dependencies.
          If npm-include-node is true, then npm-node-version must be defined.

        - npm-node-version
          (str; default: None)
          Which version of node to download.
          Required if npm-include-node is set to true.
          The option accepts a NVM-style version string, you can specify:

            * exact version (e.g. "20.12.2")
            * major+minor version (e.g. "20.12")
            * major version (e.g. "20")
            * LTS code name (e.g. "lts/iron")
            * latest mainline version ("node")

          Note that "system" and "iojs" options are not supported.
    """

    properties_class = NpmPluginProperties
    validator_class = NpmPluginEnvironmentValidator

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._node_binary_path: str | None = None

    @staticmethod
    def _get_architecture() -> str:
        """Get system architecture, formatted for downloading node.

        :raise InvalidArchitecture: If the system architecture
        isn't compatible with node.
        """
        snap_arch = os.getenv("SNAP_ARCH")
        if snap_arch is not None:
            try:
                node_arch = _NODE_ARCH_FROM_SNAP_ARCH[snap_arch]
            except KeyError as error:
                raise InvalidArchitecture(arch_name=snap_arch) from error
        else:
            machine_type = platform.machine()
            architecture_type = platform.architecture()
            try:
                node_arch = _NODE_ARCH_FROM_PLATFORM[machine_type][architecture_type[0]]
            except KeyError as error:
                raise InvalidArchitecture(
                    arch_name=f"{machine_type} {architecture_type}"
                ) from error

        return node_arch

    @staticmethod
    def _fetch_node_release_index() -> list[dict[str, Any]]:
        """Fetch the list of Node.js releases.

        :return: The list of Node.js releases.
        """
        logging.info("Fetching Node.js release index...")
        resp = requests.get("https://nodejs.org/dist/index.json", timeout=10)
        resp.raise_for_status()
        versions: list[dict[str, Any]] = resp.json()
        return versions

    @staticmethod
    def _get_best_node_version(
        node_version: str | None, target_arch: str
    ) -> tuple[str, str]:
        """Get the best matching Node.js version using NVM-style version tags.

        :param node_version: The version of Node.js to match.
        :param target_arch: The target architecture.
        :return: The best matching node version and its remote file name.
        """
        logging.info(
            "Searching for Node.js version %s for %s ...", node_version, target_arch
        )
        versions = NpmPlugin._fetch_node_release_index()
        node_os_id = f"linux-{target_arch}"
        candidate = None
        if node_version is None or node_version == "node":
            # use the latest version if not specified
            candidate = versions[0]
        elif re.match(r"^\d+\.\d+\.\d+$", node_version):
            search_version = f"v{node_version}"
            # normal Node version
            for version in versions:
                if version.get("version") == search_version:
                    candidate = version
                    break
        elif node_version.isdecimal() or re.match(r"^\d+\.\d+$", node_version):
            # major-only or major.minor Node version
            search_string = f"v{node_version}."
            for version in versions:
                # search for the first version that matches the major version
                # and also contains a release for the architecture
                if version.get("version", "").startswith(search_string) and (
                    node_os_id in version.get("files", [])
                ):
                    candidate = version
                    break
        elif node_version.startswith("lts/"):
            # LTS code name
            node_version = node_version.replace("lts/", "", 1)
            lts_string = f"{node_version.capitalize()}"
            for version in versions:
                lts_version = version.get("lts", False)
                # like-wise, but search for the LTS version
                if (
                    lts_version
                    and lts_version == lts_string
                    and (node_os_id in version.get("files", []))
                ):
                    candidate = version
                    break
        else:
            raise ValueError(f"Invalid Node.js version specifier: {node_version}")

        if candidate is None:
            raise RuntimeError(
                f"Node.js {node_version} does not exist or is unavailable for {target_arch}"
            )
        if node_os_id not in candidate.get("files", []):
            raise RuntimeError(
                f"Node.js {candidate['version']} is unavailable for {target_arch}"
            )

        logging.info(
            "Found matching Node.js version %s (%s)",
            candidate["version"],
            candidate["date"],
        )
        selected_version = candidate["version"]
        file_name = f"node-{selected_version}-{node_os_id}.tar.gz"
        return selected_version, file_name

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        if cast(NpmPluginProperties, self._options).npm_include_node:
            return {"curl", "gcc"}
        return {"gcc"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        # set the Node environment to production mode
        base_env = {
            "NODE_ENV": "production",
        }
        if cast(NpmPluginProperties, self._options).npm_include_node:
            base_env["PATH"] = "${CRAFT_PART_INSTALL}/bin:${PATH}"
        return base_env

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        return []

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        cmd = []
        options = cast(NpmPluginProperties, self._options)
        if options.npm_include_node:
            arch = self._get_architecture()
            version = options.npm_node_version
            resolved_version, file_name = self._get_best_node_version(version, arch)

            node_uri = f"https://nodejs.org/dist/{resolved_version}/{file_name}"
            checksum_uri = f"https://nodejs.org/dist/{resolved_version}/SHASUMS256.txt"
            self._node_binary_path = os.path.join(
                self._part_info.part_cache_dir, file_name
            )
            cmd += [
                dedent(
                    f"""\
                if [ ! -f "{self._node_binary_path}" ]; then
                    mkdir -p "{self._part_info.part_cache_dir}"
                    curl --retry 5 -s "{checksum_uri}" -o "{self._part_info.part_cache_dir}"/SHASUMS256.txt
                    curl --retry 5 -s "{node_uri}" -o "{self._node_binary_path}"
                fi
                pushd "{self._part_info.part_cache_dir}"
                sha256sum --ignore-missing --strict -c SHASUMS256.txt
                popd
                """
                )
            ]
        if self._node_binary_path is not None:
            cmd += [
                dedent(
                    f"""\
                tar -xzf "{self._node_binary_path}" -C "${{CRAFT_PART_INSTALL}}/" \
                    --no-same-owner --strip-components=1
                """
                ),
            ]
        cmd += [
            dedent(
                """\
            NPM_VERSION="$(npm --version)"
            # use the new-style install command if npm >= 10.0.0
            if ((${NPM_VERSION%%.*}>=10)); then
                npm install -g --prefix "${CRAFT_PART_INSTALL}" --install-links "${PWD}"
            else
                npm install -g --prefix "${CRAFT_PART_INSTALL}" "$(npm pack . | tail -1)"
            fi
            """
            )
        ]
        return cmd
    
    def _append_package_dir(self, pkg_dir: Path, pkg_name: str | None, file_list: dict[str, list[Path]], missing_deps: list[str]) -> None:
        """Reads a package dir and appends to file_list.

        :param pkg_dir: A dir containing a package.json.
        :param pkg_name: Passed when the package's name is known (i.e., not at the top level).
        :param file_list: The data structure to add the package to.
        :param missing_deps: A list of package name dependencies that couldn't be found via simple resolution, for verifying at the end.
        """
        if pkg_dir.name.startswith("@"):
            # This is a scoped name: the package.json file(s) will be in dir(s) under the scope name dir.
            # https://docs.npmjs.com/cli/v9/using-npm/scope
            missing_deps = []
            for unscoped_pkg_dir in pkg_dir.iterdir():
                # TODO: Do we need to build the name to pass in the recursive call here?
                self._append_package_dir(unscoped_pkg_dir, None, file_list, missing_deps)
            return

        # From the package-json npm docs page:
        # "If the package.json for your package is not in the root directory (for example if it is part of a monorepo), you can specify the directory in which it lives"
        # Need to figure out whether the final package will always have a package.json on the top level, even if the source repo doesn't.

        metadata_file = pkg_dir / "package.json"
        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
        except FileNotFoundError:
            # The package.json didn't exist, assume this isn't a top-level dir and this means that we have dependencies that are at the same level as each other.  For instance, if A depends on B and C, and B also depends on C, then we'll fail to find C under B's node_modules dir because it already exists in A's node_modules dir.
            # If the package name hasn't been passed, then something is wrong.
            if not pkg_name:
                raise
            missing_deps.append(pkg_name)
            return

        # https://docs.npmjs.com/cli/v10/configuring-npm/package-json

        pkg_name = metadata["name"]
        if pkg_name in file_list:
            # We've already resolved this package at a different level
            return

        # NPM allows str or dict for bin - normalize it
        bintype = type(metadata.get("bin", False))
        bins = []
        if bintype is str:
            bins = [pkg_dir / metadata["bin"]]
        elif bintype is dict:
            bins = [pkg_dir / bin_file for _, bin_file in metadata["bin"].items()]

        # TODO: man

        # TODO: directories (directories.bin, directories.man)

        # TODO: scripts

        # TODO: workspaces?

        # TODO: verify default values

        file_list[pkg_name] = [
            pkg_dir / metadata.get("main", "index.js"),
            
        ] + bins

        # TODO: peerDependencies
        # (may or may not be installed)

        # TODO: bundleDependencies
        # (do we want to call out files that were bundled in as originating from their actual source package?)

        # TODO: optionalDepenencies

        try:
            for dep_name in metadata.get("dependencies", []):
                dep_pkg_dir = pkg_dir / "node_modules" / dep_name
                self._append_package_dir(dep_pkg_dir, dep_name, file_list, missing_deps)
        except KeyError as e:
            # No dependencies
            pass


    # TODO: It seems like node packages don't have a manifest?  In which case we'll need to inspect the archive, and thus have a plugin hook at a different spot

    def get_file_list(self) -> dict[str, list[Path]]:
        modules_dir = self._part_info.part_install_dir / "usr/lib/node_modules"

        ret = {}
        missing = []
        for pkg_dir in modules_dir.iterdir():
            # These pkg_dirs will be the leaf modules installed by the user
            self._append_package_dir(pkg_dir, None, ret, missing)
        #breakpoint()

        # TODO: Figure out if the "missing packages" is actually a case we can hit, and either add in the checking for it or remove it

        return ret
