# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

import json
import os
import random
import string
from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.base import Package
from craft_parts.plugins.npm_plugin import NpmPlugin
from pydantic import ValidationError

# pylint: disable=too-many-public-methods


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


class TestPluginNpmPlugin:
    """Npm plugin tests."""

    def test_validate_environment(self, dependency_fixture, part_info):
        node = dependency_fixture(name="node")
        npm = dependency_fixture(name="npm")
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)
        validator = plugin.validator_class(
            part_name="my-part",
            env=f"PATH={str(node.parent)}:{str(npm.parent)}",
            properties=properties,
        )

        validator.validate_environment()

    @pytest.mark.parametrize(
        "dependencies",
        [
            ("node", ["npm"]),
            ("npm", ["node"]),
        ],
    )
    def test_validate_environment_missing_dependencies(
        self, dependencies, dependency_fixture, new_dir, part_info
    ):
        """Validate that missing dependencies raise an exception.

        :param dependencies: tuple consisting of 1 missing dependency
        and a list of valid dependencies
        """
        missing_dependency_name, valid_dependency_names = dependencies
        path = "PATH="

        for valid_dependencies_name in valid_dependency_names:
            valid_dependency = dependency_fixture(valid_dependencies_name)
            path += f":{str(valid_dependency.parent)}"

        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)
        validator = plugin.validator_class(
            part_name="my-part", env=path, properties=properties
        )

        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert raised.value.reason == f"'{missing_dependency_name}' not found"

    @pytest.mark.parametrize(
        "dependencies",
        [
            ("node", ["npm"]),
            ("npm", ["node"]),
        ],
    )
    def test_validate_environment_broken_dependencies(
        self, dependencies, dependency_fixture, new_dir, part_info
    ):
        """Validate that broken dependencies raise an exception.

        :param dependencies: tuple consisting of 1 broken dependency
        and a list of valid dependencies
        """
        broken_dependency_name, valid_dependency_names = dependencies
        broken_dependency = dependency_fixture(broken_dependency_name, broken=True)
        path = f"PATH={str(broken_dependency.parent)}"

        for valid_dependencies_name in valid_dependency_names:
            valid_dependency = dependency_fixture(valid_dependencies_name)
            path += f":{str(valid_dependency.parent)}"

        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)
        validator = plugin.validator_class(
            part_name="my-part", env=path, properties=properties
        )

        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert (
            raised.value.reason
            == f"'{broken_dependency_name}' failed with error code 33"
        )

    def test_validate_environment_part_dependencies(self, new_dir, part_info):
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)
        validator = plugin.validator_class(
            part_name="my-part", env="PATH=/foo", properties=properties
        )

        validator.validate_environment(part_dependencies=["npm-deps"])

    @pytest.mark.parametrize(
        ("satisfied_dependency", "error_dependency"),
        [
            ("node", "npm"),
            ("npm", "node"),
        ],
    )
    def test_validate_environment_missing_part_dependencies(
        self,
        satisfied_dependency,
        error_dependency,
        dependency_fixture,
        new_dir,
        part_info,
    ):
        """Validate that missing part dependencies raise an exception."""
        dependency = dependency_fixture(name=satisfied_dependency)

        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)
        validator = plugin.validator_class(
            part_name="my-part",
            properties=properties,
            env=f"PATH={str(dependency.parent)}",
        )

        with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
            validator.validate_environment(part_dependencies=[])

        assert raised.value.reason == (
            f"{error_dependency!r} not found and part 'my-part' "
            "does not depend on a part named 'npm-deps' that "
            "would satisfy the dependency"
        )

    def test_get_build_snaps(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_snaps() == set()

    def test_get_build_packages(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_packages() == {"gcc"}

    def test_get_build_packages_include_node_false(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal(
            {
                "source": ".",
                "npm-include-node": False,
            }
        )
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_packages() == {"gcc"}

    def test_get_build_packages_include_node_true(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal(
            {"source": ".", "npm-include-node": True, "npm-node-version": "1.0.0"}
        )
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_packages() == {"curl", "gcc"}

    def test_get_build_environment(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_environment() == {"NODE_ENV": "production"}

    def test_get_build_environment_include_node_false(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal(
            {
                "source": ".",
                "npm-include-node": False,
            }
        )
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_environment() == {"NODE_ENV": "production"}

    def test_get_build_environment_include_node_true(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal(
            {
                "source": ".",
                "npm-include-node": True,
                "npm-node-version": "1.0.0",
            }
        )
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_environment() == {
            "PATH": "${CRAFT_PART_INSTALL}/bin:${PATH}",
            "NODE_ENV": "production",
        }

    def test_get_build_commands(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            'NPM_VERSION="$(npm --version)"\n'
            "# use the new-style install command if npm >= 10.0.0\n"
            "if ((${NPM_VERSION%%.*}>=10)); then\n"
            '    npm install -g --prefix "${CRAFT_PART_INSTALL}" --install-links "${PWD}"\n'
            "else\n"
            '    npm install -g --prefix "${CRAFT_PART_INSTALL}" "$(npm pack . | tail -1)"\n'
            "fi\n",
        ]

    def test_get_build_commands_false(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal(
            {"source": ".", "npm-include-node": False}
        )
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            'NPM_VERSION="$(npm --version)"\n'
            "# use the new-style install command if npm >= 10.0.0\n"
            "if ((${NPM_VERSION%%.*}>=10)); then\n"
            '    npm install -g --prefix "${CRAFT_PART_INSTALL}" --install-links "${PWD}"\n'
            "else\n"
            '    npm install -g --prefix "${CRAFT_PART_INSTALL}" "$(npm pack . | tail -1)"\n'
            "fi\n",
        ]

    @pytest.mark.parametrize(
        "version",
        ["20", "20.13", "20.13.1", "lts/iron"],
    )
    def test_get_build_commands_include_node_true(
        self, version, part_info, mocker, new_dir
    ):
        mocker.patch.dict(os.environ, {"SNAP_ARCH": "amd64"})
        properties = NpmPlugin.properties_class.unmarshal(
            {
                "source": ".",
                "npm-include-node": True,
                "npm-node-version": version,
            }
        )
        NpmPlugin._fetch_node_release_index = lambda: [
            {
                "version": "v99.99.99",
                "date": "3304-12-31",
                "files": ["linux-x64"],
                "lts": False,
                "security": False,
            },
            {
                "version": "v20.13.1",
                "date": "2024-05-09",
                "files": ["linux-x64"],
                "lts": "Iron",
                "security": False,
            },
        ]
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_pull_commands() == []

        assert plugin.get_build_commands() == [
            f'if [ ! -f "{part_info.part_cache_dir}/node-v20.13.1-linux-x64.tar.gz" ]; then\n'
            f'    mkdir -p "{part_info.part_cache_dir}"\n'
            f'    curl --retry 5 -s "https://nodejs.org/dist/v20.13.1/SHASUMS256.txt" -o "{part_info.part_cache_dir}"/SHASUMS256.txt\n'
            f'    curl --retry 5 -s "https://nodejs.org/dist/v20.13.1/node-v20.13.1-linux-x64.tar.gz" -o "{part_info.part_cache_dir}/node-v20.13.1-linux-x64.tar.gz"\n'
            "fi\n"
            f'pushd "{part_info.part_cache_dir}"\n'
            "sha256sum --ignore-missing --strict -c SHASUMS256.txt\npopd\n",
            f'tar -xzf "{part_info.part_cache_dir}/node-v20.13.1-linux-x64.tar.gz"'
            ' -C "${CRAFT_PART_INSTALL}/"                     --no-same-owner '
            "--strip-components=1\n",
            'NPM_VERSION="$(npm --version)"\n'
            "# use the new-style install command if npm >= 10.0.0\n"
            "if ((${NPM_VERSION%%.*}>=10)); then\n"
            '    npm install -g --prefix "${CRAFT_PART_INSTALL}" --install-links "${PWD}"\n'
            "else\n"
            '    npm install -g --prefix "${CRAFT_PART_INSTALL}" "$(npm pack . | tail -1)"\n'
            "fi\n",
        ]

    def test_get_build_commands_include_node_true_no_node_version(
        self, part_info, new_dir
    ):
        with pytest.raises(ValidationError) as raised:
            NpmPlugin.properties_class.unmarshal(
                {
                    "source": ".",
                    "npm-include-node": True,
                }
            )

        assert raised.value.errors()[0]["msg"] == (
            "Value error, npm-node-version is required if npm-include-node is true"
        )

    @pytest.mark.parametrize(
        "architecture",
        [
            ("amd64", "x64"),
            ("i386", "x86"),
            ("armhf", "armv7l"),
            ("arm64", "arm64"),
            ("ppc64el", "ppc64le"),
            ("s390x", "s390x"),
        ],
    )
    def test_get_architecture_from_snap_arch(self, architecture, mocker):
        mocker.patch.dict(
            os.environ,
            {"SNAP_ARCH": architecture[0]},
        )
        assert NpmPlugin._get_architecture() == architecture[1]

    def test_get_architecture_from_snap_invalid(self, mocker):
        mocker.patch.dict(
            os.environ,
            {"SNAP_ARCH": "System/360"},
        )

        with pytest.raises(errors.InvalidArchitecture) as raised:
            NpmPlugin._get_architecture()

        assert raised.value.brief == "Architecture 'System/360' is not supported."

    def test_get_architecture_from_platform_for_x86(self, mocker):
        mocker.patch("platform.machine", return_value="x86_64")
        mocker.patch("platform.architecture", return_value=("64bit", "ELF"))
        assert NpmPlugin._get_architecture() == "x64"

    def test_get_architecture_from_platform_invalid(self, mocker, monkeypatch):
        monkeypatch.delenv("SNAP_ARCH", raising=False)
        mocker.patch("platform.machine", return_value="System/360")
        mocker.patch("platform.architecture", return_value=("32bit", "OS/360"))

        with pytest.raises(errors.InvalidArchitecture) as raised:
            NpmPlugin._get_architecture()

        assert (
            raised.value.brief
            == """Architecture "System/360 ('32bit', 'OS/360')" is not supported."""
        )

    def test_get_out_of_source_build(self, part_info, new_dir):
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        assert plugin.get_out_of_source_build() is False

    def test_get_package_files(self, part_info, new_dir):  # noqa: PLR0915
        properties = NpmPlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmPlugin(properties=properties, part_info=part_info)

        # Build a fake file tree, emulating what real package installs look like.
        # Integration tests actually install stuff and check a subset of the
        # large installed trees.
        root = plugin._part_info.part_install_dir
        root.mkdir(parents=True)

        def _randstr():
            return "".join(
                random.choice(  # noqa: S311
                    string.ascii_letters + string.digits + ".-_"
                )
                for i in range(10)
            )

        def _mk_package_json(path, version):
            with open(path / "package.json", "w") as f:
                json.dump(
                    {
                        "version": version,
                        "name": _randstr(),
                        _randstr(): _randstr(),
                    },
                    f,
                )

        def _mk_module_b(path, version):
            (path / "index.js").touch()
            _mk_package_json(path, version)

        # This tree should exercise a lot of weird things that node does and
        # how we handle them:
        # ├── bin
        # │   ├── my_executable -> ../lib/node_modules/modulea/bin/cli.js
        # │   ├── uboat -> ../lib/node_modules/modulea/node_modules/@periscope/sodeep/submarine.js
        # │   ├── something_else -> ../another/path
        # │   ├── not-even-a-link
        # │   └── modulec_thing -> ../lib/node_modules/@scopename/modulec/bin/index.js
        # ├── glorp
        #     └── plop
        # └── lib
        #     ├── boop
        #     └── node_modules
        #         ├── modulea
        #         │   ├── bin
        #         │   │   └── cli.js
        #         │   ├── index.js
        #         │   ├── package.json
        #         │   └── node_modules
        #         │       ├── @periscope
        #         │       │   └── sodeep
        #         │       │       ├── AUTHORS.txt
        #         │       │       ├── submarine.js
        #         │       │       ├── package.json
        #         │       │       └── node_modules
        #         │       │           └── moduleb
        #         │       │               ├── index.js
        #         │       │               └── package.json (v178)
        #         │       └── moduleb
        #         │           ├── index.js
        #         │           └── package.json (v2.77)
        #         ├── moduleb
        #         │   ├── index.js
        #         │   └── package.json (v1.01.1a)
        #         └── @scopename
        #             └── modulec
        #                 ├── bin
        #                 │   └── index.js
        #                 ├── lib
        #                 │   └── index.js
        #                 ├── LICENSE
        #                 ├── package.json
        #                 └── node_modules
        #                      └── moduleb
        #                          ├── index.js
        #                          └── package.json (v1.01.1a)

        # Top dirs
        (root / "bin").mkdir()
        (root / "lib").mkdir()
        (root / "lib/node_modules").mkdir()
        (root / "glorp").mkdir()

        # Ignored files
        (root / "glorp/plop").touch()
        (root / "bin/not-even-a-link").touch()
        (root / "lib/boop").touch()
        (root / "bin/something_else").symlink_to("../another/path")

        # Module dir trees
        (root / "lib/node_modules/modulea").mkdir()
        (root / "lib/node_modules/moduleb").mkdir()
        (root / "lib/node_modules/@scopename").mkdir()
        (root / "lib/node_modules/@scopename/modulec").mkdir()

        # Submodule dir trees
        (root / "lib/node_modules/modulea/node_modules").mkdir()
        (root / "lib/node_modules/modulea/node_modules/@periscope").mkdir()
        (root / "lib/node_modules/modulea/node_modules/@periscope/sodeep").mkdir()
        (
            root
            / "lib/node_modules/modulea/node_modules/@periscope/sodeep/node_modules"
        ).mkdir()
        (
            root
            / "lib/node_modules/modulea/node_modules/@periscope/sodeep/node_modules/moduleb"
        ).mkdir()
        (root / "lib/node_modules/modulea/node_modules/moduleb").mkdir()

        (root / "lib/node_modules/@scopename/modulec/node_modules").mkdir()
        (root / "lib/node_modules/@scopename/modulec/node_modules/moduleb").mkdir()

        # Populate each module install dir
        (root / "lib/node_modules/modulea/bin").mkdir()
        (root / "lib/node_modules/modulea/bin/cli.js").touch()
        (root / "lib/node_modules/modulea/index.js").touch()
        modulea_version = _randstr()
        _mk_package_json(root / "lib/node_modules/modulea", modulea_version)

        dupe_moduleb_version = "1.01.1a"
        _mk_module_b(root / "lib/node_modules/moduleb", dupe_moduleb_version)

        (root / "lib/node_modules/@scopename/modulec/bin").mkdir()
        (root / "lib/node_modules/@scopename/modulec/bin/index.js").touch()
        (root / "lib/node_modules/@scopename/modulec/lib").mkdir()
        (root / "lib/node_modules/@scopename/modulec/lib/index.js").touch()
        (root / "lib/node_modules/@scopename/modulec/LICENSE").touch()
        modulec_version = _randstr()
        _mk_package_json(root / "lib/node_modules/@scopename/modulec", modulec_version)

        (
            root / "lib/node_modules/modulea/node_modules/@periscope/sodeep/AUTHORS.txt"
        ).touch()
        (
            root
            / "lib/node_modules/modulea/node_modules/@periscope/sodeep/submarine.js"
        ).touch()
        sodeep_version = _randstr()
        _mk_package_json(
            root / "lib/node_modules/modulea/node_modules/@periscope/sodeep",
            sodeep_version,
        )

        sodeep_moduleb_version = "178"
        _mk_module_b(
            root
            / "lib/node_modules/modulea/node_modules/@periscope/sodeep/node_modules/moduleb",
            sodeep_moduleb_version,
        )

        modulea_moduleb_version = "2.77"
        _mk_module_b(
            root / "lib/node_modules/modulea/node_modules/moduleb",
            modulea_moduleb_version,
        )

        _mk_module_b(
            root / "lib/node_modules/@scopename/modulec/node_modules/moduleb",
            dupe_moduleb_version,
        )

        # bin symlinks
        (root / "bin/my_executable").symlink_to(
            "../lib/node_modules/modulea/bin/cli.js", target_is_directory=True
        )
        (root / "bin/uboat").symlink_to(
            "../lib/node_modules/modulea/node_modules/@periscope/sodeep/submarine.js",
            target_is_directory=True,
        )
        (root / "bin/modulec_thing").symlink_to(
            "../lib/node_modules/@scopename/modulec/bin/index.js",
            target_is_directory=True,
        )

        expected = {
            Package("npm", "modulea", modulea_version): {
                Path(root / "bin/my_executable"),
                Path(root / "lib/node_modules/modulea/bin"),
                Path(root / "lib/node_modules/modulea/bin/cli.js"),
                Path(root / "lib/node_modules/modulea/index.js"),
                Path(root / "lib/node_modules/modulea/package.json"),
            },
            Package("npm", "moduleb", dupe_moduleb_version): {
                Path(root / "lib/node_modules/moduleb/index.js"),
                Path(root / "lib/node_modules/moduleb/package.json"),
                Path(
                    root
                    / "lib/node_modules/@scopename/modulec/node_modules/moduleb/index.js"
                ),
                Path(
                    root
                    / "lib/node_modules/@scopename/modulec/node_modules/moduleb/package.json"
                ),
            },
            Package("npm", "@scopename/modulec", modulec_version): {
                Path(root / "bin/modulec_thing"),
                Path(root / "lib/node_modules/@scopename/modulec/bin"),
                Path(root / "lib/node_modules/@scopename/modulec/bin/index.js"),
                Path(root / "lib/node_modules/@scopename/modulec/lib"),
                Path(root / "lib/node_modules/@scopename/modulec/lib/index.js"),
                Path(root / "lib/node_modules/@scopename/modulec/LICENSE"),
                Path(root / "lib/node_modules/@scopename/modulec/package.json"),
            },
            Package("npm", "@periscope/sodeep", sodeep_version): {
                Path(root / "bin/uboat"),
                Path(
                    root
                    / "lib/node_modules/modulea/node_modules/@periscope/sodeep/AUTHORS.txt"
                ),
                Path(
                    root
                    / "lib/node_modules/modulea/node_modules/@periscope/sodeep/submarine.js"
                ),
                Path(
                    root
                    / "lib/node_modules/modulea/node_modules/@periscope/sodeep/package.json"
                ),
            },
            Package("npm", "moduleb", sodeep_moduleb_version): {
                Path(
                    root
                    / "lib/node_modules/modulea/node_modules/@periscope/sodeep/node_modules/moduleb/index.js"
                ),
                Path(
                    root
                    / "lib/node_modules/modulea/node_modules/@periscope/sodeep/node_modules/moduleb/package.json"
                ),
            },
            Package("npm", "moduleb", modulea_moduleb_version): {
                Path(root / "lib/node_modules/modulea/node_modules/moduleb/index.js"),
                Path(
                    root / "lib/node_modules/modulea/node_modules/moduleb/package.json"
                ),
            },
        }

        assert expected == plugin.get_package_files()
