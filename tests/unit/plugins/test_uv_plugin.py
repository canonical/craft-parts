# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.uv_plugin import UvPlugin
from pydantic import ValidationError


@pytest.fixture
def plugin(new_dir, monkeypatch):
    properties = UvPlugin.properties_class.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return UvPlugin(properties=properties, part_info=part_info)


def test_get_build_packages(plugin):
    assert plugin.get_build_packages() == {"findutils", "python3-venv", "python3-dev"}


def test_get_build_environment(plugin, new_dir):
    assert plugin.get_build_environment() == {
        "PATH": f"{new_dir}/parts/p1/install/bin:${{PATH}}",
        "PARTS_PYTHON_INTERPRETER": "python3",
        "PARTS_PYTHON_VENV_ARGS": "",
        "VIRTUAL_ENV": str(plugin._part_info.part_install_dir.resolve()),
        "UV_PROJECT_ENVIRONMENT": str(plugin._part_info.part_install_dir.resolve()),
        "UV_FROZEN": "true",
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_PYTHON": '"${PARTS_PYTHON_INTERPRETER}"',
        "UV_PYTHON_PREFERENCE": "only-system",
    }


# pylint: disable=line-too-long


def get_build_commands(
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
        *postfix,
    ]


def test_get_build_commands(plugin, new_dir):
    venv_dir = plugin._part_info.part_install_dir

    assert plugin.get_build_commands() == [
        f'uv venv --relocatable --allow-existing --python "{plugin._get_system_python_interpreter()}" "{venv_dir}"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{venv_dir}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        "uv sync --no-dev --no-editable",
        *get_build_commands(new_dir),
    ]


def test_get_build_commands_with_all_properties(new_dir):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = UvPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "python-constraints": ["constraints.txt"],
            "python-requirements": ["requirements.txt"],
            "python-packages": ["pip", "some-pkg; sys_platform != 'win32'"],
        }
    )

    uv_plugin = UvPlugin(part_info=part_info, properties=properties)
    venv_dir = uv_plugin._part_info.part_install_dir
    assert uv_plugin.get_build_commands() == [
        f'uv venv --relocatable --allow-existing --python "{uv_plugin._get_system_python_interpreter()}" "{venv_dir}"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{venv_dir}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        "uv sync --no-dev --no-editable",
        *get_build_commands(new_dir),
    ]


def test_invalid_properties():
    with pytest.raises(ValidationError) as raised:
        UvPlugin.properties_class.unmarshal({"source": ".", "uv-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("uv-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_properties():
    with pytest.raises(ValidationError) as raised:
        UvPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


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


def test_call_should_remove_symlinks(plugin, new_dir, monkeypatch):
    monkeypatch.setattr(UvPlugin, "_should_remove_symlinks", lambda _s: True)

    venv_dir = plugin._part_info.part_install_dir
    assert plugin.get_build_commands() == [
        f'uv venv --relocatable --allow-existing --python "{plugin._get_system_python_interpreter()}" "{venv_dir}"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{venv_dir}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        "uv sync --no-dev --no-editable",
        *get_build_commands(new_dir, should_remove_symlinks=True),
    ]
