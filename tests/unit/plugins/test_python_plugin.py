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

import csv
import email.policy
from email.message import EmailMessage
from pathlib import Path
from textwrap import dedent

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.base import Package
from craft_parts.plugins.python_plugin import PythonPlugin
from pydantic import ValidationError


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
        *postfix,
    ]


def test_get_build_commands(plugin, new_dir):
    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        f"{new_dir}/parts/p1/install/bin/pip install  -U pip setuptools wheel",
        f"[ -f setup.py ] || [ -f pyproject.toml ] && {new_dir}/parts/p1/install/bin/pip install  -U .",
        *get_build_commands(new_dir),
    ]


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
        f"[ -f setup.py ] || [ -f pyproject.toml ] && {new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U .",
        *get_build_commands(new_dir),
    ]


def test_invalid_properties():
    with pytest.raises(ValidationError) as raised:
        PythonPlugin.properties_class.unmarshal({"source": ".", "python-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("python-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_properties():
    with pytest.raises(ValidationError) as raised:
        PythonPlugin.properties_class.unmarshal({})
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
        "craft_parts.plugins.python_plugin.PythonPlugin._should_remove_symlinks",
        return_value=True,
    )

    assert plugin.get_build_commands() == [
        f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{new_dir}/parts/p1/install"',
        f'PARTS_PYTHON_VENV_INTERP_PATH="{new_dir}/parts/p1/install/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        f"{new_dir}/parts/p1/install/bin/pip install  -U pip setuptools wheel",
        f"[ -f setup.py ] || [ -f pyproject.toml ] && {new_dir}/parts/p1/install/bin/pip install  -U .",
        *get_build_commands(new_dir, should_remove_symlinks=True),
    ]


def test_get_file_list(new_dir):
    part_info = PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )
    properties = PythonPlugin.properties_class.unmarshal({"source": "."})
    plugin = PythonPlugin(properties=properties, part_info=part_info)

    # Build a fake file tree, emulating what real package installs look like.
    # Integration tests actually install stuff and check a subset of the
    # large installed trees.
    pkgs_install_dir = plugin._part_info.part_install_dir / "lib/python/site-packages"
    bins_dir = plugin._part_info.part_install_dir / "bin"
    pkgs_install_dir.mkdir(parents=True)
    bins_dir.mkdir()

    def _mk_pkg(name, version, pkg_files, bin_files=None, dist_info_extra_files=None):
        pkg_dir = pkgs_install_dir / name
        dist_info_dir = pkgs_install_dir / f"{name}-{version}.dist-info"
        if not bin_files:
            bin_files = []
        if not dist_info_extra_files:
            dist_info_extra_files = []
        metadata_file = dist_info_dir / "METADATA"
        record_file = dist_info_dir / "RECORD"

        pkg_files_abs = [pkg_dir / f for f in pkg_files]
        bin_files_abs = [bins_dir / f for f in bin_files]
        dist_info_files_abs = [metadata_file, record_file] + [
            dist_info_dir / f for f in dist_info_extra_files
        ]
        all_files = bin_files_abs + pkg_files_abs + dist_info_files_abs
        for f in all_files:
            f.parent.mkdir(exist_ok=True, parents=True)
            f.touch()

        metadata = EmailMessage(policy=email.policy.compat32)
        metadata.add_header("Name", name)
        metadata.add_header("Version", version)
        with open(metadata_file, "w+") as f:
            f.write(metadata.as_string())

        # Columns 2 and 3 are sha and size, but we don't care
        file_data = [
            [f.relative_to(pkgs_install_dir, walk_up=True), None, None]
            for f in all_files
        ]

        with open(record_file, "w+", newline="") as f:
            csvwriter = csv.writer(f)
            csvwriter.writerows(file_data)

    _mk_pkg(
        "fakeee",
        "1.2.3-deb_ian",
        [
            "a_file.py",
            "things/stuff.py",
            "things/nothing.py",
        ],
        bin_files=["doit"],
        dist_info_extra_files=["REQUESTED", "LICENSE.txt"],
    )

    expected = {
        Package("fakeee", "1.2.3-deb_ian"): {
            bins_dir / "doit",
            pkgs_install_dir / "fakeee/a_file.py",
            pkgs_install_dir / "fakeee/things/stuff.py",
            pkgs_install_dir / "fakeee/things/nothing.py",
            pkgs_install_dir / "fakeee-1.2.3-deb_ian.dist-info/LICENSE.txt",
            pkgs_install_dir / "fakeee-1.2.3-deb_ian.dist-info/METADATA",
            pkgs_install_dir / "fakeee-1.2.3-deb_ian.dist-info/RECORD",
            pkgs_install_dir / "fakeee-1.2.3-deb_ian.dist-info/REQUESTED",
        },
    }

    actual = plugin.get_files()

    assert expected == actual
