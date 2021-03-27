# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from craft_parts import errors


def test_parts_error_brief():
    err = errors.PartsError(brief="A brief description.")
    assert str(err) == "A brief description."
    assert (
        repr(err)
        == "PartsError(brief='A brief description.', details=None, resolution=None)"
    )
    assert err.brief == "A brief description."
    assert not err.details
    assert not err.resolution


def test_parts_error_full():
    err = errors.PartsError(brief="Brief", details="Details", resolution="Resolution")
    assert str(err) == "Brief\nDetails\nResolution"
    assert (
        repr(err)
        == "PartsError(brief='Brief', details='Details', resolution='Resolution')"
    )
    assert err.brief == "Brief"
    assert err.details == "Details"
    assert err.resolution == "Resolution"


def test_part_dependency_cycle():
    err = errors.PartDependencyCycle()
    assert err.brief == "A circular dependency chain was detected."
    assert not err.details
    assert err.resolution == "Review the parts definition to remove dependency cycles."


def test_invalid_part_name():
    err = errors.InvalidPartName("foo")
    assert err.part_name == "foo"
    assert err.brief == "A part named 'foo' is not defined in the parts list."
    assert not err.details
    assert err.resolution == "Review the parts definition and make sure it's correct."


def test_invalid_architecture():
    err = errors.InvalidArchitecture("m68k")
    assert err.arch_name == "m68k"
    assert err.brief == "Architecture 'm68k' is not supported."
    assert not err.details
    assert err.resolution == "Make sure the architecture name is correct."
