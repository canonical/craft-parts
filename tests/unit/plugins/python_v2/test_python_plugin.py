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
import subprocess
from textwrap import dedent

import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.python_v2.python_plugin import PythonPlugin

# A build-time interpreter path, as pip would embed it in script shebangs.
# Its value doesn't matter to the rewrite command; only that scripts match it.
_PIP_PYTHON = "/build/parts/p1/install/usr/bin/python3"

# The default runtime interpreter, from _get_runtime_python_interpreter.
_RUNTIME = "/usr/bin/python3"


def _plain_shebang(interpreter: str, args: str = "") -> bytes:
    """A pip console script with a plain shebang."""
    return f"#!{interpreter}{args}\nprint('hello')\n".encode()


def _polyglot_shebang(interpreter: str) -> bytes:
    """A pip console script with the polyglot header used for long paths."""
    return (
        b"#!/bin/sh\n"
        + f"'''exec' {interpreter} \"$0\" \"$@\"\n".encode()
        + b"' '''\n# -*- coding: utf-8 -*-\nprint('hello')\n"
    )


def _make_plugin(part_info, runtime_interpreter: str) -> PythonPlugin:
    """Build a python plugin whose scripts rewrite to the given interpreter."""

    class CustomPlugin(PythonPlugin):
        def _get_runtime_python_interpreter(self) -> str:
            return runtime_interpreter

    properties = CustomPlugin.properties_class.unmarshal({"source": "."})
    return CustomPlugin(part_info=part_info, properties=properties)


def _run_plugin_rewrite(plugin: PythonPlugin, install_dir) -> None:
    """Run a plugin's shebang-rewrite command against an install dir."""
    env = {
        "CRAFT_PART_INSTALL": str(install_dir),
        "PIP_PYTHON": _PIP_PYTHON,
        "PATH": "/usr/bin:/bin",
    }
    subprocess.run(
        ["bash", "-c", plugin._get_rewrite_shebangs_command()],
        env=env,
        check=True,
    )


def _rewrite(
    script_content: bytes, runtime_interpreter: str, part_info, work_dir
) -> bytes:
    """Run the plugin's rewrite command on a pip script and return the result."""
    install_dir = work_dir / "install"
    bin_dir = install_dir / "bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "script"
    script.write_bytes(script_content)
    script.chmod(0o755)

    _run_plugin_rewrite(_make_plugin(part_info, runtime_interpreter), install_dir)
    # The rewrite must preserve the script's executable mode.
    assert script.stat().st_mode & 0o777 == 0o755
    return script.read_bytes()


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
    assert len(commands) == 7

    project_line = dedent("""\
      if [ -f setup.py -o -f pyproject.toml ]; then
        PACKAGES+=(".")
      fi
    """)

    assert commands[1:4] == [
        "REQUIREMENTS=(-r requirements.txt)",
        "PACKAGES=(black)",
        project_line,
    ]

    rewrite_command = commands[-2]
    assert rewrite_command.startswith(
        "# Rewrite the build-time shebangs of the scripts installed by pip."
    )
    assert "runtime_interp=/usr/bin/python3" in rewrite_command

    assert commands[-1].startswith("# Add a sitecustomize")


def test_get_build_commands_custom_runtime_interpreter(part_info):
    """An app-specific subclass controls the shebang that scripts end up with."""
    python_plugin = _make_plugin(part_info, "/snap/my-snap/current/bin/python3")

    rewrite_command = python_plugin.get_build_commands()[-2]
    assert "runtime_interp=/snap/my-snap/current/bin/python3" in rewrite_command
    assert "runtime_interp=/usr/bin/python3" not in rewrite_command


# Each case is (script as pip wrote it, runtime interpreter, expected script).
@pytest.mark.parametrize(
    ("content", "runtime_interpreter", "expected"),
    [
        # Plain shebang, short path.
        pytest.param(
            _plain_shebang(_PIP_PYTHON),
            _RUNTIME,
            _plain_shebang(_RUNTIME),
            id="plain",
        ),
        # Plain shebang with interpreter arguments, which must be preserved.
        pytest.param(
            _plain_shebang(_PIP_PYTHON, " -Es"),
            _RUNTIME,
            _plain_shebang(_RUNTIME, " -Es"),
            id="args-preserved",
        ),
        # Polyglot header, written by pip when the path is over the kernel's
        # shebang limit. Only the 3-line header is collapsed; the body,
        # including pip's coding comment, survives intact.
        pytest.param(
            _polyglot_shebang(_PIP_PYTHON),
            _RUNTIME,
            b"#!/usr/bin/python3\n# -*- coding: utf-8 -*-\nprint('hello')\n",
            id="polyglot",
        ),
        # Runtime interpreter paths with characters that are special to the
        # shell or to sed's replacement syntax (all legal in POSIX paths).
        pytest.param(
            _plain_shebang(_PIP_PYTHON),
            "/snap/a&b/current/bin/python3",
            _plain_shebang("/snap/a&b/current/bin/python3"),
            id="ampersand",
        ),
        pytest.param(
            _polyglot_shebang(_PIP_PYTHON),
            "/snap/a&b/current/bin/python3",
            b"#!/snap/a&b/current/bin/python3\n# -*- coding: utf-8 -*-\nprint('hello')\n",
            id="ampersand-polyglot",
        ),
        pytest.param(
            _plain_shebang(_PIP_PYTHON),
            "/opt/a|b/bin/python3",
            _plain_shebang("/opt/a|b/bin/python3"),
            id="pipe",
        ),
        pytest.param(
            _plain_shebang(_PIP_PYTHON),
            "/opt/a\\b/bin/python3",
            _plain_shebang("/opt/a\\b/bin/python3"),
            id="backslash",
        ),
        pytest.param(
            _polyglot_shebang(_PIP_PYTHON),
            "/opt/it's-here/bin/python3",
            b"#!/opt/it's-here/bin/python3\n# -*- coding: utf-8 -*-\nprint('hello')\n",
            id="single-quote",
        ),
        pytest.param(
            _plain_shebang(_PIP_PYTHON),
            "/opt/my dir/bin/python3",
            _plain_shebang("/opt/my dir/bin/python3"),
            id="space",
        ),
    ],
)
def test_rewrite_shebangs(part_info, new_path, content, runtime_interpreter, expected):
    """The rewrite command transforms pip script shebangs as expected."""
    assert _rewrite(content, runtime_interpreter, part_info, new_path) == expected


@pytest.mark.parametrize(
    "content",
    [
        # A script that pip did not generate.
        pytest.param(b"#!/bin/sh\necho hello\n", id="other-sh"),
        # A polyglot that executes a different interpreter.
        pytest.param(_polyglot_shebang("/bin/something-else"), id="other-polyglot"),
        # An already-correct shebang.
        pytest.param(_plain_shebang(_RUNTIME), id="already-correct"),
        # A binary file.
        pytest.param(b"\x7fELF\x00binary garbage\n", id="binary"),
    ],
)
def test_rewrite_shebangs_leaves_other_files_alone(part_info, new_path, content):
    """The rewrite command does not touch files that are not pip scripts."""
    assert _rewrite(content, _RUNTIME, part_info, new_path) == content


def test_rewrite_shebangs_scoped_to_bin_dir(part_info, new_path):
    """Files outside bin/ and symlinks in bin/ are not inspected."""
    install_dir = new_path / "install"
    bin_dir = install_dir / "bin"
    bin_dir.mkdir(parents=True)
    target = bin_dir / "plain"
    target.write_bytes(_plain_shebang(_PIP_PYTHON))
    target.chmod(0o755)
    (bin_dir / "link").symlink_to("plain")

    data_dir = install_dir / "share"
    data_dir.mkdir()
    (data_dir / "build-info").write_bytes(_plain_shebang(_PIP_PYTHON))

    _run_plugin_rewrite(_make_plugin(part_info, _RUNTIME), install_dir)

    assert target.read_bytes() == _plain_shebang(_RUNTIME)
    assert (bin_dir / "link").is_symlink()
    assert (data_dir / "build-info").read_bytes() == _plain_shebang(_PIP_PYTHON)


def test_rewrite_shebangs_no_bin_dir(part_info, new_path):
    """The rewrite command succeeds and creates nothing when pip installed no scripts."""
    install_dir = new_path / "install"
    install_dir.mkdir()

    _run_plugin_rewrite(_make_plugin(part_info, _RUNTIME), install_dir)

    assert list(install_dir.iterdir()) == []


@pytest.mark.parametrize(
    "package",
    [
        "gunicorn~=26.0",
        "gunicorn>=26.0",
        "gunicorn<27.0",
        "gunicorn!=26.0",
    ],
)
def test_get_build_commands_quotes_package_arguments(new_dir, package):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PythonPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "python-packages": [package],
        }
    )

    python_plugin = PythonPlugin(part_info=part_info, properties=properties)

    commands = python_plugin.get_build_commands()

    assert f"PACKAGES=('{package}')" in commands
    assert 'pip install "${REQUIREMENTS[@]}" "${PACKAGES[@]}"' in commands


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
