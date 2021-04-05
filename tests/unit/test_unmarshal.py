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

from craft_parts import unmarshal


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, "", None],
        [{"test": ""}, "", None],
        [{"test": "foo"}, "foo", None],
        [{"test": False}, "", "'test' must be a string"],
    ],
)
def test_unmarshal_string(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_string("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_string("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, "", ""],
        [{}, "foo", "foo"],
        [{"test": "bar"}, "", "bar"],
        [{"test": "bar"}, "foo", "bar"],
    ],
)
def test_unmarshal_string_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_string("test", default)
    assert test == value


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, None, None],
        [{"test": ""}, "", None],
        [{"test": "foo"}, "foo", None],
        [{"test": False}, "", "'test' must be a string"],
    ],
)
def test_unmarshal_optional_string(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_optional_string("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_optional_string("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, None, None],
        [{}, "foo", "foo"],
        [{"test": "bar"}, "", "bar"],
        [{"test": "bar"}, "foo", "bar"],
    ],
)
def test_unmarshal_optional_string_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_optional_string("test", default)
    assert test == value


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, 0, None],
        [{"test": 42}, 42, None],
        [{"test": -42}, -42, None],
        [{"test": "42"}, "", "'test' must be an integer"],
        [{"test": 42.5}, "", "'test' must be an integer"],
    ],
)
def test_unmarshal_integer(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_integer("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_integer("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, 5, 5],
        [{"test": 42}, 50, 42],
    ],
)
def test_unmarshal_integer_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_integer("test", default)
    assert test == value


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, False, None],
        [{"test": False}, False, None],
        [{"test": True}, True, None],
        [{"test": 0}, False, "'test' must be a boolean"],
    ],
)
def test_unmarshal_boolean(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_boolean("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_boolean("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, False, False],
        [{}, True, True],
        [{"test": True}, False, True],
    ],
)
def test_unmarshal_boolean_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_boolean("test", default)
    assert test == value


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, [], None],
        [{"test": ["foo", "bar"]}, ["foo", "bar"], None],
        [{"test": False}, [], "'test' must be a list of strings"],
        [{"test": ["foo", 42]}, [], "'test' must be a list of strings"],
    ],
)
def test_unmarshal_list_str(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_list_str("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_list_str("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, ["a", "b"], ["a", "b"]],
        [{"test": ["foo", "bar"]}, ["a", "b"], ["foo", "bar"]],
    ],
)
def test_unmarshal_list_str_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_list_str("test", default)
    assert test == value


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, [], None],
        [{"test": [{}, {}]}, [{}, {}], None],
        [{"test": [{"foo": "bar"}]}, [{"foo": "bar"}], None],
        [{"test": False}, [], "'test' must be a list of dictionaries"],
        [{"test": [{}, 42]}, [], "'test' must be a list of dictionaries"],
    ],
)
def test_unmarshal_list_dict(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_list_dict("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_list_dict("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, [{"a": "b"}], [{"a": "b"}]],
        [{"test": [{"foo": "bar"}]}, [{"a": "b"}], [{"foo": "bar"}]],
    ],
)
def test_unmarshal_list_dict_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_list_dict("test", default)
    assert test == value


@pytest.mark.parametrize(
    "data,value,error",
    [
        [{}, {}, None],
        [{"test": {}}, {}, None],
        [{"test": {"foo": "bar"}}, {"foo": "bar"}, None],
        [{"test": False}, {}, "'test' must be a dictionary"],
    ],
)
def test_unmarshal_dict(data, value, error):
    udata = unmarshal.DataUnmarshaler(data)
    if error:
        with pytest.raises(ValueError) as raised:
            udata.pop_dict("test")
        assert str(raised.value) == error
    else:
        test = udata.pop_dict("test")
        assert "test" not in data
        assert test == value


@pytest.mark.parametrize(
    "data,default,value",
    [
        [{}, {"a": "b"}, {"a": "b"}],
        [{"test": {"foo": "bar"}}, {"a": "b"}, {"foo": "bar"}],
    ],
)
def test_unmarshal_dict_default(data, default, value):
    udata = unmarshal.DataUnmarshaler(data)
    test = udata.pop_dict("test", default)
    assert test == value
