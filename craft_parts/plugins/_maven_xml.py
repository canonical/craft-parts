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

"""XML templates for Maven project settings."""

from textwrap import dedent

SETTINGS_TEMPLATE = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 http://maven.apache.org/xsd/settings-1.0.0.xsd">
        <interactiveMode>false</interactiveMode>
        {proxies_element}
    </settings>
""")

PROXIES_TEMPLATE = dedent("""\
    <proxies>
        {proxies}
    </proxies>
""")

PROXY_TEMPLATE = dedent("""\
    <proxy>
        <id>{id}</id>
        <protocol>{protocol}</protocol>
        <host>{host}</host>
        <port>{port}</port>
        <nonProxyHosts>{non_proxy_hosts}</nonProxyHosts>
        {credentials}
        <active>true</active>
    </proxy>
""")

PROXY_CREDENTIALS_TEMPLATE = dedent("""\
    <username>{username}</username>
    <password>{password}</password>
""")
