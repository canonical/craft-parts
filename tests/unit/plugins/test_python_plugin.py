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
            find "{new_dir}/parts/p1/install" -type f -executable -print0 | xargs -0 \
                sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|#\\!/usr/bin/env ${{PARTS_PYTHON_INTERPRETER}}|"
            """
        ),
        dedent(
            f"""\
            determine_link_target() {{
                opts_state="$(set +o +x | grep xtrace)"
                interp_dir="$(dirname "${{PARTS_PYTHON_VENV_INTERP_PATH}}")"
                # Determine python based on PATH, then resolve it, e.g:
                # (1) <application venv dir>/bin/python3 -> /usr/bin/python3.8
                # (2) /usr/bin/python3 -> /usr/bin/python3.8
                # (3) /root/stage/python3 -> /root/stage/python3.8
                # (4) /root/parts/<part>/install/usr/bin/python3 -> /root/parts/<part>/install/usr/bin/python3.8
                python_path="$(which "${{PARTS_PYTHON_INTERPRETER}}")"
                python_path="$(readlink -e "${{python_path}}")"
                for dir in "{new_dir}/parts/p1/install" "{new_dir}/stage"; do
                    if  echo "${{python_path}}" | grep -q "${{dir}}"; then
                        python_path="$(realpath --strip --relative-to="${{interp_dir}}" \\
                                "${{python_path}}")"
                        break
                    fi
                done
                echo "${{python_path}}"
                eval "${{opts_state}}"
            }}

            python_path="$(determine_link_target)"
            ln -sf "${{python_path}}" "${{PARTS_PYTHON_VENV_INTERP_PATH}}"
        """
        ),
    ]


def test_get_build_commands(plugin, new_dir):
    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        "pip install  -U pip setuptools wheel",
        "[ -f setup.py ] && pip install  -U .",
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
        "pip install -c 'constraints.txt' -U pip 'some-pkg; sys_platform != '\"'\"'win32'\"'\"''",
        "pip install -c 'constraints.txt' -U -r 'requirements.txt'",
        "[ -f setup.py ] && pip install -c 'constraints.txt' -U .",
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
