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

"""Partition classes and helpers."""

from collections.abc import Iterable, Iterator


class PartitionList:
    """List of partitions and aliases.

    PartitionList wraps a dict with alias or partition names as keys and
    concrete partition names as values.

    Example map:
    {
      "default":"default",
      "volume/pc/efi":"volume/pc/efi",
      "volume/pc/rootfs":"default",
    }
    """

    def __init__(
        self,
        concrete_partitions: list[str] | None,
        *,
        aliases: dict[str, str] | None = None,
    ) -> None:
        self._partitions: dict[str, str] = {}
        if concrete_partitions:
            self._partitions.update({el: el for el in concrete_partitions})
        if aliases:
            self._partitions = add_aliases(partitions=self._partitions, aliases=aliases)

    def __iter__(self) -> Iterator[str]:
        return iter(self._partitions)

    def __getitem__(self, item: str) -> str | None:
        return self._partitions.get(item)

    def get(self, key: str, default: None = None) -> str | None:
        """Return a specific item of the underlying dict."""
        return self._partitions.get(key, default)

    def items(self) -> Iterable[tuple[str, str]]:
        """Return items of the underlying dict."""
        return self._partitions.items()

    def values(self) -> dict[str, str]:
        """Return items of the underlying dict."""
        return self._partitions.values()  # type: ignore[reportReturnType]

    @property
    def concrete_partitions(self) -> list[str]:
        """Return a list of concrete partitions."""
        return list(dict.fromkeys(self._partitions.values()))

    @property
    def aliases_or_partitions(self) -> list[str]:
        """Return a list of concrete partitions."""
        return list(self._partitions.keys())


def add_aliases(partitions: dict[str, str], aliases: dict[str, str]) -> dict[str, str]:
    """Validate the alias mapping and return the updated list of partitions.

    Checks:
    - every value is a known partition
    - no key is a known partition
    - no value is a known key (no circular dependency)
    """
    for key, val in aliases.items():
        # if key in partitions.values():
        #     raise ValueError(f"alias {key} cannot be a concrete partition")
        if val not in partitions:
            raise ValueError(f"alias {key} pointing to a unknown {val} partition")
        if val in aliases:
            raise ValueError(f"alias {key} pointing to another alias")
        partitions[key] = val
    return partitions
