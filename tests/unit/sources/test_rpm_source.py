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
from craft_parts import ProjectDirs
from craft_parts.sources import errors, sources


# region Fixtures
@pytest.fixture
def rpm_source(tmp_path: pathlib.Path, partitions):
    dest_dir = tmp_path / "src"
    dest_dir.mkdir()
    dirs = ProjectDirs(partitions=partitions)
    return sources.RpmSource(
        str(dest_dir / "test.rpm"), dest_dir, cache_dir=tmp_path, project_dirs=dirs
    )


@pytest.fixture
def mock_popen(mocker):
    return mocker.patch.object(subprocess, "Popen", autospec=True)


@pytest.fixture
def mock_tarfile_open(mocker):
    return mocker.patch.object(tarfile, "open", autospec=True)


# endregion


# region Validation tests
def test_valid_options(partitions):
    dirs = ProjectDirs(partitions=partitions)
    sources.RpmSource(
        "source",
        pathlib.Path(),
        cache_dir=pathlib.Path(),
        project_dirs=dirs,
        source_tag=None,
        source_commit=None,
        source_branch=None,
        source_submodules=None,
        source_depth=None,
    )


# pylint: disable=too-many-arguments
@pytest.mark.parametrize(
    (
        "source_tag",
        "source_commit",
        "source_branch",
        "source_submodules",
        "source_depth",
        "expected",
    ),
    [
        pytest.param("tag", None, None, None, None, "'source-tag'", id="bad-tag"),
        pytest.param(
            None, "commit", None, None, None, "'source-commit'", id="bad-commit"
        ),
        pytest.param(
            None, None, "branch", None, None, "'source-branch'", id="bad-branch"
        ),
        pytest.param(
            None,
            None,
            None,
            ["submodule"],
            None,
            "'source-submodules'",
            id="bad-submodules",
        ),
        pytest.param(None, None, None, None, 1, "'source-depth'", id="bad-depth"),
        pytest.param(
            "tag",
            "commit",
            "branch",
            "submodule",
            "depth",
            "'source-branch', 'source-commit', 'source-depth', 'source-submodules', and 'source-tag'",
            id="all-values-bad",
        ),
    ],
)
def test_invalid_options(
    partitions,
    source_tag,
    source_commit,
    source_branch,
    source_submodules,
    source_depth,
    expected,
):
    dirs = ProjectDirs(partitions=partitions)
    with pytest.raises(
        (errors.InvalidSourceOptions, errors.InvalidSourceOption)
    ) as exc_info:
        sources.RpmSource(
            "source",
            pathlib.Path("part_src_dir"),
            cache_dir=pathlib.Path(),
            project_dirs=dirs,
            source_tag=source_tag,
            source_commit=source_commit,
            source_branch=source_branch,
            source_submodules=source_submodules,
            source_depth=source_depth,
        )

    assert exc_info.value.brief == (
        f"Failed to pull source: {expected} cannot be used with a rpm source."
    )


# pylint: enable=too-many-arguments


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
