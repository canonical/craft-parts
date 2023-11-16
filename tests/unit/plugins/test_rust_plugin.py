# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022-2023 Canonical Ltd.
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
import subprocess

import pytest
import pytest_subprocess
from pydantic import ValidationError

from craft_parts.errors import PluginEnvironmentValidationError
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.rust_plugin import GET_RUSTUP_COMMAND_TEMPLATE, RustPlugin


@pytest.fixture
def part_info(new_dir):
    yield PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_get_build_snaps(part_info):
    properties = RustPlugin.properties_class.unmarshal({"source": "."})
    plugin = RustPlugin(properties=properties, part_info=part_info)
    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = RustPlugin.properties_class.unmarshal({"source": "."})
    plugin = RustPlugin(properties=properties, part_info=part_info)
    assert plugin.get_build_packages() == {
        "curl",
        "gcc",
        "git",
        "pkg-config",
        "findutils",
    }


def test_get_build_environment(part_info):
    properties = RustPlugin.properties_class.unmarshal({"source": "."})
    plugin = RustPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {"PATH": "${HOME}/.cargo/bin:${PATH}"}


def test_get_build_commands_default(part_info):
    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "rust-channel": "stable"}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = lambda: False

    commands = plugin.get_build_commands()
    assert plugin.get_pull_commands()[0] == GET_RUSTUP_COMMAND_TEMPLATE.format(
        channel="stable"
    )
    assert 'cargo install -f --locked --path "."' in commands[0]


def test_get_build_commands_no_install(part_info):
    def _check_rustup():
        raise RuntimeError("should not be called")

    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "rust-channel": "none"}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = _check_rustup

    commands = plugin.get_build_commands()
    assert len(commands) == 1
    assert plugin.get_pull_commands() == []
    assert 'cargo install -f --locked --path "."' in commands[0]


def test_get_build_commands_use_lto(part_info):
    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "rust-use-global-lto": True, "rust-channel": "stable"}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = lambda: True

    commands = plugin.get_build_commands()
    assert len(commands) == 1
    assert "curl" not in plugin.get_pull_commands()[0]
    assert 'cargo install -f --locked --path "."' in commands[0]
    assert "--config 'profile.release.lto = true'" in commands[0]


def test_get_build_commands_multiple_crates(part_info):
    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "rust-path": ["a", "b", "c"], "rust-channel": "stable"}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = lambda: True

    commands = plugin.get_build_commands()
    assert len(commands) == 3
    assert "curl" not in plugin.get_pull_commands()[0]
    assert 'cargo install -f --locked --path "a"' in commands[0]
    assert 'cargo install -f --locked --path "b"' in commands[1]
    assert 'cargo install -f --locked --path "c"' in commands[2]


def test_get_build_commands_multiple_features(part_info):
    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "rust-features": ["ft-a", "ft-b"], "rust-channel": "stable"}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = lambda: True

    commands = plugin.get_build_commands()
    assert len(commands) == 1
    assert "curl" not in plugin.get_pull_commands()[0]
    assert 'cargo install -f --locked --path "."' in commands[0]
    assert "--features 'ft-a ft-b'" in commands[0]


@pytest.mark.parametrize(
    "value",
    [
        "stable",
        "nightly",
        "beta",
        "1.65",
        "1.71.1",
        "nightly-2022-12-01",
        "stable-x86_64-fortanix-unknown-sgx",
        "nightly-2023-06-14-aarch64-nintendo-switch-freestanding",
    ],
)
def test_get_build_commands_different_channels(part_info, value):
    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "rust-channel": value}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = lambda: False
    commands = plugin.get_build_commands()
    assert len(commands) == 1
    assert f"--default-toolchain {value}" in plugin.get_pull_commands()[0]


@pytest.mark.parametrize(
    "rust_path",
    [None, "i am a string", {"i am": "a dictionary"}, ["duplicate", "duplicate"]],
)
def test_get_build_commands_rust_path_invalid(rust_path, part_info):
    with pytest.raises(ValidationError):
        RustPlugin.properties_class.unmarshal({"source": ".", "rust-path": rust_path})


def test_error_on_conflict_config(part_info):
    properties = RustPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "rust-path": ["a", "b", "c"],
            "after": ["rust-deps"],
            "rust-channel": "stable",
        }
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    validator = plugin.validator_class(
        part_name="my-part", properties=properties, env=""
    )
    with pytest.raises(PluginEnvironmentValidationError):
        validator.validate_environment(part_dependencies=["rust-deps"])


@pytest.mark.parametrize(
    ("rustc_stdout", "cargo_stdout", "pull_commands"),
    [
        pytest.param(
            "rustc 1.73.0 (cc66ad468 2023-10-03)",
            "cargo 1.73.0 (9c4383fb5 2023-08-26)",
            [],
            id="rustup",
        ),
        pytest.param(
            "rustc 1.66.1 (90743e729 2023-01-10) (built from a source tarball)",
            "cargo 1.66.1",
            [],
            id="jammy",
        ),
        pytest.param(
            "You don't have rust installed!",
            "You don't have rust installed!",
            [GET_RUSTUP_COMMAND_TEMPLATE.format(channel="stable")],
            id="not-installed",
        ),
    ],
)
def test_get_pull_commands_compat_no_exceptions(
    fake_process: pytest_subprocess.FakeProcess,
    part_info,
    rustc_stdout,
    cargo_stdout,
    pull_commands,
):
    fake_process.register(["rustc", "--version"], stdout=rustc_stdout)
    fake_process.register(["cargo", "--version"], stdout=cargo_stdout)

    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "after": ["rust-deps"]}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)
    plugin._check_rustup = lambda: False  # type: ignore[method-assign]

    commands = plugin.get_build_commands()
    assert plugin.get_pull_commands() == pull_commands
    assert 'cargo install -f --locked --path "."' in commands[0]


@pytest.mark.parametrize(
    "exc_class", [subprocess.CalledProcessError, FileNotFoundError]
)
@pytest.mark.parametrize("failed_command", ["rustc", "cargo", "rustup"])
def test_get_pull_commands_compat_with_exceptions(
    fake_process: pytest_subprocess.FakeProcess, part_info, failed_command, exc_class
):
    fake_process.register(["rustc", "--version"])
    fake_process.register(["cargo", "--version"])
    fake_process.register(["rustup", "--version"])

    def callback_fail():
        raise exc_class()

    fake_process.register([failed_command, "--version"], callback=callback_fail)

    properties = RustPlugin.properties_class.unmarshal(
        {"source": ".", "after": ["rust-deps"]}
    )
    plugin = RustPlugin(properties=properties, part_info=part_info)

    assert plugin.get_pull_commands() == [
        GET_RUSTUP_COMMAND_TEMPLATE.format(channel="stable")
    ]


def test_get_out_of_source_build(part_info):
    properties = RustPlugin.properties_class.unmarshal({"source": "."})
    plugin = RustPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False
