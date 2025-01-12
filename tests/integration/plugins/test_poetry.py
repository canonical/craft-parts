# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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
import pathlib
import stat
import subprocess
import sys
import textwrap

import craft_parts.plugins.plugins
import pytest
import pytest_check  # type: ignore[import-untyped]
from craft_parts import LifecycleManager, Step, errors, plugins
from overrides import override


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


@pytest.fixture(params=["test_poetry"])
def source_directory(request):
    return pathlib.Path(__file__).parent / request.param


@pytest.fixture
def poetry_part(source_directory):
    return {
        "source": str(source_directory),
        "plugin": "poetry",
        "poetry-export-extra-args": ["--without-hashes"],
        "poetry-pip-extra-args": ["--no-deps"],
    }


@pytest.fixture
def parts_dict(poetry_part):
    return {"parts": {"foo": poetry_part}}


def test_poetry_plugin(new_dir, partitions, source_directory, parts_dict):
    """Prime a simple python source."""
    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = pathlib.Path(lf.project_info.prime_dir, "bin", "mytest")
    python_link = pathlib.Path(lf.project_info.prime_dir, "bin", "python3")
    with pytest_check.check():
        assert primed_script.exists()
        assert primed_script.open().readline().rstrip() == "#!/usr/bin/env python3"
        assert python_link.is_symlink()
    with pytest_check.check():
        assert python_link.readlink().is_absolute()
        # This is normally /usr/bin/python3.*, but if running in a venv
        # it could be elsewhere.
        assert python_link.name.startswith("python3")
        assert python_link.stat().st_mode & stat.S_IXOTH

    with pytest_check.check():
        result = subprocess.run(
            [python_link, primed_script], text=True, capture_output=True, check=False
        )
        assert result.stdout == "Test succeeded!\n"

    with pytest_check.check():
        result = subprocess.run(
            [python_link, "-m", "test_poetry"],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.stdout == "Test succeeded!\n"


def test_poetry_plugin_override_get_system_interpreter(
    new_dir, partitions, source_directory, parts_dict
):
    """Override the system interpreter, link should use it."""

    class MyPoetryPlugin(craft_parts.plugins.plugins.PoetryPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            return "use-this-python"

    plugins.register({"poetry": MyPoetryPlugin})

    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = pathlib.Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.is_symlink()
    assert os.readlink(python_link) == "use-this-python"


@pytest.mark.parametrize("remove_symlinks", [(True), (False)])
def test_poetry_plugin_no_system_interpreter(
    new_dir,
    partitions,
    remove_symlinks: bool,  # noqa: FBT001
    parts_dict,
):
    """Check that the build fails if a payload interpreter is needed but not found."""

    class MyPoetryPlugin(craft_parts.plugins.plugins.PoetryPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            return None

        @override
        def _should_remove_symlinks(self) -> bool:
            # Parametrize this to make sure that the build fails even if the
            # venv symlinks will be removed.
            return remove_symlinks

    plugins.register({"poetry": MyPoetryPlugin})

    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx, pytest.raises(errors.PluginBuildError):
        ctx.execute(actions)


def test_poetry_plugin_remove_symlinks(new_dir, partitions, parts_dict):
    """Override symlink removal."""

    class MyPoetryPlugin(craft_parts.plugins.plugins.PoetryPlugin):
        @override
        def _should_remove_symlinks(self) -> bool:
            return True

    plugins.register({"poetry": MyPoetryPlugin})

    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = pathlib.Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.exists() is False


def test_poetry_plugin_override_shebangs(new_dir, partitions, parts_dict):
    """Override what we want in script shebang lines."""

    class MyPoetryPlugin(craft_parts.plugins.plugins.PoetryPlugin):
        @override
        def _get_script_interpreter(self) -> str:
            return "#!/my/script/interpreter"

    plugins.register({"poetry": MyPoetryPlugin})

    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = pathlib.Path(lf.project_info.prime_dir, "bin/pip")
    assert primed_script.open().readline().rstrip() == "#!/my/script/interpreter"


def test_find_payload_python_bad_version(new_dir, partitions, parts_dict, poetry_part):
    """Test that the build fails if a payload interpreter is needed but it's the
    wrong Python version."""
    poetry_part["override-build"] = textwrap.dedent(
        f"""\
        # Put a binary called "python3.3" in the payload
        mkdir -p ${{CRAFT_PART_INSTALL}}/usr/bin
        cp {sys.executable} ${{CRAFT_PART_INSTALL}}/usr/bin/python3.3
        craftctl default
        """
    )

    class MyPoetryPlugin(craft_parts.plugins.plugins.PoetryPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            # To have the build fail after failing to find the payload interpreter
            return None

    plugins.register({"poetry": MyPoetryPlugin})

    real_python = pathlib.Path(sys.executable).resolve()
    real_basename = real_python.name

    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    out = pathlib.Path("out.txt")
    with out.open(mode="w") as outfile, pytest.raises(errors.PluginBuildError):
        with lf.action_executor() as ctx:
            ctx.execute(actions, stdout=outfile)

    output = out.read_text()
    expected_text = textwrap.dedent(
        f"""\
        Looking for a Python interpreter called "{real_basename}" in the payload...
        Python interpreter not found in payload.
        No suitable Python interpreter found, giving up.
        """
    )
    assert expected_text in output


def test_find_payload_python_good_version(new_dir, partitions, parts_dict, poetry_part):
    """Test that the build succeeds if a payload interpreter is needed, and it's
    the right Python version."""

    real_python = pathlib.Path(sys.executable).resolve()
    real_basename = real_python.name
    install_dir = pathlib.Path("parts/foo/install")
    # Copy the "real" binary into the payload before calling the plugin's build.
    poetry_part["override-build"] = textwrap.dedent(
        f"""\
        # Put a binary called "{real_basename}" in the payload
        mkdir -p ${{CRAFT_PART_INSTALL}}/usr/bin
        cp {sys.executable} ${{CRAFT_PART_INSTALL}}/usr/bin/{real_basename}
        craftctl default
        """
    )

    lf = LifecycleManager(
        parts_dict,
        application_name="test_poetry",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    out = pathlib.Path("out.txt")
    with out.open(mode="w") as outfile:
        with lf.action_executor() as ctx:
            ctx.execute(actions, stdout=outfile)

    output = out.read_text()
    payload_python = (install_dir / f"usr/bin/{real_basename}").resolve()
    expected_text = textwrap.dedent(
        f"""\
        Found interpreter in payload: "{payload_python}"
        """
    )
    assert expected_text in output
