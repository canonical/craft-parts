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

import os
import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest
from craft_parts import ProjectDirs
from craft_parts.sources import errors, sources
from craft_parts.sources.git_source import GitSource

# pylint: disable=too-many-lines


def _call(cmd: list[str]) -> None:
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _call_with_output(cmd: list[str]) -> str:
    return subprocess.check_output(cmd).decode("utf-8").strip()


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


# pylint: disable=missing-class-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-public-methods


@pytest.mark.usefixtures("new_dir")
class GitBaseTestCase:
    """Helper functions for git tests."""

    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        self._dirs = ProjectDirs(partitions=partitions)

    # pylint: enable=attribute-defined-outside-init

    def rm_dir(self, dir_name):
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

    def clean_dir(self, dir_name):
        self.rm_dir(dir_name)
        os.mkdir(dir_name)

    def clone_repo(self, repo, tree):
        self.clean_dir(tree)
        _call(["git", "clone", repo, tree])
        os.chdir(tree)
        _call(["git", "config", "--local", "user.name", '"Example Dev"'])
        _call(["git", "config", "--local", "user.email", "dev@example.com"])

    def add_file(self, filename, body, message):
        with open(filename, "w") as fp:
            fp.write(body)

        _call(["git", "add", filename])
        _call(["git", "commit", "-am", message])

    def check_file_contents(self, path, expected):
        body = None
        with open(path) as fp:
            body = fp.read()
        assert body == expected


# LP: #1733584
@pytest.mark.usefixtures("mock_get_source_details")
class TestGitSource(GitBaseTestCase):
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

    def test_pull_commit(self, fake_run, new_dir):
        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
            project_dirs=self._dirs,
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "clone",
                        "--recursive",
                        "git://my-source",
                        "source_dir",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "origin",
                        "2514f9533ec9b45d07883e10a561b248497a8e3c",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "checkout",
                        "2514f9533ec9b45d07883e10a561b248497a8e3c",
                    ]
                ),
            ]
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

    def test_pull_existing_with_commit(self, mocker, fake_run, new_dir):
        Path("source_dir/.git").mkdir(parents=True)

        git = GitSource(
            "git://my-source",
            Path("source_dir"),
            cache_dir=new_dir,
            source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
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
                        "2514f9533ec9b45d07883e10a561b248497a8e3c",
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

    def test_pull_existing_after_update(self, new_dir):
        """Test that `pull_existing` works after the remote is updated."""
        # set up repositories
        remote = Path("remote.git").absolute()
        working_tree = Path("working-tree").absolute()
        other_tree = Path("helper-tree").absolute()

        git = GitSource(
            str(remote), working_tree, cache_dir=new_dir, project_dirs=self._dirs
        )

        self.clean_dir(remote)
        self.clean_dir(working_tree)
        self.clean_dir(other_tree)

        # initialize remote
        os.chdir(remote)
        _call(["git", "init", "--bare"])

        # from the working tree, clone, commit, and push
        self.clone_repo(remote, working_tree)
        os.chdir(working_tree)
        self.add_file("test.txt", "Hello, World!", "created test.txt")
        _call(["git", "push", str(remote)])

        # from the other tree, clone, commit and push
        self.clone_repo(remote, other_tree)
        os.chdir(other_tree)
        self.add_file("test.txt", "Howdy, Partner!", "updated test.txt")
        _call(["git", "push", "-f", str(remote)])

        # go back to the working tree and pull the new commit
        os.chdir(working_tree)
        git.pull()

        # assert we actually pulled the commit
        with open(Path(working_tree / "test.txt")) as file:
            assert file.read() == "Howdy, Partner!"

    def test_pull_existing_with_branch_after_update(self, new_dir):
        """Test that `pull_existing` with a branch works after the remote is updated."""
        # set up repositories
        remote = Path("remote.git").absolute()
        working_tree = Path("working-tree").absolute()
        other_tree = Path("helper-tree").absolute()

        git = GitSource(
            str(remote),
            working_tree,
            cache_dir=new_dir,
            source_branch="test-branch",
            project_dirs=self._dirs,
        )

        self.clean_dir(remote)
        self.clean_dir(working_tree)
        self.clean_dir(other_tree)

        # initialize remote with a unique branch name
        os.chdir(remote)
        _call(["git", "init", "--bare", "--initial-branch", "test-branch"])

        # from the working tree, clone, commit, and push
        self.clone_repo(remote, working_tree)
        os.chdir(working_tree)
        self.add_file("test.txt", "Hello, World!", "created test.txt")
        _call(["git", "push", str(remote)])

        # from the other tree, clone, commit and push
        self.clone_repo(remote, other_tree)
        os.chdir(other_tree)
        self.add_file("test.txt", "Howdy, Partner!", "updated test.txt")
        _call(["git", "push", "-f", str(remote)])

        # go back to the working tree and pull the new commit
        os.chdir(working_tree)
        git.pull()

        # assert the commit was actually pulled
        with open(Path(working_tree / "test.txt")) as file:
            assert file.read() == "Howdy, Partner!"

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


class TestGitConflicts(GitBaseTestCase):
    """Test that git pull errors don't kill the parser"""

    def test_git_conflicts(self, new_dir):
        repo = os.path.abspath("conflict-test.git")
        working_tree = Path("git-conflict-test").absolute()
        conflicting_tree = f"{working_tree}-conflict"
        git = GitSource(repo, working_tree, cache_dir=new_dir, project_dirs=self._dirs)

        self.clean_dir(repo)
        self.clean_dir(working_tree)
        self.clean_dir(conflicting_tree)

        os.chdir(repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(repo, working_tree)

        # check out the original repo
        self.clone_repo(repo, conflicting_tree)

        # add a file to the repo
        os.chdir(working_tree)
        self.add_file("fake", "fake 1", "fake 1")
        _call(["git", "push", repo])

        git.pull()

        os.chdir(conflicting_tree)
        self.add_file("fake", "fake 2", "fake 2")
        _call(["git", "push", "-f", repo])

        os.chdir(working_tree)
        git.pull()

        body = None
        with open(os.path.join(working_tree, "fake")) as fp:
            body = fp.read()

        assert body == "fake 2"

    def test_git_submodules(self, new_dir):
        """Test that updates to submodules are pulled"""
        repo = os.path.abspath("submodules.git")
        sub_repo = os.path.abspath("subrepo")
        working_tree = Path("git-submodules").absolute()
        working_tree_two = f"{working_tree}-two"
        sub_working_tree = os.path.abspath("git-submodules-sub")
        git = GitSource(repo, working_tree, cache_dir=new_dir, project_dirs=self._dirs)

        self.clean_dir(repo)
        self.clean_dir(sub_repo)
        self.clean_dir(working_tree)
        self.clean_dir(working_tree_two)
        self.clean_dir(sub_working_tree)

        os.chdir(sub_repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(sub_repo, sub_working_tree)
        self.add_file("sub-file", "sub-file", "sub-file")
        _call(["git", "push", sub_repo])

        os.chdir(repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(repo, working_tree)
        _call(["git", "-c", "protocol.file.allow=always", "submodule", "add", sub_repo])
        _call(["git", "commit", "-am", "added submodule"])
        _call(["git", "push", repo])

        git.pull()

        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )

        # add a file to the repo
        os.chdir(sub_working_tree)
        self.add_file("fake", "fake 1", "fake 1")
        _call(["git", "push", sub_repo])

        os.chdir(working_tree)
        git.pull()

        # this shouldn't cause any change
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )
        assert os.path.exists(os.path.join(working_tree, "subrepo", "fake")) is False

        # update the submodule
        self.clone_repo(repo, working_tree_two)
        _call(
            [
                "git",
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "update",
                "--init",
                "--recursive",
                "--remote",
            ]
        )
        _call(["git", "add", "subrepo"])
        _call(["git", "commit", "-am", "updated submodule"])
        _call(["git", "push"])

        os.chdir(working_tree)
        git.pull()

        # new file should be there now
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "fake"), "fake 1"
        )


# pylint: disable=attribute-defined-outside-init


class TestGitDetails(GitBaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        def _add_and_commit_file(filename, content=None, message=None):
            if not content:
                content = filename

            if not message:
                message = filename

            with open(filename, "w") as fp:
                fp.write(content)

            _call(["git", "add", filename])
            _call(["git", "commit", "-am", message])

        self.working_tree = "git-test"
        self.source_dir = Path("git-checkout")
        self.clean_dir(self.working_tree)

        os.chdir(self.working_tree)
        _call(["git", "init"])
        _call(["git", "config", "user.name", '"Example Dev"'])
        _call(["git", "config", "user.email", "dev@example.com"])
        _add_and_commit_file("testing")
        self.expected_commit = _call_with_output(["git", "rev-parse", "HEAD"])

        _add_and_commit_file("testing-2")
        _call(["git", "tag", "test-tag"])
        self.expected_tag = "test-tag"

        _add_and_commit_file("testing-3")
        self.expected_branch = "test-branch"
        _call(["git", "branch", self.expected_branch])

        os.chdir("..")

        self._dirs = ProjectDirs(partitions=partitions)
        self.git = GitSource(
            self.working_tree,
            self.source_dir,
            cache_dir=new_dir,
            source_commit=self.expected_commit,
            project_dirs=self._dirs,
        )
        self.git.pull()

        self.source_details = self.git._get_source_details()

    def test_git_details_commit(self):
        assert self.source_details["source-commit"] == self.expected_commit

    def test_git_details_branch(self, new_dir):
        shutil.rmtree(self.source_dir)
        self.git = GitSource(
            self.working_tree,
            self.source_dir,
            cache_dir=new_dir,
            source_branch=self.expected_branch,
            project_dirs=self._dirs,
        )
        self.git.pull()

        self.source_details = self.git._get_source_details()
        assert self.source_details["source-branch"] == self.expected_branch

    def test_git_details_tag(self, new_dir):
        self.git = GitSource(
            self.working_tree,
            self.source_dir,
            cache_dir=new_dir,
            source_tag="test-tag",
            project_dirs=self._dirs,
        )
        self.git.pull()

        self.source_details = self.git._get_source_details()
        assert self.source_details["source-tag"] == self.expected_tag


# pylint: enable=attribute-defined-outside-init


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
