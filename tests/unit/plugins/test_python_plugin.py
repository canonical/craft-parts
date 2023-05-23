# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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
from typing import List

import pytest
from pydantic import ValidationError

from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.python_plugin import PythonPlugin


@pytest.fixture
def plugin(new_dir):
    properties = PythonPlugin.properties_class.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return PythonPlugin(properties=properties, part_info=part_info)


def test_get_build_packages(plugin):
    assert plugin.get_build_packages() == {"findutils", "python3-venv", "python3-dev"}


def test_get_build_environment(plugin, new_dir):
    assert plugin.get_build_environment() == {
        "PATH": f"{new_dir}/parts/p1/install/bin:${{PATH}}",
        "PARTS_PYTHON_INTERPRETER": "python3",
        "PARTS_PYTHON_VENV_ARGS": "",
    }


# pylint: disable=line-too-long


def get_build_commands(new_dir: Path) -> List[str]:
    return [
        dedent(
            f"""\
            find "{new_dir}/parts/p1/install" -type f -executable -print0 | xargs -0 \\
                sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|#!/usr/bin/env ${{PARTS_PYTHON_INTERPRETER}}|"
            """
        ),
        dedent(
            f"""\
            # look for a provisioned python interpreter
            opts_state="$(set +o|grep errexit)"
            set +e
            install_dir="{new_dir}/parts/p1/install/usr/bin"
            stage_dir="{new_dir}/stage/usr/bin"
            payload_python=$(find "$install_dir" "$stage_dir" -type f -executable -name "python3.*" -print -quit 2>/dev/null)

            if [ -n "$payload_python" ]; then
                # We found a provisioned interpreter, use it.
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
                symlink_target="$(readlink -f "$(which "${{PARTS_PYTHON_INTERPRETER}}")")"
            fi

            if [ -z "$symlink_target" ]; then
                echo "No suitable Python interpreter found, giving up."
                exit 1
            fi

            eval "${{opts_state}}"
            ln -sf "${{symlink_target}}" "${{PARTS_PYTHON_VENV_INTERP_PATH}}"
            """
        ),
    ]


def test_get_build_commands(plugin, new_dir):
    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        f"{new_dir}/parts/p1/install/bin/pip install  -U pip setuptools wheel",
        f"[ -f setup.py ] && {new_dir}/parts/p1/install/bin/pip install  -U .",
    ] + get_build_commands(new_dir)


def test_get_build_commands_with_all_properties(new_dir):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PythonPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "python-constraints": ["constraints.txt"],
            "python-requirements": ["requirements.txt"],
            "python-packages": ["pip", "some-pkg; sys_platform != 'win32'"],
        }
    )

    python_plugin = PythonPlugin(part_info=part_info, properties=properties)

    assert python_plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        f"{new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U pip 'some-pkg; sys_platform != '\"'\"'win32'\"'\"''",
        f"{new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U -r 'requirements.txt'",
        f"[ -f setup.py ] && {new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U .",
    ] + get_build_commands(new_dir)


def test_invalid_properties():
    with pytest.raises(ValidationError) as raised:
        PythonPlugin.properties_class.unmarshal({"source": ".", "python-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("python-invalid",)
    assert err[0]["type"] == "value_error.extra"


def test_missing_properties():
    with pytest.raises(ValidationError) as raised:
        PythonPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "value_error.missing"


def test_get_out_of_source_build(plugin):
    assert plugin.get_out_of_source_build() is False


def test_should_remove_symlinks(plugin):
    assert plugin._should_remove_symlinks() is False


def test_get_system_python_interpreter(plugin):
    assert plugin._get_system_python_interpreter() == (
        '$(readlink -f "$(which "${PARTS_PYTHON_INTERPRETER}")")'
    )


def test_script_interpreter(plugin):
    assert plugin._get_script_interpreter() == (
        "#!/usr/bin/env ${PARTS_PYTHON_INTERPRETER}"
    )


def test_call_should_remove_symlinks(plugin, new_dir, mocker):
    mocker.patch(
        "craft_parts.plugins.python_plugin.PythonPlugin._should_remove_symlinks",
        return_value=True,
    )

    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        f"{new_dir}/parts/p1/install/bin/pip install  -U pip setuptools wheel",
        f"[ -f setup.py ] && {new_dir}/parts/p1/install/bin/pip install  -U .",
        f'find "{new_dir}/parts/p1/install" -type f -executable -print0 | xargs -0 \\\n'
        f'    sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|#!/usr/bin/env ${{PARTS_PYTHON_INTERPRETER}}|"\n',
        f"echo Removing python symlinks in {new_dir}/parts/p1/install/bin\n"
        f'rm "{new_dir}/parts/p1/install"/bin/python*\n',
    ]
