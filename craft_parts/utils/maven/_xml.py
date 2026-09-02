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
        {craft_repository_element}
        {mirror_repository_element}
        {local_repository_element}
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

LOCAL_REPO_TEMPLATE = dedent("""\
    <localRepository>{repo_dir}</localRepository>
""")

CRAFT_REPO_TEMPLATE = dedent("""\
    <profiles>
      <profile>
        <id>craft</id>
        <repositories>
          <repository>
            <id>craft</id>
            <name>Craft-managed intermediate repository</name>
            <url>{repo_uri}</url>
          </repository>
        </repositories>
      </profile>
    </profiles>

    <activeProfiles>
      <activeProfile>craft</activeProfile>
    </activeProfiles>
""")

MIRROR_REPO = dedent("""\
  <mirrors>
        <mirror>
            <id>debian</id>
            <mirrorOf>central</mirrorOf>
            <name>Mirror Repository from Debian packages</name>
            <url>file:///usr/share/maven-repo</url>
        </mirror>
  </mirrors>
""")

DISTRIBUTION_REPO_TEMPLATE = dedent("""\
    <distributionManagement>
        <repository>
        <id>craft</id>
        <name>Craft-managed intermediate repository</name>
        <url>{repo_uri}</url>
        </repository>
    </distributionManagement>
""")

PLUGIN_TEMPLATE = dedent("""\
    <plugin>
        <artifactId>{artifact_id}</artifactId>
        <groupId>{group_id}</groupId>
        <version>{version}</version>
    </plugin>
""")
