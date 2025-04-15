# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
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

import pathlib
import textwrap

import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors
from py import path  # type: ignore[import-untyped]


@pytest.fixture
def cargo_project(new_dir: path.LocalPath) -> pathlib.Path:
    (new_dir / "Cargo.toml").write_text(
        textwrap.dedent(
            """\
            [package]
            name = "craft-core"
            version = "1.2.4"
            """
        ),
        encoding="utf-8",
    )
    return pathlib.Path(new_dir)


def test_cargo_use(
    new_dir: path.LocalPath, cargo_project: pathlib.Path, partitions
) -> None:
    """Test cargo registry plugin"""
    parts_yaml = textwrap.dedent(
        """\
        parts:
          craft-core:
            source: .
            plugin: cargo-use
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_cargo_use",
        cache_dir=pathlib.Path(new_dir),
        work_dir=pathlib.Path(new_dir),
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    cargo_registry = lf.project_info.dirs.backstage_dir / "cargo-registry"
    part_registry_entry = cargo_registry / "craft-core-1.2.4"
    assert cargo_registry.is_dir(), "Cargo registry directory should be created."
    assert part_registry_entry.is_dir(), "Part registry entry should be created."

    assert (part_registry_entry / ".cargo-checksum.json").read_text() == '{"files":{}}'

    configuration_file = pathlib.Path(new_dir) / "cargo" / "config.toml"
    assert configuration_file.exists(), "config.toml should be created"
    assert configuration_file.read_text() == textwrap.dedent(
        f"""\
        [source.craft-parts]
        directory = "{cargo_registry}"

        [source.apt]
        directory = "/usr/share/cargo/registry"

        [source.crates-io]
        replace-with = "craft-parts"
        """
    )


def test_cargo_use_on_non_rust_sources(new_dir: path.LocalPath, partitions) -> None:
    """Test cargo registry plugin"""
    parts_yaml = textwrap.dedent(
        """\
        parts:
          craft-core:
            source: .
            plugin: cargo-use
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_cargo_use",
        cache_dir=pathlib.Path(new_dir),
        work_dir=pathlib.Path(new_dir),
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with pytest.raises(
        errors.PartsError,
        match="Cannot use 'cargo-use' plugin on non-Rust project.",
    ):
        with lf.action_executor() as ctx:
            ctx.execute(actions)


def test_cargo_use_multiple(new_dir: path.LocalPath, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          librust-cf-if:
            source: https://github.com/rust-lang/cfg-if.git
            source-tag: 1.0.0
            plugin: cargo-use
          librust-zerocopy:
            source: https://github.com/google/zerocopy.git
            source-tag: v0.8.24
            plugin: cargo-use
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_cargo_use",
        cache_dir=pathlib.Path(new_dir),
        work_dir=pathlib.Path(new_dir),
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    cargo_registry = lf.project_info.dirs.backstage_dir / "cargo-registry"
    assert cargo_registry.is_dir(), "Cargo registry directory should be created."

    part_registry_entry = cargo_registry / "cfg-if-1.0.0"
    assert part_registry_entry.is_dir(), "Part registry entry should be created."
    assert (part_registry_entry / ".cargo-checksum.json").read_text() == '{"files":{}}'

    part_registry_entry = cargo_registry / "zerocopy-0.8.24"
    assert part_registry_entry.is_dir(), "Part registry entry should be created."
    assert (part_registry_entry / ".cargo-checksum.json").read_text() == '{"files":{}}'
