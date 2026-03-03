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
from subprocess import CompletedProcess

from craft_parts.packages.deb import _dpkg_installed_version


def test_dpkg_installed_version_nonzero_returncode(monkeypatch):
    def fake_run(*args, **kwargs):
        return CompletedProcess(args=["dpkg-query"], returncode=1, stdout="", stderr="nope")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _dpkg_installed_version("bash") is None


def test_dpkg_installed_version_empty_stdout(monkeypatch):
    def fake_run(*args, **kwargs):
        return CompletedProcess(args=["dpkg-query"], returncode=0, stdout="\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _dpkg_installed_version("bash") is None


def test_dpkg_installed_version_not_installed_status(monkeypatch):
    def fake_run(*args, **kwargs):
        out = "deinstall ok config-files\t1.2.3\n"
        return CompletedProcess(args=["dpkg-query"], returncode=0, stdout=out, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _dpkg_installed_version("bash") is None


def test_dpkg_installed_version_installed(monkeypatch):
    def fake_run(*args, **kwargs):
        out = "install ok installed\t5.2.15-2ubuntu1\n"
        return CompletedProcess(args=["dpkg-query"], returncode=0, stdout=out, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _dpkg_installed_version("bash") == "5.2.15-2ubuntu1"
