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

from __future__ import annotations

import subprocess
from pathlib import Path

from craft_parts.packages.deb import Ubuntu


def test_get_installed_packages_uses_dpkg_query_when_available(monkeypatch):
    def fake_check_output(cmd, text=False, stderr=None):  # noqa: ANN001
        assert cmd[:2] == ["dpkg-query", "-W"]
        # Format: "<pkg>\t<status>\t<version>\n"
        return (
            "bash\tinstall ok installed\t5.2.15-2ubuntu1\n"
            "coreutils\tinstall ok installed\t9.4-3ubuntu6\n"
            "bash\tinstall ok installed\t5.2.15-2ubuntu1\n"
            "removed\tdeinstall ok config-files\t1.0\n"
            "\n"
        )

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    pkgs = Ubuntu.get_installed_packages()
    assert pkgs == ["bash=5.2.15-2ubuntu1", "coreutils=9.4-3ubuntu6"]


def test_get_installed_packages_dpkg_query_ignores_malformed_lines(monkeypatch):
    def fake_check_output(cmd, text=False, stderr=None):  # noqa: ANN001
        assert cmd[:2] == ["dpkg-query", "-W"]
        # Missing fields / wrong separators should be ignored.
        return (
            "bash install ok installed 5.2\n"
            "ok\tinstall ok installed\t1.2.3\n"
            "nover\tinstall ok installed\t\n"
        )

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    pkgs = Ubuntu.get_installed_packages()
    assert pkgs == ["ok=1.2.3"]


def test_get_installed_packages_fallback_parses_dpkg_status_and_flushes_last_stanza(
    monkeypatch, tmp_path
):
    # Force dpkg-query path to fail
    def boom(*a, **kw):  # noqa: ANN001
        raise subprocess.CalledProcessError(1, "dpkg-query")

    monkeypatch.setattr(subprocess, "check_output", boom)

    # Fake /var/lib/dpkg/status with NO trailing blank line on last stanza
    status = (
        "Package: aaa\n"
        "Status: install ok installed\n"
        "Version: 1.0\n"
        "\n"
        "Package: zzz\n"
        "Status: install ok installed\n"
        "Version: 9.9\n"
    )
    fake_status = tmp_path / "status"
    fake_status.write_text(status, encoding="utf-8")

    # Redirect Path('/var/lib/dpkg/status') to our temp file
    real_path = Path

    def fake_path(p):  # noqa: ANN001
        if p == "/var/lib/dpkg/status":
            return fake_status
        return real_path(p)

    monkeypatch.setattr("craft_parts.packages.deb.Path", fake_path)

    pkgs = Ubuntu.get_installed_packages()
    assert pkgs == ["aaa=1.0", "zzz=9.9"]


def test_get_installed_packages_fallback_ignores_not_installed(monkeypatch, tmp_path):
    def boom(*a, **kw):  # noqa: ANN001
        raise subprocess.CalledProcessError(1, "dpkg-query")

    monkeypatch.setattr(subprocess, "check_output", boom)

    status = (
        "Package: keep\n"
        "Status: install ok installed\n"
        "Version: 2.0\n"
        "\n"
        "Package: gone\n"
        "Status: deinstall ok config-files\n"
        "Version: 1.0\n"
        "\n"
    )
    fake_status = tmp_path / "status"
    fake_status.write_text(status, encoding="utf-8")

    real_path = Path

    def fake_path(p):  # noqa: ANN001
        if p == "/var/lib/dpkg/status":
            return fake_status
        return real_path(p)

    monkeypatch.setattr("craft_parts.packages.deb.Path", fake_path)

    pkgs = Ubuntu.get_installed_packages()
    assert pkgs == ["keep=2.0"]
