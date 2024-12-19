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
    ("has_poetry", "part_deps", "expected_added_poetry"),
    [
        (False, set(), True),
        (False, {"poetry-deps"}, False),
        (True, {"poetry-deps"}, False),
        (True, set(), False),
    ],
)
def test_get_build_packages(
    monkeypatch,
    plugin: PoetryPlugin,
    has_poetry,
    part_deps,
    expected_added_poetry,
):
    monkeypatch.setattr(plugin, "_system_has_poetry", lambda: has_poetry)
    plugin._part_info._part_dependencies = part_deps
    assert plugin._part_info.part_dependencies == part_deps

    obtained = plugin.get_build_packages()
    added_poetry = "python3-poetry" in obtained

    assert added_poetry == expected_added_poetry


@pytest.mark.parametrize(
    ("optional_groups", "poetry_extra_args", "export_addendum"),
    [
        (set(), [], ""),
        ({"dev"}, [], " --with=dev"),
        ({"toml", "yaml", "silly-walks"}, [], " --with=silly-walks,toml,yaml"),
        (set(), ["--no-binary=:all:"], " --no-binary=:all:"),
    ],
)
@pytest.mark.parametrize(
    ("pip_extra_args", "pip_addendum"),
    [
        ([], ""),
        (["--no-binary=:all:"], "--no-binary=:all:"),
        (["--pre", "-U"], "--pre -U"),
    ],
)
def test_get_install_commands(
    new_dir,
    optional_groups,
    poetry_extra_args,
    export_addendum,
    pip_extra_args,
    pip_addendum,
):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PoetryPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "poetry-with": optional_groups,
            "poetry-export-extra-args": poetry_extra_args,
            "poetry-pip-extra-args": pip_extra_args,
        }
    )

    plugin = PoetryPlugin(part_info=part_info, properties=properties)

    requirements = new_dir / "parts" / "p1" / "build" / "requirements.txt"
    pip = new_dir / "parts" / "p1" / "install" / "bin" / "pip"
    assert plugin._get_package_install_commands() == [
        f"poetry export --format=requirements.txt --output={requirements} --with-credentials"
        + export_addendum,
        f"{pip} install {pip_addendum} --requirement={requirements}",
        f"{pip} install --no-deps .",
        f"{pip} check",
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
