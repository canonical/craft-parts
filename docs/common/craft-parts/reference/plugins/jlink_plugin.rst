.. _craft_parts_jlink_plugin:

JLink plugin
============

The `JLink <jlink_>`_ plugin can be used for Java projects where you would want to
deploy a Java runtime specific for your application or install a minimal Java runtime.


Keys
----

This plugin provides the following unique keys.


jlink-modules
~~~~~~~~~~~~~

**Type:** list of strings

The exhaustive list of modules to include in the OpenJDK image. If set, this key
overrides all other keys for this plugin.


jlink-jars
~~~~~~~~~~

**Type:** list of strings

List of paths to your application's JAR files. If not specified, the plugin will find
all JAR files in the staging area.


jlink-extra-modules
~~~~~~~~~~~~~~~~~~~

**Type:** list of strings

Additional modules to include in the OpenJDK image.


jlink-multi-release
~~~~~~~~~~~~~~~~~~~
**Type:** int or string

**Default:** "base"

OpenJDK release version to use for multi-release JARs.


Dependencies
------------

The plugin expects OpenJDK to be available on the system and to contain the ``jlink``
executable. OpenJDK can be defined as a ``build-package`` in the part using ``jlink``
plugin. Another alternative is to define another part with the name ``jlink-deps``, and
declare that the part using the ``jlink`` plugin comes after the ``jlink-deps`` part
through the ``after`` key.

If the system has multiple OpenJDK installations available, one must be selected by
setting the ``JAVA_HOME`` environment variable.

.. code-block:: yaml

    parts:
      runtime:
        plugin: jlink
        build-packages:
          - openjdk-21-jdk
        build-environment:
          - JAVA_HOME: /usr/jvm/java-21-openjdk-${CRAFT_ARCH_BUILD_FOR}


The user is expected to stage OpenJDK dependencies either by installing an appropriate
OpenJDK slice:

.. code-block:: yaml

    parts:
      runtime:
        plugin: jlink
        build-packages:
          - openjdk-21-jdk
        after:
          - deps

        deps:
          plugin: nil
          stage-packages:
            - openjdk-21-jre-headless_security
          stage:
            - -usr/lib/jvm

Or, by installing the dependencies directly:

.. code-block:: yaml

    parts:
      runtime:
        plugin: jlink
        build-packages:
          - openjdk-21-jdk
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

The plugin performs actions during the build step.

When ``jlink-modules`` option is specified, the plugin runs `jlink`_ to create
an OpenJDK image with the specified modules.

Otherwise, the plugin performs the following actions:

#. Find all JAR files in the staging area or selects jars specified in ``jlink-jars``.
#. Unpack JAR files to the temporary location and concatenate all embedded jars into
   `jdeps`_ classpath.
#. Run `jdeps`_ to discover Java modules required for the staged jars.
#. Run `jlink`_ to create a runtime image from the build JDK.


.. _`jdeps`: https://docs.oracle.com/en/java/javase/21/docs/specs/man/jdeps.html
.. _`jlink`: https://docs.oracle.com/en/java/javase/21/docs/specs/man/jlink.html
