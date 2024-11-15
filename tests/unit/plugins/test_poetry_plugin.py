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
import pytest_check  # type: ignore[import-untyped]
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.poetry_plugin import PoetryPlugin
from pydantic import ValidationError


@pytest.fixture
def plugin(new_dir):
    properties = PoetryPlugin.properties_class.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return PoetryPlugin(properties=properties, part_info=part_info)


@pytest.mark.parametrize(
    ("has_poetry", "part_deps", "expected_packages"),
    [
        (False, set(), {"python3-poetry"}),
        (False, {"poetry-deps"}, set()),
        (True, {"poetry-deps"}, set()),
        (True, set(), set()),
    ],
)
def test_get_build_packages(
    monkeypatch, plugin: PoetryPlugin, has_poetry, part_deps, expected_packages: set
):
    monkeypatch.setattr(plugin, "_system_has_poetry", lambda: has_poetry)
    plugin._part_info.dependencies = part_deps  # type: ignore[attr-defined]

    assert plugin.get_build_packages().issuperset(expected_packages)


def test_get_build_environment(plugin, new_dir):
    assert plugin.get_build_environment() == {
        "PATH": f"{new_dir}/parts/p1/install/bin:${{PATH}}",
        "PARTS_PYTHON_INTERPRETER": "python3",
        "PARTS_PYTHON_VENV_ARGS": "",
    }


# pylint: disable=line-too-long


def get_build_commands(
    new_dir: Path, *, should_remove_symlinks: bool = False
) -> list[str]:
    if should_remove_symlinks:
        postfix = dedent(
            f"""\
            echo Removing python symlinks in {new_dir}/parts/p1/install/bin
            rm "{new_dir}/parts/p1/install"/bin/python*
            """
        )
    else:
        postfix = dedent(
            'ln -sf "${symlink_target}" "${PARTS_PYTHON_VENV_INTERP_PATH}"'
        )

    return [
        dedent(
            f"""\
            find "{new_dir}/parts/p1/install" -type f -executable -print0 | xargs --no-run-if-empty -0 \\
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
        postfix,
    ]


@pytest.mark.parametrize(
    ("optional_groups", "export_addendum"),
    [
        (set(), ""),
        ({"dev"}, " --with=dev"),
        ({"toml", "yaml", "silly-walks"}, " --with=silly-walks,toml,yaml"),
    ],
)
def test_get_build_commands(new_dir, optional_groups, export_addendum):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PoetryPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "poetry-with": optional_groups,
        }
    )

    plugin = PoetryPlugin(part_info=part_info, properties=properties)

    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        f"poetry export --format=requirements.txt --output={new_dir}/parts/p1/build/requirements.txt --with-credentials"
        + export_addendum,
        f"{new_dir}/parts/p1/install/bin/pip install --requirement={new_dir}/parts/p1/build/requirements.txt",
        f"{new_dir}/parts/p1/install/bin/pip install --no-deps .",
        f"{new_dir}/parts/p1/install/bin/pip check",
        *get_build_commands(new_dir),
    ]


def test_missing_properties():
    with pytest.raises(ValidationError) as raised:
        PoetryPlugin.properties_class.unmarshal({})
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


def test_call_should_remove_symlinks(plugin, new_dir, mocker):
    mocker.patch(
        "craft_parts.plugins.poetry_plugin.PoetryPlugin._should_remove_symlinks",
        return_value=True,
    )

    build_commands = plugin.get_build_commands()

    pytest_check.is_in(
        f"echo Removing python symlinks in {plugin._part_info.part_install_dir}/bin",
        build_commands,
    )
    pytest_check.is_in(
        f'rm "{plugin._part_info.part_install_dir}"/bin/python*', build_commands
    )
