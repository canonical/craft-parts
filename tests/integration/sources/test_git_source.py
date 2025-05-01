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

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from craft_parts import ProjectDirs
from craft_parts.sources.git_source import GitSource


def _call(cmd: list[str]) -> None:
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _call_with_output(cmd: list[str]) -> str:
    return subprocess.check_output(cmd).decode("utf-8").strip()


@pytest.mark.usefixtures("new_dir")
class GitBaseTestCase:
    """Helper functions for git tests."""

    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions, monkeypatch):
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

    def get_commit(self, path) -> str:
        return _call_with_output(["git", "-C", path, "rev-parse", "HEAD"])


class TestGitSource(GitBaseTestCase):
    def test_pull_existing_after_update(self, new_dir, monkeypatch):
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
        monkeypatch.chdir(remote)
        _call(["git", "init", "--bare"])

        # from the working tree, clone, commit, and push
        self.clone_repo(remote, working_tree)
        monkeypatch.chdir(working_tree)
        self.add_file("test.txt", "Hello, World!", "created test.txt")
        _call(["git", "push", str(remote)])

        # from the other tree, clone, commit and push
        self.clone_repo(remote, other_tree)
        monkeypatch.chdir(other_tree)
        self.add_file("test.txt", "Howdy, Partner!", "updated test.txt")
        _call(["git", "push", "-f", str(remote)])

        # go back to the working tree and pull the new commit
        monkeypatch.chdir(working_tree)
        git.pull()

        # assert we actually pulled the commit
        assert Path(working_tree / "test.txt").read_text() == "Howdy, Partner!"

    def test_pull_existing_with_branch_after_update(self, new_dir, monkeypatch):
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
        monkeypatch.chdir(remote)
        _call(["git", "init", "--bare", "--initial-branch", "test-branch"])

        # from the working tree, clone, commit, and push
        self.clone_repo(remote, working_tree)
        monkeypatch.chdir(working_tree)
        self.add_file("test.txt", "Hello, World!", "created test.txt")
        _call(["git", "push", str(remote)])

        # from the other tree, clone, commit and push
        self.clone_repo(remote, other_tree)
        monkeypatch.chdir(other_tree)
        self.add_file("test.txt", "Howdy, Partner!", "updated test.txt")
        _call(["git", "push", "-f", str(remote)])

        # go back to the working tree and pull the new commit
        monkeypatch.chdir(working_tree)
        git.pull()

        # assert the commit was actually pulled
        assert Path(working_tree / "test.txt").read_text() == "Howdy, Partner!"

    @pytest.mark.parametrize("use_short_commit", [True, False])
    def test_pull_new_commit(self, use_short_commit, new_dir, monkeypatch):
        """Pull a commit in a new repo."""
        # set up repositories
        remote = Path("remote.git").absolute()
        working_tree = Path("working-tree").absolute()
        other_tree = Path("helper-tree").absolute()
        self.clean_dir(remote)
        self.clean_dir(working_tree)
        self.clean_dir(other_tree)

        # initialize remote
        monkeypatch.chdir(remote)
        _call(["git", "init", "--bare"])

        # initialize the other tree, clone, commit, and push
        self.clone_repo(remote, other_tree)
        monkeypatch.chdir(other_tree)
        self.add_file("test.txt", "Hello, World!", "created test.txt")
        _call(["git", "push", str(remote)])
        commit = self.get_commit(other_tree)

        # test that short commits are expanded
        commit = commit[:10] if use_short_commit else commit

        # create a second commit and push
        self.add_file("test.txt", "Howdy, Partner!", "updated test.txt")
        _call(["git", "push", str(remote)])

        git = GitSource(
            str(remote),
            working_tree,
            cache_dir=new_dir,
            project_dirs=self._dirs,
            # provide a short commit
            source_commit=commit[:10],
        )

        git.pull()

        # assert the first commit was pulled
        assert Path(working_tree / "test.txt").read_text() == "Hello, World!"

    @pytest.mark.parametrize("use_short_commit", [True, False])
    def test_pull_existing_commit(self, use_short_commit, new_dir, monkeypatch):
        """Pull a commit in an existing repo."""
        # set up repositories
        remote = Path("remote.git").absolute()
        working_tree = Path("working-tree").absolute()
        self.clean_dir(remote)
        self.clean_dir(working_tree)

        # initialize remote
        monkeypatch.chdir(remote)
        _call(["git", "init", "--bare"])

        # initialize working tree
        self.clone_repo(remote, working_tree)

        # from the working tree, clone, commit, and push
        monkeypatch.chdir(working_tree)
        self.add_file("test.txt", "Hello, World!", "created test.txt")
        _call(["git", "push", str(remote)])
        commit = self.get_commit(working_tree)

        # test that short commits are expanded
        commit = commit[:10] if use_short_commit else commit

        # create a second commit and push
        self.add_file("test.txt", "Howdy, Partner!", "updated test.txt")
        _call(["git", "push", str(remote)])

        git = GitSource(
            str(remote),
            working_tree,
            cache_dir=new_dir,
            project_dirs=self._dirs,
            # provide a short commit
            source_commit=commit[:10],
        )

        git.pull()

        # assert the first commit was pulled
        assert Path(working_tree / "test.txt").read_text() == "Hello, World!"


class TestGitConflicts(GitBaseTestCase):
    """Test that git pull errors don't kill the parser"""

    def test_git_conflicts(self, new_dir, monkeypatch):
        repo = os.path.abspath("conflict-test.git")
        working_tree = Path("git-conflict-test").absolute()
        conflicting_tree = f"{working_tree}-conflict"
        git = GitSource(repo, working_tree, cache_dir=new_dir, project_dirs=self._dirs)

        self.clean_dir(repo)
        self.clean_dir(working_tree)
        self.clean_dir(conflicting_tree)

        monkeypatch.chdir(repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(repo, working_tree)

        # check out the original repo
        self.clone_repo(repo, conflicting_tree)

        # add a file to the repo
        monkeypatch.chdir(working_tree)
        self.add_file("fake", "fake 1", "fake 1")
        _call(["git", "push", repo])

        git.pull()

        monkeypatch.chdir(conflicting_tree)
        self.add_file("fake", "fake 2", "fake 2")
        _call(["git", "push", "-f", repo])

        monkeypatch.chdir(working_tree)
        git.pull()

        body = None
        with open(os.path.join(working_tree, "fake")) as fp:
            body = fp.read()

        assert body == "fake 2"

    def test_git_submodules(self, new_dir, monkeypatch):
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

        monkeypatch.chdir(sub_repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(sub_repo, sub_working_tree)
        self.add_file("sub-file", "sub-file", "sub-file")
        _call(["git", "push", sub_repo])

        monkeypatch.chdir(repo)
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
        monkeypatch.chdir(sub_working_tree)
        self.add_file("fake", "fake 1", "fake 1")
        _call(["git", "push", sub_repo])

        monkeypatch.chdir(working_tree)
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

        monkeypatch.chdir(working_tree)
        git.pull()

        # new file should be there now
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "fake"), "fake 1"
        )


class TestGitDetails(GitBaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions, monkeypatch):
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

        monkeypatch.chdir(self.working_tree)
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

        monkeypatch.chdir("..")

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
