# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
from pathlib import Path
from unittest import mock

import pytest
from craft_parts import ProjectDirs
from craft_parts.sources import errors, sources
from craft_parts.sources.git_source import GitSource


def _fake_git_command_error(*args, **kwargs):
    raise subprocess.CalledProcessError(44, ["git"], output=b"git: some error")


@pytest.fixture
def mock_get_source_details(mocker) -> None:
    mocker.patch(
        "craft_parts.sources.git_source.GitSource._get_source_details", return_value=""
    )


@pytest.fixture
def fake_check_output(mocker):
    return mocker.patch("subprocess.check_output")


@pytest.fixture
def fake_run(mocker):
    return mocker.patch("craft_parts.sources.base.SourceHandler._run")


@pytest.fixture
def fake_get_current_branch(mocker):
    mocker.patch(
        "craft_parts.sources.git_source.GitSource._get_current_branch",
        return_value="test-branch",
    )


@pytest.mark.usefixtures("mock_get_source_details")
class TestGitSource:
    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        self._dirs = ProjectDirs(partitions=partitions)

    # pylint: enable=attribute-defined-outside-init
    def test_get_current_branch(self, mocker, new_dir):
        Path("source_dir/.git").mkdir(parents=True)
        mocker.patch(
            "craft_parts.sources.base.SourceHandler._run_output",
            return_value="test-branch",
        )

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        assert git._get_current_branch() == "test-branch"

    def test_pull(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_called_once_with(
            ["git", "clone", "--recursive", "git://my-source", "source_dir"]
        )

    def test_pull_with_depth(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_depth=2,
            project_dirs=self._dirs,
        )

        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                "--depth",
                "2",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_branch(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_branch="my-branch",
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                "--branch",
                "my-branch",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_tag(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_tag="tag",
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                "--branch",
                "tag",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_full_length_commit(self, fake_run, new_dir):
        commit = "2514f9533ec9b45d07883e10a561b248497a8e3c"
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit=commit,
            project_dirs=self._dirs,
        )

        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    ["git", "clone", "--recursive", "git://my-source", "source_dir"]
                ),
                mock.call(["git", "-C", "source_dir", "fetch", "origin", commit]),
                mock.call(["git", "-C", "source_dir", "checkout", commit]),
            ]
        )

    def test_pull_short_commit(self, fake_check_output, fake_run, new_dir):
        short_commit = "2514f9533e"
        commit = "2514f9533ec9b45d07883e10a561b248497a8e3c"
        fake_check_output.return_value = commit
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit=short_commit,
            project_dirs=self._dirs,
        )

        git.pull()

        fake_check_output.assert_has_calls(
            [
                mock.call(
                    ["git", "-C", "source_dir", "rev-parse", short_commit], text=True
                )
            ]
            * 2
        )
        fake_run.assert_has_calls(
            [
                mock.call(
                    ["git", "clone", "--recursive", "git://my-source", "source_dir"]
                ),
                mock.call(["git", "-C", "source_dir", "fetch", "origin", commit]),
                mock.call(["git", "-C", "source_dir", "checkout", commit]),
            ]
        )

    def test_pull_short_commit_error(self, fake_check_output, fake_run, new_dir):
        fake_check_output.side_effect = subprocess.CalledProcessError(1, [])
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit="deadbeef",
            project_dirs=self._dirs,
        )

        with pytest.raises(errors.VCSError) as raised:
            git.pull()

        assert raised.value.message == "Failed to parse commit 'deadbeef'."
        assert raised.value.resolution == (
            "Ensure 'source-commit' is correct or provide a full-length (40 character) commit."
        )

    def test_pull_short_commit_depth_error(self, fake_check_output, fake_run, new_dir):
        fake_check_output.side_effect = subprocess.CalledProcessError(1, [])
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit="deadbeef",
            source_depth=1,
            project_dirs=self._dirs,
        )

        with pytest.raises(errors.VCSError) as raised:
            git.pull()

        assert raised.value.message == "Failed to parse commit 'deadbeef'."
        assert raised.value.resolution == (
            "Ensure 'source-commit' is correct, provide a full-length (40 character) "
            "commit, or remove the 'source-depth' key from the part."
        )

    def test_pull_with_submodules_default(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_called_once_with(
            ["git", "clone", "--recursive", "git://my-source", "source_dir"]
        )

    def test_pull_with_submodules_empty(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_submodules=[],
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_called_once_with(
            ["git", "clone", "git://my-source", "source_dir"]
        )

    def test_pull_with_submodules(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_submodules=["submodule_1", "dir/submodule_2"],
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive=submodule_1",
                "--recursive=dir/submodule_2",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_local(self, fake_run, new_dir):
        """Verify cloning of a local filepath."""
        git = GitSource(
            "path/to/repo.git",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )

        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                f"file://{new_dir}/path/to/repo.git",
                "source_dir",
            ]
        )

    @pytest.mark.parametrize(
        "repository",
        [
            "ssh://user@host.xz:123/path/to/repo.git",
            "git+ssh://user@host.xz:123/path/to/repo.git",
            "user@host.xz:path/to/repo.git",
            "https://host.xz/path/to/repo.git",
            "user@host.xz:/~[user]/path/to/repo.git",
            "file:///path/to/repo.git",
        ],
    )
    def test_pull_repository_syntax(self, fake_run, new_dir, repository):
        """Verify cloning of valid repository syntaxes.

        This test should capture regressions in the reformatting of local filepaths.
        """
        git = GitSource(
            repository, Path("source_dir"), cache_dir=new_dir, project_dirs=self._dirs
        )

        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                repository,
                "source_dir",
            ]
        )

    def test_pull_existing(self, mocker, fake_run, fake_get_current_branch, new_dir):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/remotes/origin/test-branch",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_tag(self, mocker, fake_run, new_dir):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_tag="tag",
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/tags/tag",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_full_length_commit(self, fake_run, new_dir):
        commit = "2514f9533ec9b45d07883e10a561b248497a8e3c"
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit=commit,
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(["git", "-C", "source_dir", "fetch", "origin", commit]),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(["git", "-C", "source_dir", "reset", "--hard", commit]),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_short_commit(
        self, fake_check_output, fake_run, new_dir
    ):
        short_commit = "2514f9533e"
        commit = "2514f9533ec9b45d07883e10a561b248497a8e3c"
        fake_check_output.return_value = commit
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit=short_commit,
            project_dirs=self._dirs,
        )
        git.pull()

        fake_check_output.assert_has_calls(
            [
                mock.call(
                    ["git", "-C", "source_dir", "rev-parse", short_commit], text=True
                )
            ]
            * 2
        )
        fake_run.assert_has_calls(
            [
                mock.call(["git", "-C", "source_dir", "fetch", "origin", commit]),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(["git", "-C", "source_dir", "reset", "--hard", commit]),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_branch(self, mocker, fake_run, new_dir):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_branch="my-branch",
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/remotes/origin/my-branch",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_submodules_default(
        self, mocker, fake_run, fake_get_current_branch, new_dir
    ):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/remotes/origin/test-branch",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_submodules_empty(
        self, mocker, fake_run, fake_get_current_branch, new_dir
    ):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_submodules=[],
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/remotes/origin/test-branch",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_submodules(
        self, mocker, fake_run, fake_get_current_branch, new_dir
    ):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_submodules=["submodule_1", "dir/submodule_2"],
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/remotes/origin/test-branch",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                        "submodule_1",
                        "dir/submodule_2",
                    ]
                ),
            ]
        )

    def test_init_with_source_branch_and_tag_raises_exception(self, new_dir):
        with pytest.raises(errors.IncompatibleSourceOptions) as raised:
            GitSource(
                "git://mysource",
                Path("source_dir"),
                cache_dir=new_dir,
                source_tag="tag",
                source_branch="branch",
                project_dirs=self._dirs,
            )
        assert raised.value.source_type == "git"
        assert raised.value.options == ["source-tag", "source-branch"]

    def test_init_with_source_branch_and_commit_raises_exception(self, new_dir):
        with pytest.raises(errors.IncompatibleSourceOptions) as raised:
            GitSource(
                "git://mysource",
                Path("source_dir"),
                cache_dir=new_dir,
                source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
                source_branch="branch",
                project_dirs=self._dirs,
            )
        assert raised.value.source_type == "git"
        assert raised.value.options == ["source-branch", "source-commit"]

    def test_init_with_source_tag_and_commit_raises_exception(self, new_dir):
        with pytest.raises(errors.IncompatibleSourceOptions) as raised:
            GitSource(
                "git://mysource",
                Path("source_dir"),
                cache_dir=new_dir,
                source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
                source_tag="tag",
                project_dirs=self._dirs,
            )
        assert raised.value.source_type == "git"
        assert raised.value.options == ["source-tag", "source-commit"]

    def test_source_checksum_raises_exception(self, new_dir, partitions):
        dirs = ProjectDirs(partitions=partitions)
        with pytest.raises(errors.InvalidSourceOption) as raised:
            GitSource(
                "git://mysource",
                Path("source_dir"),
                cache_dir=new_dir,
                source_checksum="md5/d9210476aac5f367b14e513bdefdee08",
                project_dirs=dirs,
            )
        assert raised.value.source_type == "git"
        assert raised.value.option == "source-checksum"

    def test_has_source_handler_entry(self):
        assert sources._get_source_handler_class("", source_type="git") is GitSource

    def test_pull_failure(self, mocker, new_dir):
        mock_process_run = mocker.patch("craft_parts.utils.os_utils.process_run")
        mock_process_run.side_effect = subprocess.CalledProcessError(1, [])

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        with pytest.raises(errors.PullError) as raised:
            git.pull()
        assert raised.value.command == [
            "git",
            "clone",
            "--recursive",
            "git://my-source",
            "source_dir",
        ]
        assert raised.value.exit_code == 1


class TestGitGenerateVersion:
    @pytest.mark.parametrize(
        ("return_value", "expected"),
        [
            ("2.28", "2.28"),  # only_tag
            ("2.28-28-gabcdef1", "2.28+git28.abcdef1"),  # tag+commits
            ("2.28-29-gabcdef1-dirty", "2.28+git29.abcdef1-dirty"),  # tag+dirty
        ],
    )
    def test_version(self, mocker, return_value, expected):
        mocker.patch("subprocess.check_output", return_value=return_value.encode())
        assert GitSource.generate_version() == expected


class TestGitGenerateVersionNoTag:
    def test_version(self, mocker, fake_check_output):
        popen_mock = mocker.patch("subprocess.Popen")

        fake_check_output.side_effect = subprocess.CalledProcessError(1, [])
        proc_mock = mock.Mock()
        proc_mock.returncode = 0
        proc_mock.communicate.return_value = (b"abcdef1", b"")
        popen_mock.return_value = proc_mock

        expected = "0+git.abcdef1"
        assert GitSource.generate_version() == expected


class TestGitGenerateVersionNoGit:
    def test_version(self, mocker, fake_check_output):
        popen_mock = mocker.patch("subprocess.Popen")

        fake_check_output.side_effect = subprocess.CalledProcessError(1, [])
        proc_mock = mock.Mock()
        proc_mock.returncode = 2
        proc_mock.communicate.return_value = (b"", b"No .git")
        popen_mock.return_value = proc_mock

        with pytest.raises(errors.VCSError):
            GitSource.generate_version()
