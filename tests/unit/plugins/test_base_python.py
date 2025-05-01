# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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
from textwrap import dedent
from typing import Literal

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.base import BasePythonPlugin, PluginProperties
from overrides import override


class FakePythonPluginProperties(PluginProperties, frozen=True):
    plugin: Literal["fakepy"] = "fakepy"
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class FakePythonPlugin(BasePythonPlugin):
    """A really awesome Python plugin"""

    properties_class = FakePythonPluginProperties
    _options: FakePythonPluginProperties

    @override
    def _get_package_install_commands(self) -> list[str]:
        return ['"${PARTS_PYTHON_INTERPRETER}" -m fake_pip --install']


@pytest.fixture
def plugin(new_dir):
    properties = FakePythonPlugin.properties_class.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return FakePythonPlugin(properties=properties, part_info=part_info)


def get_python_build_commands(
    new_dir: Path, *, should_remove_symlinks: bool = False
) -> list[str]:
    if should_remove_symlinks:
        postfix = [
            f"echo Removing python symlinks in {new_dir}/parts/p1/install/bin",
            f'rm "{new_dir}/parts/p1/install"/bin/python*',
        ]
    else:
        postfix = ['ln -sf "${symlink_target}" "${PARTS_PYTHON_VENV_INTERP_PATH}"']

    return [
        dedent(
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
            payload_python=$(find "$install_dir" "$stage_dir" -type f -executable -name "${{basename}}" -print -quit 2>/dev/null || true)

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
                echo "Python interpreter not found in payload." >&2
                symlink_target="$(readlink -f "$(which "${{PARTS_PYTHON_INTERPRETER}}")")"
            fi

            if [ -z "$symlink_target" ]; then
                echo "No suitable Python interpreter found, giving up." >&2
                exit 1
            fi

            eval "${{opts_state}}"
            """
        ),
        *postfix,
    ]


def get_python_shebang_rewrite_commands(
    expected_shebang: str, install_dir: str
) -> list[str]:
    find_cmd = f'find "{install_dir}" -type f -executable -print0'
    xargs_cmd = "xargs --no-run-if-empty -0"
    sed_cmd = (
        f'sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|{expected_shebang}|"'
    )
    return [
        dedent(
            f"""\
            {find_cmd} | {xargs_cmd} \\
                {sed_cmd}
            """
        )
    ]


def test_get_build_packages(plugin) -> None:
    assert plugin.get_build_packages() == {"findutils", "python3-venv", "python3-dev"}


def test_get_build_environment(plugin, new_dir) -> None:
    assert plugin.get_build_environment() == {
        "PATH": f"{new_dir}/parts/p1/install/bin:${{PATH}}",
        "PARTS_PYTHON_INTERPRETER": "python3",
        "PARTS_PYTHON_VENV_ARGS": "",
    }


def test_get_build_commands(plugin, new_dir) -> None:
    venv_path = new_dir / "parts" / "p1" / "install"
    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{venv_path}"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{venv_path}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        '"${PARTS_PYTHON_INTERPRETER}" -m fake_pip --install',
        *get_python_shebang_rewrite_commands(
            "#!/usr/bin/env ${PARTS_PYTHON_INTERPRETER}",
            str(plugin._part_info.part_install_dir),
        ),
        *get_python_build_commands(new_dir, should_remove_symlinks=False),
    ]


def test_call_should_remove_symlinks(plugin, new_dir, monkeypatch):
    monkeypatch.setattr(plugin, "_should_remove_symlinks", lambda: True)

    venv_path = new_dir / "parts" / "p1" / "install"
    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{venv_path}"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{venv_path}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        '"${PARTS_PYTHON_INTERPRETER}" -m fake_pip --install',
        *get_python_shebang_rewrite_commands(
            "#!/usr/bin/env ${PARTS_PYTHON_INTERPRETER}",
            str(plugin._part_info.part_install_dir),
        ),
        *get_python_build_commands(new_dir, should_remove_symlinks=True),
    ]


def test_script_interpreter(plugin):
    assert plugin._get_script_interpreter() == (
        "#!/usr/bin/env ${PARTS_PYTHON_INTERPRETER}"
    )


def test_get_system_python_interpreter(plugin):
    assert plugin._get_system_python_interpreter() == (
        '$(readlink -f "$(which "${PARTS_PYTHON_INTERPRETER}")")'
    )
