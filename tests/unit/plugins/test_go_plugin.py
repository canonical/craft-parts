# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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
from craft_parts.plugins.go_plugin import GoPlugin


@pytest.fixture
def go_exe(new_dir):
    go_bin = Path(new_dir, "mock_bin", "go")
    go_bin.parent.mkdir(exist_ok=True)
    go_bin.write_text('#!/bin/sh\necho "go version go1.13.8 linux/amd64"')
    go_bin.chmod(0o755)
    yield go_bin


@pytest.fixture
def broken_go_exe(new_dir):
    go_bin = Path(new_dir, "mock_bin", "go")
    go_bin.parent.mkdir(exist_ok=True)
    go_bin.write_text("#!/bin/sh\nexit 33")
    go_bin.chmod(0o755)
    yield go_bin


@pytest.fixture
def invalid_go_exe(new_dir):
    go_bin = Path(new_dir, "mock_bin", "go")
    go_bin.parent.mkdir(exist_ok=True)
    go_bin.touch()
    go_bin.chmod(0o755)
    yield go_bin


@pytest.fixture
def part_info(new_dir):
    yield PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(go_exe, part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go_exe.parent)}"
    )
    validator.validate_environment()


def test_validate_environment_missing_go(part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "go compiler not found"


def test_validate_environment_broken_go(broken_go_exe, part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(broken_go_exe.parent)}"
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "go compiler failed with error code 33"


def test_validate_environment_invalid_go(invalid_go_exe, part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(invalid_go_exe.parent)}"
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid go compiler version ''"


def test_validate_environment_with_go_part(part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    validator.validate_environment(part_dependencies=["go"])


def test_validate_environment_without_go_part(part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "go compiler not found and part 'my-part' "
        "does not depend on a part named 'go'"
    )


def test_get_build_snaps(part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == {"gcc"}


def test_get_build_environment(new_dir, part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {
        "CGO_ENABLED": "1",
        "GOBIN": f"{new_dir}/parts/my-part/install/bin",
        "PARTS_GO_LDFLAGS": "-ldflags -linkmode=external",
    }


def test_get_build_commands(part_info):
    properties = GoPlugin.properties_class.unmarshal({"source": "."})
    plugin = GoPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "go mod download",
        'go install -p "1"  ${PARTS_GO_LDFLAGS} ./...',
    ]


def test_get_build_commands_with_buildtags(part_info):
    properties = GoPlugin.properties_class.unmarshal(
        {"source": ".", "go-buildtags": ["dev", "debug"]}
    )
    plugin = GoPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "go mod download",
        'go install -p "1" -tags=dev,debug ${PARTS_GO_LDFLAGS} ./...',
    ]


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        GoPlugin.properties_class.unmarshal({"source": ".", "go-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("go-invalid",)
    assert err[0]["type"] == "value_error.extra"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        GoPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "value_error.missing"
