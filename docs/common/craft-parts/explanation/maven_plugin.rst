.. _maven_plugin_explanation:

Maven Plugin
============

Maven plugin is a plugin that simplifies building and packaging Jars for projects that use the
Maven (mvn) tooling. It is equivalent to running the following command:

.. code-block:: shell
    
    mvn package


Plugin parameter ``maven_parameters`` is used to additionally provide any arguments to the mvn
package command above. ``maven_parameters`` parameter can be used to further configure any command
line arguments. All values are passed in after the initial ``mvn package`` command, delimited by
spaces.

Another plugin parameter ``maven_use_mvnw`` is used to leverage Maven wrapper files provided by the
project to run the package command. Initial mvn executable is replaced with project’s mvnw
executable file, resulting in ``./mvnw package`` command.

The plugin is able to detect and apply the following proxy environment variables:
``http_proxy``, ``https_proxy``, ``no_proxy``. These environment variables can be supplied through
the ``build-environment`` directive. These environment variables will be used to create a maven
settings file (``.parts/.m2/settings.xml``) which will be supplied to the ``mvn package`` command.

Before executing the build, an ``effective-pom`` will be generated to check the validity of the
project Java version against the build system Java version. If an incompatible version is found,
the plugin will terminate early without attempting to build.

After the successful build, Java binary and Jar files will be installed in the
``CRAFT_PART_INSTALL`` directory. Java binary will be mapped under ``CRAFT_PART_INSTALL/bin/java``.
Jar files will be mapped under ``CRAFT_PART_INSTALL/jar/`` directory.
