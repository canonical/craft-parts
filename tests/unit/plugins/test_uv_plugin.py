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

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.uv_plugin import UvPlugin
from pydantic import ValidationError


@pytest.fixture
def plugin(new_dir):
    properties = UvPlugin.properties_class.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    return UvPlugin(properties=properties, part_info=part_info)


@pytest.mark.parametrize(
    ("extras", "extras_expected"),
    [
        pytest.param(set(), "", id="no-extras"),
        pytest.param(
            {
                "queso",
            },
            " --extra queso",
            id="one-extra",
        ),
        pytest.param(
            {
                "queso",
                "guac",
            },
            " --extra guac --extra queso",
            id="multi-extras",
        ),
    ],
)
@pytest.mark.parametrize(
    ("groups", "groups_expected"),
    [
        pytest.param(set(), "", id="no-groups"),
        pytest.param(
            {
                "archaea",
            },
            " --group archaea",
            id="one-group",
        ),
        pytest.param(
            {"archaea", "bacteria", "eukarya"},
            " --group archaea --group bacteria --group eukarya",
            id="multi-groups",
        ),
    ],
)
def test_get_install_commands(
    new_dir,
    extras: set[str],
    extras_expected: str,
    groups: set[str],
    groups_expected: str,
):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = UvPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "uv-extras": extras,
            "uv-groups": groups,
        }
    )

    uv_plugin = UvPlugin(part_info=part_info, properties=properties)

    assert uv_plugin._get_package_install_commands() == [
        f"uv sync --no-dev --no-editable{extras_expected}{groups_expected}"
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
