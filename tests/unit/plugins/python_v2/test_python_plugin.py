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
    assert "#!/usr/bin/python3" in rewrite_command

    assert commands[-1].startswith("# Add a sitecustomize")


def test_get_build_commands_custom_runtime_interpreter(new_dir):
    """An app-specific subclass controls the shebang that scripts end up with."""

    class CustomPlugin(PythonPlugin):
        def _get_runtime_python_interpreter(self) -> str:
            return "/snap/my-snap/current/bin/python3"

    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = CustomPlugin.properties_class.unmarshal({"source": "."})

    python_plugin = CustomPlugin(part_info=part_info, properties=properties)

    rewrite_command = python_plugin.get_build_commands()[-2]
    assert "#!/snap/my-snap/current/bin/python3" in rewrite_command
    assert "#!/usr/bin/python3" not in rewrite_command


def _get_rewrite_command(work_dir) -> str:
    """Extract the plugin's shebang-rewrite shell command."""
    info = ProjectInfo(application_name="test", cache_dir=work_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))
    properties = PythonPlugin.properties_class.unmarshal({"source": "."})
    python_plugin = PythonPlugin(part_info=part_info, properties=properties)
    return python_plugin._get_rewrite_shebangs_command()


# A build-time interpreter path, as pip would embed it in script shebangs.
# Its value doesn't matter to the rewrite command; only that scripts match it.
_PIP_PYTHON = "/build/parts/p1/install/usr/bin/python3"


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


def _run_rewrite_command(new_path) -> None:
    """Run the plugin's rewrite command against a fabricated install dir."""
    env = {
        "CRAFT_PART_INSTALL": str(new_path / "install"),
        "PIP_PYTHON": _PIP_PYTHON,
        "PATH": "/usr/bin:/bin",
    }
    subprocess.run(
        ["bash", "-c", _get_rewrite_command(new_path)],
        env=env,
        check=True,
    )


def _write_script(bin_dir, name, content):
    script = bin_dir / name
    script.write_bytes(content)
    script.chmod(0o755)
    return script


# Each case is a script as pip wrote it and the shebang expected after the
# rewrite.
@pytest.mark.parametrize(
    ("content", "expected_shebang"),
    [
        # Plain shebang, short path.
        pytest.param(
            _plain_shebang(_PIP_PYTHON),
            "#!/usr/bin/python3",
            id="plain",
        ),
        # Plain shebang with interpreter arguments, which must be preserved.
        pytest.param(
            _plain_shebang(_PIP_PYTHON, " -Es"),
            "#!/usr/bin/python3 -Es",
            id="args-preserved",
        ),
        # Polyglot header, written by pip when the path is over the kernel's
        # shebang limit.
        pytest.param(
            _polyglot_shebang(_PIP_PYTHON),
            "#!/usr/bin/python3",
            id="polyglot",
        ),
    ],
)
def test_rewrite_shebangs_command(new_path, content, expected_shebang):
    """Run the plugin's rewrite command on a pip-style script."""
    bin_dir = new_path / "install/bin"
    bin_dir.mkdir(parents=True)

    script = _write_script(bin_dir, "script", content)
    _run_rewrite_command(new_path)

    assert script.read_bytes().split(b"\n", 1)[0].decode() == expected_shebang


def test_rewrite_shebangs_command_preserves_polyglot_body(new_path):
    """Rewriting a polyglot shebang collapses the 3-line header only."""
    bin_dir = new_path / "install/bin"
    bin_dir.mkdir(parents=True)

    script = _write_script(bin_dir, "script", _polyglot_shebang(_PIP_PYTHON))
    _run_rewrite_command(new_path)

    # The body, including the coding comment that pip's template emits, must
    # survive the header collapse intact.
    assert script.read_bytes() == (
        b"#!/usr/bin/python3\n# -*- coding: utf-8 -*-\nprint('hello')\n"
    )


@pytest.mark.parametrize(
    "content",
    [
        # A script that pip did not generate.
        pytest.param(b"#!/bin/sh\necho hello\n", id="other-sh"),
        # A polyglot that executes a different interpreter.
        pytest.param(_polyglot_shebang("/bin/something-else"), id="other-polyglot"),
        # An already-correct shebang.
        pytest.param(_plain_shebang("/usr/bin/python3"), id="good"),
        # A binary file.
        pytest.param(b"\x7fELF\x00binary garbage\n", id="binary"),
    ],
)
def test_rewrite_shebangs_command_leaves_other_files_alone(new_path, content):
    """The rewrite command does not touch files that are not pip scripts."""
    bin_dir = new_path / "install/bin"
    bin_dir.mkdir(parents=True)

    script = _write_script(bin_dir, "script", content)
    _run_rewrite_command(new_path)

    assert script.read_bytes() == content


def test_rewrite_shebangs_command_scoped_to_bin_dir(new_path):
    """Files outside bin/ and symlinks in bin/ are not inspected."""
    bin_dir = new_path / "install/bin"
    bin_dir.mkdir(parents=True)

    target = _write_script(bin_dir, "plain", _plain_shebang(_PIP_PYTHON))
    (bin_dir / "link").symlink_to("plain")

    data_dir = new_path / "install/share"
    data_dir.mkdir()
    (data_dir / "build-info").write_bytes(_plain_shebang(_PIP_PYTHON))

    _run_rewrite_command(new_path)

    assert target.read_bytes() == _plain_shebang("/usr/bin/python3")
    assert (bin_dir / "link").is_symlink()
    assert (data_dir / "build-info").read_bytes() == _plain_shebang(_PIP_PYTHON)


def test_rewrite_shebangs_command_no_bin_dir(new_path):
    """The rewrite command succeeds when pip installed no scripts."""
    (new_path / "install").mkdir()

    _run_rewrite_command(new_path)


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
