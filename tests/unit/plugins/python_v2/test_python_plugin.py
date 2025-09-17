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
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.python_v2.python_plugin import PythonPlugin


def test_get_build_commands(new_dir):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PythonPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "python-requirements": ["requirements.txt"],
            "python-packages": ["black"],
        }
    )

    python_plugin = PythonPlugin(part_info=part_info, properties=properties)

    commands = python_plugin.get_build_commands()
    assert len(commands) == 5

    assert commands[1:4] == [
        "pip install -r requirements.txt",
        "pip install black",
        "[ -f setup.py -o -f pyproject.toml ] && pip install .",
    ]

    assert commands[-1].startswith("# Add a sitecustomize")


def test_get_build_environment(new_dir):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PythonPlugin.properties_class.unmarshal(
        {
            "source": ".",
        }
    )

    python_plugin = PythonPlugin(part_info=part_info, properties=properties)
    environment = python_plugin.get_build_environment()
    assert environment == {
        "PIP_USER": "1",
        "PYTHONUSERBASE": str(new_dir / "parts/p1/install"),
        "PIP_BREAK_SYSTEM_PACKAGES": "1",
        "PIP_PYTHON": "$(which python3)",
    }
