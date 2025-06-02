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

"""Common utilities for Maven-based plugins."""

import os
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


def create_settings(
    settings_path: Path,
    *,
    extra_elements: list[ET.Element] | None = None,
) -> None:
    """Create a Maven configuration file.

    The settings file contains additional configuration for Maven, such
    as proxy parameters.

    :param settings_path: the location the settings file will be created.
    """
    settings = ET.Element(
        "settings",
        attrib={
            "xmlns": "http://maven.apache.org/SETTINGS/1.0.0",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": (
                "http://maven.apache.org/SETTINGS/1.0.0 "
                "http://maven.apache.org/xsd/settings-1.0.0.xsd"
            ),
        },
    )
    element = ET.Element("interactiveMode")
    element.text = "false"
    settings.append(element)

    if _proxy_needed():
        proxies = ET.Element("proxies")

        for protocol in ("http", "https"):
            env_name = f"{protocol}_proxy"
            case_insensitive_env = {
                item[0].lower(): item[1] for item in os.environ.items()
            }
            if env_name not in case_insensitive_env:
                continue

            proxy_url = urlparse(case_insensitive_env[env_name])
            proxy = ET.Element("proxy")
            proxy_tags = [
                ("id", env_name),
                ("active", "true"),
                ("protocol", protocol),
                ("host", str(proxy_url.hostname)),
                ("port", str(proxy_url.port)),
            ]
            if proxy_url.username is not None and proxy_url.password is not None:
                proxy_tags.extend(
                    [
                        ("username", proxy_url.username),
                        ("password", proxy_url.password),
                    ]
                )
            proxy_tags.append(("nonProxyHosts", _get_no_proxy_string()))

            add_xml_tags(proxy, proxy_tags)

            proxies.append(proxy)

        settings.append(proxies)

    if extra_elements is not None:
        for element in extra_elements:
            settings.append(element)

    tree = ET.ElementTree(settings)
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)

    with settings_path.open("w") as file:
        tree.write(file, encoding="unicode")
        file.write("\n")


def _get_no_proxy_string() -> str:
    no_proxy = [k.strip() for k in os.environ.get("no_proxy", "localhost").split(",")]
    return "|".join(no_proxy)


def add_xml_tags(element: ET.Element, tags: list[tuple[str, str]]) -> ET.Element:
    """Add a list of tags to an XML element."""
    for tag, text in tags:
        inner_ele = ET.Element(tag)
        inner_ele.text = text
        element.append(inner_ele)
    return element


def _proxy_needed() -> bool:
    """Determine whether or not to use proxy settings for Maven."""
    env_vars_lower = list(map(str.lower, os.environ.keys()))
    return any(k in env_vars_lower for k in ("http_proxy", "https_proxy"))
