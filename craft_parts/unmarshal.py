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

"""Helpers for data class unmarshaling."""

from typing import Any, Dict, KeysView, List, Optional


class DataUnmarshaler:
    """Unmarshal data with validation helpers.

    :param data: The dictionary to unmarshal data from.
    """

    def __init__(self, data: Dict[str, Any], consume: bool = False):
        if consume:
            self._retrieve = self._pop
        else:
            self._retrieve = self._get

        self._data = data

    def keys(self) -> KeysView[str]:
        """Return the current data dictionary keys."""
        return self._data.keys()

    def get_string(self, key: str, default: str = "") -> str:
        """Pop an item and validates it as a string."""
        value = self._retrieve(key, default)
        if not isinstance(value, str):
            raise ValueError(f"{key!r} must be a string")
        return value

    def get_optional_string(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Pop an item and validates it as a string."""
        value = self._retrieve(key, default)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{key!r} must be a string")
        return value

    def get_integer(self, key: str, default: int = 0) -> int:
        """Pop an item and validates it as a boolean."""
        value = self._retrieve(key, default)
        if not isinstance(value, int):
            raise ValueError(f"{key!r} must be an integer")
        return value

    def get_boolean(self, key: str, default: bool = False) -> bool:
        """Pop an item and validates it as a boolean."""
        value = self._retrieve(key, default)
        if not isinstance(value, bool):
            raise ValueError(f"{key!r} must be a boolean")
        return value

    def get_list_str(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """Pop an item and validates it as a list of strings."""
        if not default:
            default = []
        value = self._retrieve(key, default)
        if not isinstance(value, list):
            raise ValueError(f"{key!r} must be a list of strings")
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{key!r} must be a list of strings")
        return value

    def get_list_dict(
        self, key: str, default: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Pop an item and validates it as a list of dicts."""
        if not default:
            default = []
        value = self._retrieve(key, default)
        if not isinstance(value, list):
            raise ValueError(f"{key!r} must be a list of dictionaries")
        for item in value:
            if not isinstance(item, dict):
                raise ValueError(f"{key!r} must be a list of dictionaries")
        return value

    def get_dict(
        self, key: str, default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Pop an item and validates it as a dict."""
        if not default:
            default = {}
        value = self._retrieve(key, default)
        if not isinstance(value, dict):
            raise ValueError(f"{key!r} must be a dictionary")
        return value

    def _get(self, key, default):
        return self._data.get(key, default)

    def _pop(self, key, default):
        return self._data.pop(key, default)
