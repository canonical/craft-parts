# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
import subprocess
import tarfile

import pytest

from craft_parts.sources import errors, sources


# region Fixtures
@pytest.fixture
def rpm_source(tmp_path: pathlib.Path):
    dest_dir = tmp_path / "src"
    dest_dir.mkdir()
    yield sources.RpmSource(str(dest_dir / "test.rpm"), dest_dir, cache_dir=tmp_path)


@pytest.fixture
def mock_popen(mocker):
    return mocker.patch.object(subprocess, "Popen", autospec=True)


@pytest.fixture
def mock_tarfile_open(mocker):
    return mocker.patch.object(tarfile, "open", autospec=True)


# endregion


# region Provisioning tests
def test_popen_process_error(rpm_source, mock_popen, tmp_path):
    mock_popen.side_effect = inner_error = subprocess.CalledProcessError(
        returncode=1, cmd="some command"
    )
    src = tmp_path / "test.rpm"
    src.touch()

    with pytest.raises(errors.InvalidRpmPackage) as exc_info:
        rpm_source.provision(tmp_path, src=src)

    assert exc_info.value.__cause__ == inner_error


def test_tar_error(rpm_source, mock_popen, mock_tarfile_open, tmp_path):
    mock_tarfile_open.side_effect = inner_error = tarfile.TarError()
    src = tmp_path / "test.rpm"
    src.touch()

    with pytest.raises(errors.InvalidRpmPackage) as exc_info:
        rpm_source.provision(tmp_path, src=src)

    assert exc_info.value.__cause__ == inner_error


def test_correct_command(mocker, rpm_source, tmp_path, mock_popen, mock_tarfile_open):
    src = tmp_path / "some-package.rpm"
    src.touch()

    rpm_source.provision(tmp_path, keep=True, src=src)

    mock_popen.assert_called_once_with(
        ["rpm2archive", "-"],
        stdin=mocker.ANY,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_unlinks(rpm_source, tmp_path, mock_popen, mock_tarfile_open):
    src = tmp_path / "test.rpm"
    src.touch()

    rpm_source.provision(tmp_path, keep=False, src=src)

    assert not src.exists()


def test_keep_no_unlink(rpm_source, tmp_path, mock_popen, mock_tarfile_open):
    src = tmp_path / "test.rpm"
    src.touch()

    rpm_source.provision(tmp_path, keep=True, src=src)

    assert src.exists()


# endregion
