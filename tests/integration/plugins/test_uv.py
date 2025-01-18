# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2025 Canonical Ltd.
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
import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import craft_parts.plugins.plugins
import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors, plugins
from overrides import override


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


@pytest.fixture
def uv_parts_simple() -> dict[str, Any]:
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: uv
            source: "{Path(__file__).parent / "test_uv"}"
        """
    )

    return cast(dict[str, Any], yaml.safe_load(parts_yaml))


def test_uv_plugin(new_dir, partitions, uv_parts_simple):
    """Prime a simple python source."""
    lf = LifecycleManager(
        uv_parts_simple,
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "bin", "mytestuv")
    assert primed_script.exists()

    output = subprocess.getoutput(str(primed_script))
    assert output == "it works with uv too!"


def test_uv_plugin_symlink(new_dir, partitions, uv_parts_simple):
    """Run in the standard scenario with no overrides."""
    lf = LifecycleManager(
        uv_parts_simple,
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.is_symlink()

    # In regular Ubuntu this would be /usr/bin/python3.* but in GH this can be
    # something like /opt/hostedtoolcache/Python/3.9.16/x64/bin/python3.9
    assert os.path.isabs(python_link)
    assert os.path.basename(python_link).startswith("python3")


def test_uv_plugin_override_get_system_interpreter(
    new_dir, partitions, uv_parts_simple
):
    """Override the system interpreter, link should use it."""

    class MyUvPlugin(craft_parts.plugins.plugins.UvPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            return sys.executable

    plugins.register({"uv": MyUvPlugin})

    lf = LifecycleManager(
        uv_parts_simple,
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python")
    assert python_link.is_symlink()
    assert python_link.resolve() == Path(sys.executable).resolve()


@pytest.mark.parametrize("remove_symlinks", [(True), (False)])
def test_uv_plugin_no_system_interpreter(
    new_dir, partitions, uv_parts_simple, remove_symlinks: bool  # noqa: FBT001
):
    """Check that the build fails if a payload interpreter is needed but not found."""

    class MyUvPlugin(craft_parts.plugins.plugins.UvPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            return None

        @override
        def _should_remove_symlinks(self) -> bool:
            # Parametrize this to make sure that the build fails even if the
            # venv symlinks will be removed.
            return remove_symlinks

    plugins.register({"uv": MyUvPlugin})

    lf = LifecycleManager(
        uv_parts_simple,
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx, pytest.raises(errors.PluginBuildError):
        ctx.execute(actions)


def test_uv_plugin_remove_symlinks(new_dir, partitions, uv_parts_simple):
    """Override symlink removal."""

    class MyUvPlugin(craft_parts.plugins.plugins.UvPlugin):
        @override
        def _should_remove_symlinks(self) -> bool:
            return True

    plugins.register({"uv": MyUvPlugin})

    lf = LifecycleManager(
        uv_parts_simple,
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python")
    assert python_link.exists() is False


@pytest.fixture
def uv_parts_complex() -> Callable[[str, str], dict[str, Any]]:
    """A part whose override-build copies the system's Python interpreter
    into the payload"""

    def _inner(
        payload_python: str,
        real_python: str,
        *,
        source: Path = Path(__file__).parent / "test_uv",
    ) -> dict[str, Any]:
        parts_yaml = textwrap.dedent(
            f"""\
            parts:
              foo:
                plugin: uv
                source: {source}
                override-build: |
                  # Put a binary called "{payload_python}" in the payload
                  mkdir -p ${{CRAFT_PART_INSTALL}}/usr/bin
                  cp {real_python} ${{CRAFT_PART_INSTALL}}/usr/bin/{payload_python}
                  craftctl default
            """
        )

        return cast(dict[str, Any], yaml.safe_load(parts_yaml))

    return _inner


def test_find_payload_python_bad_version(new_dir, partitions, uv_parts_complex):
    """Test that the build fails if a payload interpreter is needed but it's the
    wrong Python version."""

    class MyUvPlugin(craft_parts.plugins.plugins.UvPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            # To have the build fail after failing to find the payload interpreter
            return "python3.3"

    plugins.register({"uv": MyUvPlugin})

    real_python = Path(sys.executable).resolve()

    # Copy the "real" binary into the payload before calling the plugin's build,
    # but name it "python3.3".
    lf = LifecycleManager(
        uv_parts_complex(real_python=real_python, payload_python="python3.3"),
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    out = Path("out.txt")
    with out.open(mode="w") as outfile, pytest.raises(errors.PluginBuildError):
        with lf.action_executor() as ctx:
            ctx.execute(actions, stdout=outfile, stderr=outfile)

    output = out.read_text()
    assert "Invalid version request:" in output


def test_find_payload_python_good_version(new_dir, partitions, uv_parts_complex):
    """Test that the build succeeds if a payload interpreter is needed, and it's
    the right Python version."""

    real_python = Path(sys.executable).resolve()
    real_basename = real_python.name
    install_dir = Path("parts/foo/install")

    # Copy the "real" binary into the payload before calling the plugin's build.
    lf = LifecycleManager(
        uv_parts_complex(real_python=real_python, payload_python=real_basename),
        application_name="test_uv",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    out = Path("out.txt")
    with out.open(mode="w") as outfile:
        with lf.action_executor() as ctx:
            ctx.execute(actions, stdout=outfile)

    output = out.read_text()
    payload_python = (install_dir / f"usr/bin/{real_basename}").resolve()
    expected_text = textwrap.dedent(
        f"""\
        Looking for a Python interpreter called "{real_basename}" in the payload...
        Found interpreter in payload: "{payload_python}"
        """
    )
    assert expected_text in output
