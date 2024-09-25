# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

import textwrap
from typing import Literal, cast

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin, PluginProperties
from craft_parts.plugins.base import BasePythonPlugin


class FooPluginProperties(PluginProperties, frozen=True):
    """Test plugin properties."""

    plugin: Literal["foo"] = "foo"

    foo_name: str


class FooPlugin(Plugin):
    """A test plugin."""

    properties_class = FooPluginProperties

    def get_build_snaps(self) -> set[str]:
        return {"build_snap"}

    def get_build_packages(self) -> set[str]:
        return {"build_package"}

    def get_build_environment(self) -> dict[str, str]:
        return {"ENV": "value"}

    def get_build_commands(self) -> list[str]:
        options = cast(FooPluginProperties, self._options)
        return ["hello", options.foo_name]


def test_plugin(new_dir):
    part = Part("p1", {})
    project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=project_info, part=part)

    props = FooPluginProperties.unmarshal({"foo-name": "world"})
    plugin = FooPlugin(properties=props, part_info=part_info)

    validator = FooPlugin.validator_class(part_name=part.name, env="", properties=props)
    validator.validate_environment()

    assert plugin.get_build_snaps() == {"build_snap"}
    assert plugin.get_build_packages() == {"build_package"}
    assert plugin.get_build_environment() == {"ENV": "value"}
    assert plugin.get_out_of_source_build() is False
    assert plugin.get_build_commands() == ["hello", "world"]


def test_abstract_methods(new_dir):
    class FaultyPlugin(Plugin):
        """A plugin that doesn't implement abstract methods."""

    part = Part("p1", {})
    project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=project_info, part=part)

    expected = (
        r"^Can't instantiate abstract class FaultyPlugin with(out an implementation "
        r"for)? abstract methods '?get_build_commands'?, '?get_build_environment'?, "
        r"'?get_build_packages'?, '?get_build_snaps'?$"
    )

    with pytest.raises(TypeError, match=expected):
        FaultyPlugin(properties=None, part_info=part_info)  # type: ignore[reportGeneralTypeIssues]


class FooPythonPlugin(BasePythonPlugin):
    """A plugin for testing the base Python plugin."""

    properties_class = FooPluginProperties

    def _get_package_install_commands(self) -> list[str]:
        return ["echo 'This is where I put my install commands... if I had any!'"]


@pytest.fixture
def python_plugin(new_dir):
    properties = FooPythonPlugin.properties_class.unmarshal(
        {"source": ".", "foo-name": "testy"}
    )
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return FooPythonPlugin(properties=properties, part_info=part_info)


def test_python_get_build_packages(python_plugin):
    assert python_plugin.get_build_packages() == {
        "findutils",
        "python3-venv",
        "python3-dev",
    }


def test_python_get_build_environment(new_dir, python_plugin):
    assert python_plugin.get_build_environment() == {
        "PATH": f"{new_dir}/parts/p1/install/bin:${{PATH}}",
        "PARTS_PYTHON_INTERPRETER": "python3",
        "PARTS_PYTHON_VENV_ARGS": "",
    }


def test_python_get_create_venv_commands(new_dir, python_plugin: FooPythonPlugin):
    assert python_plugin._get_create_venv_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
    ]


def test_python_get_find_python_interpreter_commands(
    new_dir, python_plugin: FooPythonPlugin
):
    assert python_plugin._get_find_python_interpreter_commands() == [
        textwrap.dedent(
            f"""\
            # look for a provisioned python interpreter
            opts_state="$(set +o|grep errexit)"
            set +e
            install_dir="{new_dir}/parts/p1/install/usr/bin"
            stage_dir="{new_dir}/stage/usr/bin"

            # look for the right Python version - if the venv was created with python3.10,
            # look for python3.10
            basename=$(basename $(readlink -f ${{PARTS_PYTHON_VENV_INTERP_PATH}}))
            echo Looking for a Python interpreter called \\"${{basename}}\\" in the payload...
            payload_python=$(find "$install_dir" "$stage_dir" -type f -executable -name "${{basename}}" -print -quit 2>/dev/null)

            if [ -n "$payload_python" ]; then
                # We found a provisioned interpreter, use it.
                echo Found interpreter in payload: \\"${{payload_python}}\\"
                installed_python="${{payload_python##{new_dir}/parts/p1/install}}"
                if [ "$installed_python" = "$payload_python" ]; then
                    # Found a staged interpreter.
                    symlink_target="..${{payload_python##{new_dir}/stage}}"
                else
                    # The interpreter was installed but not staged yet.
                    symlink_target="..$installed_python"
                fi
            else
                # Otherwise use what _get_system_python_interpreter() told us.
                echo "Python interpreter not found in payload."
                symlink_target="$(readlink -f "$(which "${{PARTS_PYTHON_INTERPRETER}}")")"
            fi

            if [ -z "$symlink_target" ]; then
                echo "No suitable Python interpreter found, giving up."
                exit 1
            fi

            eval "${{opts_state}}"
            """
        ),
    ]


def test_python_get_rewrite_shebangs_commands(new_dir, python_plugin: FooPythonPlugin):
    assert python_plugin._get_rewrite_shebangs_commands() == [
        textwrap.dedent(
            f"""\
            find "{new_dir}/parts/p1/install" -type f -executable -print0 | xargs --no-run-if-empty -0 \\
                sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|#!/usr/bin/env ${{PARTS_PYTHON_INTERPRETER}}|"
            """
        )
    ]


@pytest.mark.parametrize(
    ("should_remove_symlinks", "expected_template"),
    [
        (
            True,
            [
                "echo Removing python symlinks in {install_dir}/bin",
                'rm "{install_dir}"/bin/python*',
            ],
        ),
        (False, ['ln -sf "${{symlink_target}}" "${{PARTS_PYTHON_VENV_INTERP_PATH}}"']),
    ],
)
def test_python_get_handle_symlinks_commands(
    new_dir,
    python_plugin: FooPythonPlugin,
    should_remove_symlinks,
    expected_template: list[str],
):
    expected = [
        template.format(install_dir=new_dir / "parts" / "p1" / "install")
        for template in expected_template
    ]
    python_plugin._should_remove_symlinks = lambda: should_remove_symlinks  # type: ignore[method-assign]

    assert python_plugin._get_handle_symlinks_commands() == expected


def test_python_get_build_commands(new_dir, python_plugin: FooPythonPlugin):
    assert python_plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        "echo 'This is where I put my install commands... if I had any!'",
        textwrap.dedent(
            f"""\
            find "{new_dir}/parts/p1/install" -type f -executable -print0 | xargs --no-run-if-empty -0 \\
                sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|#!/usr/bin/env ${{PARTS_PYTHON_INTERPRETER}}|"
            """
        ),
        textwrap.dedent(
            f"""\
            # look for a provisioned python interpreter
            opts_state="$(set +o|grep errexit)"
            set +e
            install_dir="{new_dir}/parts/p1/install/usr/bin"
            stage_dir="{new_dir}/stage/usr/bin"

            # look for the right Python version - if the venv was created with python3.10,
            # look for python3.10
            basename=$(basename $(readlink -f ${{PARTS_PYTHON_VENV_INTERP_PATH}}))
            echo Looking for a Python interpreter called \\"${{basename}}\\" in the payload...
            payload_python=$(find "$install_dir" "$stage_dir" -type f -executable -name "${{basename}}" -print -quit 2>/dev/null)

            if [ -n "$payload_python" ]; then
                # We found a provisioned interpreter, use it.
                echo Found interpreter in payload: \\"${{payload_python}}\\"
                installed_python="${{payload_python##{new_dir}/parts/p1/install}}"
                if [ "$installed_python" = "$payload_python" ]; then
                    # Found a staged interpreter.
                    symlink_target="..${{payload_python##{new_dir}/stage}}"
                else
                    # The interpreter was installed but not staged yet.
                    symlink_target="..$installed_python"
                fi
            else
                # Otherwise use what _get_system_python_interpreter() told us.
                echo "Python interpreter not found in payload."
                symlink_target="$(readlink -f "$(which "${{PARTS_PYTHON_INTERPRETER}}")")"
            fi

            if [ -z "$symlink_target" ]; then
                echo "No suitable Python interpreter found, giving up."
                exit 1
            fi

            eval "${{opts_state}}"
            """
        ),
        'ln -sf "${symlink_target}" "${PARTS_PYTHON_VENV_INTERP_PATH}"',
    ]
