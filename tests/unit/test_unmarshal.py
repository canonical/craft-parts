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

import pytest

from craft_parts.unmarshal import DataUnmarshaler


class TestUnmarshalConsume:
    """Verify the data consumption switch."""

    def test_unmarshal(self):
        data = {"test": "foobar"}
        udata = DataUnmarshaler(data)
        test = udata.get_string("test")
        assert test == "foobar"
        assert data == {"test": "foobar"}

    def test_unmarshal_consume(self):
        data = {"test": "foobar"}
        udata = DataUnmarshaler(data, consume=True)
        test = udata.get_string("test")
        assert test == "foobar"
        assert data == {}


# pylint: disable=line-too-long


class TestUnmarshalData:
    """Check data retrieval and type correctness."""

    def test_unmarshal_string(self):
        assert DataUnmarshaler({}).get_string("test") == ""
        assert DataUnmarshaler({"test": ""}).get_string("test") == ""
        assert DataUnmarshaler({"test": "a"}).get_string("test") == "a"
        assert DataUnmarshaler({}).get_string("test", "b") == "b"
        assert DataUnmarshaler({"test": "a"}).get_string("test", "b") == "a"

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": False}).get_string("test")
        assert str(raised.value) == "'test' must be a string"

    def test_unmarshal_optional_string(self):
        assert DataUnmarshaler({}).get_optional_string("test") is None
        assert DataUnmarshaler({"test": "a"}).get_optional_string("test") == "a"
        assert DataUnmarshaler({}).get_optional_string("test", "b") == "b"
        assert DataUnmarshaler({"test": "a"}).get_optional_string("test", "b") == "a"

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": False}).get_optional_string("test")
        assert str(raised.value) == "'test' must be a string"

    def test_unmarshal_integer(self):
        assert DataUnmarshaler({}).get_integer("test") == 0
        assert DataUnmarshaler({"test": 42}).get_integer("test") == 42
        assert DataUnmarshaler({}).get_integer("test", 50) == 50
        assert DataUnmarshaler({"test": 42}).get_integer("test", 50) == 42

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": "0"}).get_integer("test")
        assert str(raised.value) == "'test' must be an integer"

    def test_unmarshal_boolean(self):
        assert DataUnmarshaler({}).get_boolean("test") is False
        assert DataUnmarshaler({"test": True}).get_boolean("test") is True
        assert DataUnmarshaler({}).get_boolean("test", True) is True
        assert DataUnmarshaler({"test": False}).get_boolean("test", True) is False

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": 0}).get_boolean("test")
        assert str(raised.value) == "'test' must be a boolean"

    def test_unmarshal_list_str(self):
        assert DataUnmarshaler({}).get_list_str("test") == []
        assert DataUnmarshaler({"test": ["a"]}).get_list_str("test") == ["a"]
        assert DataUnmarshaler({}).get_list_str("test", ["bar"]) == ["bar"]
        assert DataUnmarshaler({"test": ["a"]}).get_list_str("test", ["bar"]) == ["a"]

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": 0}).get_list_str("test")
        assert str(raised.value) == "'test' must be a list of strings"

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": [0]}).get_list_str("test")
        assert str(raised.value) == "'test' must be a list of strings"

    def test_unmarshal_list_dict(self):
        # fmt: off
        assert DataUnmarshaler({}).get_list_dict("test") == []
        assert DataUnmarshaler({"test": [{"a": "b"}]}).get_list_dict("test") == [{"a": "b"}]
        assert DataUnmarshaler({}).get_list_dict("test", [{"c": "d"}]) == [{"c": "d"}]
        assert DataUnmarshaler({"test": [{"a": "b"}]}).get_list_dict("test", [{"c": "d"}]) == [{"a": "b"}]
        # fmt: on

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": 0}).get_list_dict("test")
        assert str(raised.value) == "'test' must be a list of dictionaries"

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": [0]}).get_list_dict("test")
        assert str(raised.value) == "'test' must be a list of dictionaries"

    def test_unmarshal_dict(self):
        # fmt: off
        assert DataUnmarshaler({}).get_dict("test") == {}
        assert DataUnmarshaler({"test": {"a": "b"}}).get_dict("test") == {"a": "b"}
        assert DataUnmarshaler({}).get_dict("test", {"c": "d"}) == {"c": "d"}
        assert DataUnmarshaler({"test": {"a": "b"}}).get_dict("test", {"c": "d"}) == {"a": "b"}
        # fmt: on

        with pytest.raises(ValueError) as raised:
            DataUnmarshaler({"test": []}).get_dict("test")
        assert str(raised.value) == "'test' must be a dictionary"
