import os

import pydantic
import pytest

from craft_parts.permissions import Permissions, apply_permissions, filter_permissions


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


def test_apply_permissions_owner_group(tmp_path, mocker):
    chown_mock = mocker.patch.object(os, "chown", autospec=True)
    target = tmp_path / "a.txt"
    target.touch()

    perm = Permissions()
    perm.apply_permissions(target)
    assert not chown_mock.called

    perm = Permissions(owner=1111, group=2222)
    perm.apply_permissions(target)
    chown_mock.assert_called_once_with(target, 1111, 2222)


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


class OwnerGroup:
    owner: int = -1
    group: int = -1


def test_apply_permissions(tmp_path, mocker):
    chown_call = OwnerGroup

    def fake_chown(_path, owner, group):
        chown_call.owner = owner
        chown_call.group = group

    mocker.patch.object(os, "chown", side_effect=fake_chown)

    target = tmp_path / "a.txt"
    target.touch()
    os.chmod(target, 0)

    p1 = Permissions(mode="755")
    p2 = Permissions(owner=1111, group=2222)
    p3 = Permissions(owner=3333, group=4444)

    permissions = [p1, p2, p3]
    apply_permissions(target, permissions)

    assert get_mode(target) == 0o755
    assert chown_call.owner == 3333
    assert chown_call.group == 4444
