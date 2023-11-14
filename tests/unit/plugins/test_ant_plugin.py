# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

import os
from unittest import mock

import pytest
from craft_parts import Part, PartInfo, ProjectInfo, errors
from craft_parts.plugins.ant_plugin import AntPlugin
from pydantic import ValidationError


@pytest.fixture()
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)
    ant = dependency_fixture(
        "ant", output="Apache Ant(TM) version 1.10.12 compiled on October 13 2021"
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ant.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_ant(part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ant' not found"


def test_validate_environment_broken_ant(dependency_fixture, part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)
    ant = dependency_fixture("ant", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ant.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'ant' failed with error code 33"


def test_validate_environment_invalid_ant(dependency_fixture, part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)
    ant = dependency_fixture("ant", invalid=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ant.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid ant version ''"


def test_validate_environment_with_ant_part(part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["ant-deps"])


def test_validate_environment_without_ant_part(part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'ant' not found and part 'my-part' does not depend on a part named "
        "'ant-deps' that would satisfy the dependency"
    )


def test_get_build_snaps_and_packages(part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == set()


def test_get_build_environment(part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


@pytest.mark.parametrize(
    "protocol,host,port,username,password",
    [
        ("http", "my-proxy-host", "", "", ""),
        ("http", "my-proxy-host", "3128", "", ""),
        ("http", "my-proxy-host", "3128", "ubuntu", ""),
        ("http", "my-proxy-host", "3128", "ubuntu", "ubuntu"),
        ("https", "my-proxy-host", "", "", ""),
        ("https", "my-proxy-host", "3128", "", ""),
        ("https", "my-proxy-host", "3128", "ubuntu", ""),
        ("https", "my-proxy-host", "3128", "ubuntu", "ubuntu"),
    ],
)
def test_get_build_environment_proxy(
    part_info, protocol, host, port, username, password
):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)
    if username != "" and password != "":
        env_dict = {
            f"{protocol}_proxy": f"http://{username}:{password}@{host}:{port}",
        }
    elif username != "":
        env_dict = {
            f"{protocol}_proxy": f"http://{username}@{host}:{port}",
        }
    elif port == "":
        env_dict = {
            f"{protocol}_proxy".format(protocol): f"http://{host}",
        }
    else:
        env_dict = {
            f"{protocol}_proxy".format(protocol): f"http://{host}:{port}",
        }
    with mock.patch.dict(os.environ, env_dict):
        ant_opts = ""
        if host != "":
            ant_opts = f"{ant_opts} -D{protocol}.proxyHost={host}"
        if port != "":
            ant_opts = f"{ant_opts} -D{protocol}.proxyPort={port}"
        if username != "":
            ant_opts = f"{ant_opts} -D{protocol}.proxyUser={username}"
        if password != "":
            ant_opts = f"{ant_opts} -D{protocol}.proxyPassword={password}"
        assert plugin.get_build_environment() == {"ANT_OPTS": ant_opts.strip()}


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        AntPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "value_error.missing"


def test_get_build_commands(part_info):
    properties = AntPlugin.properties_class.unmarshal({"source": "."})
    plugin = AntPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "ant",
        *plugin._get_java_post_build_commands(),
    ]


def test_get_build_commands_with_parameters(part_info):
    properties = AntPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "ant-build-targets": ["compile", "jar"],
            "ant-build-file": "myfile.txt",
            "ant-properties": {"prop1": "1", "prop2": "2"},
        }
    )
    plugin = AntPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == (
        [
            "ant -f myfile.txt -Dprop1=1 -Dprop2=2 compile jar",
            *plugin._get_java_post_build_commands(),
        ]
    )
