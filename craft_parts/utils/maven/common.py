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

"""Utilities for Maven projects and settings."""

import os
from pathlib import Path
from urllib.parse import urlparse

from craft_parts import infos

from ._xml import (
    PROXIES_TEMPLATE,
    PROXY_CREDENTIALS_TEMPLATE,
    PROXY_TEMPLATE,
    SETTINGS_TEMPLATE,
)


def create_maven_settings(*, part_info: infos.PartInfo) -> Path | None:
    """Create a Maven configuration file.

    The settings file contains additional configuration for Maven, such
    as proxy parameters.

    If it detects that no configuration is necessary, it will return None
    and do nothing.

    :param part_info: The part info for the part invoking Maven.

    :return: Returns a Path object to the settings file if one is created,
        otherwise None.
    """
    if not _needs_proxy_config():
        return None

    settings_path = part_info.part_build_subdir / ".parts/.m2/settings.xml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    proxies_element = _get_proxy_config()

    settings_xml = SETTINGS_TEMPLATE.format(proxies_element=proxies_element)

    settings_path.write_text(settings_xml)

    return settings_path


def _get_proxy_config() -> str:
    """Generate an XML string for proxy configurations.

    Reads the environment for information on desired proxy settings and
    transforms those variables into Maven XML settings entries.
    """
    # Transform all environment variables to their lowercase form to support HTTPS_PROXY
    # vs. https_proxy and such
    case_insensitive_env = {item[0].lower(): item[1] for item in os.environ.items()}

    proxies: list[str] = []
    for protocol in ["http", "https"]:
        env_name = f"{protocol}_proxy"
        if env_name not in case_insensitive_env:
            continue

        proxy_url = urlparse(case_insensitive_env[env_name])
        if proxy_url.username is not None and proxy_url.password is not None:
            credentials = PROXY_CREDENTIALS_TEMPLATE.format(
                username=proxy_url.username, password=proxy_url.password
            )
        else:
            credentials = ""

        proxy_element = PROXY_TEMPLATE.format(
            id=env_name,
            protocol=protocol,
            host=proxy_url.hostname,
            port=proxy_url.port,
            credentials=credentials,
            non_proxy_hosts=_get_no_proxy_string(),
        )

        proxies.append(proxy_element)

    return PROXIES_TEMPLATE.format(proxies="\n".join(proxies))


def _needs_proxy_config() -> bool:
    """Determine whether or not proxy configuration is necessary for Maven."""
    proxy_vars = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
    return any(key in os.environ for key in proxy_vars)


def _get_no_proxy_string() -> str:
    no_proxy = [k.strip() for k in os.environ.get("no_proxy", "localhost").split(",")]
    return "|".join(no_proxy)
