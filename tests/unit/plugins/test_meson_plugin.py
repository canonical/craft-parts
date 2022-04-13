# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path

import pytest
from pydantic import ValidationError

from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.meson_plugin import MesonPlugin


@pytest.fixture
def meson_exe(new_dir):
    meson_bin = Path(new_dir, "mock_bin", "meson")
    meson_bin.parent.mkdir(exist_ok=True)
    meson_bin.write_text('#!/bin/sh\necho "1.13.8"')
    meson_bin.chmod(0o755)
    yield meson_bin


@pytest.fixture
def broken_meson_exe(new_dir):
    meson_bin = Path(new_dir, "mock_bin", "meson")
    meson_bin.parent.mkdir(exist_ok=True)
    meson_bin.write_text("#!/bin/sh\nexit 33")
    meson_bin.chmod(0o755)
    yield meson_bin


@pytest.fixture
def ninja_exe(new_dir):
    ninja_bin = Path(new_dir, "mock_bin", "ninja")
    ninja_bin.parent.mkdir(exist_ok=True)
    ninja_bin.write_text('#!/bin/sh\necho "2.13.8"')
    ninja_bin.chmod(0o755)
    yield ninja_bin


@pytest.fixture
def broken_ninja_exe(new_dir):
    ninja_bin = Path(new_dir, "mock_bin", "ninja")
    ninja_bin.parent.mkdir(exist_ok=True)
    ninja_bin.write_text("#!/bin/sh\nexit 33")
    ninja_bin.chmod(0o755)
    yield ninja_bin


@pytest.fixture
def part_info(new_dir):
    yield PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(meson_exe, ninja_exe, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(meson_exe.parent)}:{str(ninja_exe.parent)}"
    )
    validator.validate_environment()


def test_validate_environment_missing_meson(part_info, ninja_exe):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ninja_exe.parent)}"
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'meson' not found"


def test_validate_environment_missing_ninja(part_info, meson_exe):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(meson_exe.parent)}"
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ninja' not found"


def test_validate_environment_broken_meson(ninja_exe, broken_meson_exe, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(ninja_exe.parent)}:{str(broken_meson_exe.parent)}",
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'meson' failed with error code 33"


def test_validate_environment_broken_ninja(meson_exe, broken_ninja_exe, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part",
        env=f"PATH={str(meson_exe.parent)}:{str(broken_ninja_exe.parent)}",
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ninja' failed with error code 33"


def test_validate_environment_with_meson_and_ninja_part(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    validator.validate_environment(part_dependencies=["meson", "ninja"])


def test_validate_environment_without_meson_part(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=["ninja"])

    assert raised.value.reason == (
        "'meson' not found and part 'my-part' depends on a part named 'meson'"
    )


def test_validate_environment_without_ninja_part(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=["meson"])

    assert raised.value.reason == (
        "'ninja' not found and part 'my-part' depends on a part named 'ninja'"
    )


def test_out_of_source_build(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.out_of_source_build is True


def test_get_build_snaps(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


def test_get_build_environment(new_dir, part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


def test_get_build_commands(part_info):
    properties = MesonPlugin.properties_class.unmarshal({"source": "."})
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        f"meson {plugin._part_info.part_src_dir}",
        "ninja",
        f"DESTDIR={plugin._part_info.part_install_dir} ninja install",
    ]


def test_get_build_commands_with_parameters(part_info):
    properties = MesonPlugin.properties_class.unmarshal(
        {"source": ".", "meson-parameters": ["--debug", "--prefix=foo bar"]}
    )
    plugin = MesonPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        f"meson {plugin._part_info.part_src_dir} --debug '--prefix=foo bar'",
        "ninja",
        f"DESTDIR={plugin._part_info.part_install_dir} ninja install",
    ]


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        MesonPlugin.properties_class.unmarshal({"source": ".", "meson-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("meson-invalid",)
    assert err[0]["type"] == "value_error.extra"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        MesonPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "value_error.missing"
