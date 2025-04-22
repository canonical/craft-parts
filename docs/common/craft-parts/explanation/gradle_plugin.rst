.. _gradle_plugin_explanation:

Gradle Plugin
=============

Gradle plugin is a plugin that simplifies building and packaging Jars for projects that use the
Gradle (gradle) tooling. It is equivalent to running the following command:

.. code-block:: shell

    gradle <gradle-task> # or `./gradlew <gradle-task>` if gradlew file is provided by the project


The plugin key ``gradle_parameters`` is used to additionally provide any arguments to the
``gradle <gradle-task>`` command above. The ``gradle_parameters`` key can be used to further
configure any command line arguments. All values are passed in after the initial
``gradle <gradle-task>`` command, delimited by spaces.

The ``gradle-task`` key is used to supply the build task. The task should build a JAR
artifact within the project directory.

The ``gradle-init-script`` key is used to supply any Gradle initialization script if
available, to configure the project prior to building. This script is executed via the 
``./gradlew --init-script <gradle-init-script>`` command.

The plugin is able to detect and apply the following proxy environment variables:
``http_proxy``, ``https_proxy`` and ``no_proxy``. These environment variables can be supplied
through the ``build-environment`` directive. These environment variables will be used to create a
Gradle properties file (``$GRADLE_HOME/gradle.properties``) which will be picked up by the Gradle
tooling.

After the successful build, Java binary and Jar files will be installed in the
``$CRAFT_PART_INSTALL`` directory. Java binary will be mapped under ``$CRAFT_PART_INSTALL/bin/java``.
Jar files will be mapped under the ``$CRAFT_PART_INSTALL/jar/`` directory.
