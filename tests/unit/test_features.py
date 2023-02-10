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

import pytest

from craft_parts import Features


@pytest.fixture(autouse=True)
def setup_features():
    Features.reset()
    yield
    Features.reset()


def test_features():
    features = Features()
    assert features.enable_overlay is False


def test_features_set():
    features = Features(enable_overlay=False)
    assert features.enable_overlay is False

    # A different instance should have the previously set value
    f2 = Features()
    assert f2.enable_overlay is False


def test_features_set_twice():
    Features(enable_overlay=False)

    with pytest.raises(RuntimeError) as raised:
        Features(enable_overlay=False)

    assert str(raised.value) == "parameters can only be set once"
