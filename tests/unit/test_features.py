# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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
from craft_parts import Features, errors


@pytest.fixture(autouse=True)
def setup_features():
    Features.reset()
    yield
    Features.reset()


def test_features_default():
    """Features are disabled by default."""
    features = Features()

    assert features.enable_overlay is False
    assert features.enable_partitions is False


@pytest.mark.parametrize("enabled", [True, False])
def test_features_set_overlay(enabled):
    """Set the overlay feature."""
    features = Features(enable_overlay=enabled)

    assert features.enable_overlay is enabled

    # A different instance should have the previously set value
    f2 = Features()

    assert f2.enable_overlay is enabled


@pytest.mark.parametrize("enabled", [True, False])
def test_features_set_partitions(enabled):
    """Set the partitions feature."""
    features = Features(enable_partitions=enabled)

    assert features.enable_partitions is enabled

    # A different instance should have the previously set value
    f2 = Features()

    assert f2.enable_partitions is enabled


def test_features_set_twice():
    """Features are a frozen singleton and can only be configured once."""
    Features(enable_overlay=False)

    with pytest.raises(RuntimeError) as raised:
        Features(enable_overlay=False)

    assert str(raised.value) == "parameters can only be set once"


def test_features_mutually_exclusive():
    """Mutually exclusive features cannot be enabled together."""
    with pytest.raises(errors.FeatureError) as raised:
        Features(enable_overlay=True, enable_partitions=True)

    assert raised.value.message == "Cannot enable overlay and partition features."
    assert raised.value.details == (
        "Overlay and partition features are mutually exclusive."
    )
