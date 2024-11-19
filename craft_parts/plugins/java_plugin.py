# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2024 Canonical Ltd.
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

"""Plugin base class and definitions."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile

from overrides import override

from .base import Plugin

logger = logging.getLogger(__name__)


class JavaPlugin(Plugin):
    """A base class for java-related plugins.

    Provide common methods to deal with the java executable location and
    symlink creation.
    """

    def _check_java(self, javac: str) -> tuple[int | None, str]:
        with tempfile.TemporaryDirectory() as tempdir:
            test_class = """
                public class Test {
                    public static void main(String[] args){
                        System.out.println(System.getProperty("java.specification.version"));
                    }
                }"""
            with open(f"{tempdir}/Test.java", "w") as file:
                file.write(test_class)

            try:
                subprocess.call([javac, "-d", tempdir, f"{tempdir}/Test.java"])
                java_home = os.path.dirname(os.path.dirname(javac))
                spec_version = subprocess.check_output(
                    [java_home + "/bin/java", "-cp", tempdir, "Test"], text=True
                )
                # Java 8 reports spec 1.8. Treat it as a spec version 8
                # 11 and up report the actual spec version number
                version = int(spec_version.split(".")[-1])

            except subprocess.CalledProcessError as err:
                logging.debug(f"{javac} is not a valid Java compiler: {err.output}")
            except PermissionError as err:
                logging.debug(
                    f"{javac} is not a valid Java compiler. Permission error {err}"
                )
            else:
                logging.info(f"Found JAVA_HOME {java_home}. Java version {version}.")
                return version, java_home
        logging.info("JDK not found.")
        return None, ""

    def _find_javac(self) -> list[str]:
        cmd = ["find", "/usr/lib/jvm", "-path", "*/bin/javac", "-print"]
        output = subprocess.check_output(cmd, text=True)
        return [x for x in output.split("\n") if len(x) > 0]

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Override JAVA_HOME in the build environment."""
        env = {}
        candidate_java = {}
        for javac in self._find_javac():
            spec, home = self._check_java(javac)
            if spec is not None:
                candidate_java[spec] = home
        if len(candidate_java) > 0:
            best = sorted(candidate_java.keys())[-1]
            env["JAVA_HOME"] = candidate_java[best]
        return env

    def _get_java_link_commands(self) -> list[str]:
        """Get the bash commands to provide /bin/java symlink."""
        # pylint: disable=line-too-long
        return [
            '# Find the "java" executable and make a link to it in $CRAFT_PART_INSTALL/bin/java',
            "mkdir -p ${CRAFT_PART_INSTALL}/bin",
            "java_bin=$(find ${CRAFT_PART_INSTALL} -name java -type f -executable)",
            "ln -s --relative $java_bin ${CRAFT_PART_INSTALL}/bin/java",
        ]
        # pylint: enable=line-too-long

    def _get_jar_link_commands(self) -> list[str]:
        """Get the bash commands to provide ${CRAFT_STAGE}/jars."""
        # pylint: disable=line-too-long
        return [
            "# Find all the generated jars and hardlink them inside CRAFT_PART_INSTALL/jar/",
            "mkdir -p ${CRAFT_PART_INSTALL}/jar",
            r'find ${CRAFT_PART_BUILD}/ -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jar \;',
        ]
        # pylint: enable=line-too-long

    def _get_java_post_build_commands(self) -> list[str]:
        """Get the bash commands to structure a Java build in the part's install dir.

        :return: The returned list contains the bash commands to do the following:

          - Create bin/ and jar/ directories in ${CRAFT_PART_INSTALL};
          - Find the ``java`` executable (provided by whatever jre the part used) and
            link it as ${CRAFT_PART_INSTALL}/bin/java;
          - Hardlink the .jar files generated in ${CRAFT_PART_BUILD} to
            ${CRAFT_PART_INSTALL}/jar.
        """
        return self._get_java_link_commands() + self._get_jar_link_commands()
