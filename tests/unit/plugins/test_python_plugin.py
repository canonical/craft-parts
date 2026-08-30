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

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.python_plugin import PythonPlugin
from pydantic import ValidationError


@pytest.fixture
def plugin(new_dir):
    properties = PythonPlugin.properties_class.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return PythonPlugin(properties=properties, part_info=part_info)


def test_get_install_commands_with_all_properties(new_dir):
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

    assert python_plugin._get_package_install_commands() == [
        f"{new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U pip 'some-pkg; sys_platform != '\"'\"'win32'\"'\"''",
        f"{new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U -r 'requirements.txt'",
        f"[ -f setup.py ] || [ -f pyproject.toml ] && {new_dir}/parts/p1/install/bin/pip install -c 'constraints.txt' -U .",
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
