.. _craft_parts_jlink_plugin:

JLink plugin
=============

The JLink plugin can be used for Java projects where you would want to
deploy Java runtime specific for your application or install a minimal
Java runtime.


Keywords
--------

This plugin uses the common :ref:`plugin <part-properties-plugin>` keywords as
well as those for :ref:`sources <part-properties-sources>`.

Additionally, this plugin provides the plugin-specific keywords defined in the
following sections.

jlink-jars
~~~~~~~~~~~~~~~~~~
**Type:** list of strings

List of paths to jar files of your application. If not specified, plugin
will find all jar files in the staging area.

Dependencies
------------

The plugin expects OpenJDK to be available on the system and contain
``jlink`` executable, unless a part named ``jlink-deps`` is defined.
In this case, the plugin will assume that this part will stage the
openjdk to be used in the build step.

If the system has multiple OpenJDK installations available, it
should be selected by setting the ``JAVA_HOME`` environment variable.

.. code-block:: yaml

    parts:
        runtime:
            plugin: jlink
            build-packages:
                - openjdk-21-jdk
            build-environment:
                - JAVA_HOME: /usr/jvm/java-21-openjdk-${CRAFT_ARCH_BUILD_FOR}


The user is expected to stage openjdk dependencies either by installing
an appropriate openjdk slice:

.. code-block:: yaml

    parts:
        runtime:
            plugin: jlink
            after:
                - deps

        deps:
            plugin: nil
            stage-packages:
                - openjdk-21-jre-headless_security

or by installing the dependencies directly:

.. code-block:: yaml

    parts:
        runtime:
            plugin: jlink
            after:
                - deps

        deps:
            plugin: nil
            stage-packages:
                - libc6_libs
                - libgcc-s1_libs
                - libstdc++6_libs
                - zlib1g_libs
                - libnss3_libs


How it works
------------

During the build step, the plugin performs the following actions:

* Finds all jar files in the staging area or selects jars specified in
  ``jlink_jars``.
* Unpacks jar files to the temporary location and concatenates all embedded jars
  into `jdeps <jdeps_>`_ classpath.
* Runs `jdeps <jdeps_>`_ to discover Java modules required for the staged jars.
* Runs `jlink <jlink_>`_ to create a runtime image from the build JDK.


.. _`jdeps`: https://docs.oracle.com/en/java/javase/21/docs/specs/man/jdeps.html
.. _`jlink`: https://docs.oracle.com/en/java/javase/21/docs/specs/man/jlink.html
