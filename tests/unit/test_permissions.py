# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

import pydantic
import pytest
from craft_parts.permissions import (
    Permissions,
    apply_permissions,
    filter_permissions,
    permissions_are_compatible,
)


def get_mode(path) -> int:
    """Shortcut the retrieve the read/write/execute mode for a given path."""
    return os.stat(path).st_mode & 0o777


def test_owner_group_error():
    """Check that "owner" and "group" cannot be declared individually."""
    with pytest.raises(pydantic.ValidationError):
        Permissions(owner=1)

    with pytest.raises(pydantic.ValidationError):
        Permissions(group=1)


def test_apply_permissions_mode(tmp_path):
    target = tmp_path / "a.txt"
    target.touch()
    os.chmod(target, 0)

    perm = Permissions()
    perm.apply_permissions(target)
    assert get_mode(target) == 0

    perm = Permissions(mode="644")
    perm.apply_permissions(target)
    assert get_mode(target) == 0o644


def test_apply_permissions_owner_group(tmp_path, mock_chown):
    target = tmp_path / "a.txt"
    target.touch()

    perm = Permissions()
    perm.apply_permissions(target)
    assert len(mock_chown) == 0

    perm = Permissions(owner=1111, group=2222)
    perm.apply_permissions(target)

    chown_call = mock_chown[target]
    assert chown_call.owner == 1111
    assert chown_call.group == 2222


def test_applies_to():
    perm = Permissions()
    assert perm.path == "*"

    assert perm.applies_to("etc/")
    assert perm.applies_to("etc/file1.txt")

    perm = Permissions(path="etc/*.txt")
    assert perm.applies_to("etc/file.txt")
    assert not perm.applies_to("etc")
    assert not perm.applies_to("etc/file.bin")


def test_filter_permissions():
    p1 = Permissions()
    p2 = Permissions(path="etc/*")
    p3 = Permissions(path="etc/file1.txt")

    permissions = [p1, p2, p3]

    assert filter_permissions("etc", permissions) == [p1]
    assert filter_permissions("etc/file2.bin", permissions) == [p1, p2]
    assert filter_permissions("etc/file1.txt", permissions) == [p1, p2, p3]


def test_apply_permissions(tmp_path, mock_chown):
    target = tmp_path / "a.txt"
    target.touch()
    os.chmod(target, 0)

    p1 = Permissions(mode="755")
    p2 = Permissions(owner=1111, group=2222)
    p3 = Permissions(owner=3333, group=4444)

    permissions = [p1, p2, p3]
    apply_permissions(target, permissions)

    assert get_mode(target) == 0o755
    chown_call = mock_chown[target]
    assert chown_call.owner == 3333
    assert chown_call.group == 4444


def test_permissions_are_compatible():
    perm1 = [Permissions(mode="755"), Permissions(owner=1111, group=2222)]
    perm2 = [Permissions(mode="0o755", owner=1111, group=2222)]
    perm3 = [Permissions(owner=1111, group=2222)]
    perm4 = None
    perm5 = []

    assert permissions_are_compatible(perm1, perm2)
    assert not permissions_are_compatible(perm1, perm3)
    assert not permissions_are_compatible(perm2, perm3)
    assert permissions_are_compatible(perm1, perm4)
    assert permissions_are_compatible(perm1, perm5)
    assert permissions_are_compatible(perm4, perm5)
