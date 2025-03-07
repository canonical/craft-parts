.. _craft_parts_spring_boot_plugin:

Spring Boot plugin
==============

The `Spring Boot <spring_boot_>`_ plugin can be used for Java Spring Boot
application projects where you would want to build and deploy a Spring Boot
application.


Keywords
-------------

No keywords are supported for the plugin.

Dependencies
-------------------

The plugin expects OpenJDK to be available on the system and to contain the
``java`` executable. OpenJDK can be defined as a ``build-package`` in the part
using ``spring-boot`` plugin.

Another alternative is to define another part with the name
``spring-boot-deps``, and declare that the part in the ``spring-boot``
plugin :ref:`after <after>` the ``spring-boot-deps`` part.

If the system has multiple OpenJDK installations available, one must be selected
by setting the ``JAVA_HOME`` environment variable.

.. code-block:: yaml

    parts:
      runtime:
        plugin: spring-boot
        build-packages:
          - openjdk-21-jdk
        build-environment:
          - JAVA_HOME: /usr/jvm/java-21-openjdk-${CRAFT_ARCH_BUILD_FOR}


The user is expected to stage OpenJDK dependencies either by installing an
appropriate OpenJDK slice:

.. code-block:: yaml

    parts:
      runtime:
        plugin: spring-boot
        source: .
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
        plugin: spring-boot
        source: .
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
-----------------

During the build step, the plugin performs the following actions:

* Check the build wrappers (either mavenw or gradlew) exists
* Check that the project Java version is compatible with build Java version
* Build the project and stage the jar.

Recommendations
—----------------------

The Spring Boot plugin is best used with the Jlink plugin for use with
lightweight JVM, customized for the project.

.. code-block:: yaml

    parts:
      build:
        plugin: spring-boot
        source: .
        build-packages:
          - openjdk-21-jdk

      runtime:
        plugin: jlink
        after: [build]

For more information about the Jlink plugin, refer to the
`Jlink plugin documentation <craft_parts_jlink_plugin>_`.

.. _`spring_boot`: https://spring.io/
