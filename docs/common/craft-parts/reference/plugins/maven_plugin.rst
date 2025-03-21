.. _craft_parts_maven_plugin:

Maven plugin
============

The Maven plugin builds Java projects using the Maven build tool.

The plugin will check for project Java version compatibility with the build system Java version
compatibility before executing the build. If an incompatible version is detected, the plugin will
fail early.

After a successful build, this plugin will:

.. _craft_parts_maven_plugin_post_build_begin:

* Create ``bin/`` and ``jar/`` directories in ``$CRAFT_PART_INSTALL``.
* Find the ``java`` executable provided by the part and link it as
  ``$CRAFT_PART_INSTALL/bin/java``.
* Hard link the ``.jar`` files generated in ``$CRAFT_PART_BUILD`` to
  ``$CRAFT_PART_INSTALL/jar``.

.. _craft_parts_maven_plugin_post_build_end:

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

maven-parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings

Used to add additional parameters to the ``mvn package`` command line.

maven-use-mvnw
~~~~~~~~~~~~~~
**Type:** boolean

Used to determine whether the build should use the project provided Maven
wrapper (located at ``<project-root>/mvnw``) executable file. The command ``mvn
package`` is replaced with ``./mvnw package`` command.


Environment variables
---------------------

Environment variables can be specified to modify behavior of the build. For the Maven plugin,
three proxy related environment variables are treated specially. ``http_proxy``, ``https_proxy``
and ``no_proxy``.

For a list of environment variables used to configure Maven, please refer to
`Configuring Apache Maven <https://maven.apache.org/configure.html>`_.

http_proxy
~~~~~~~~~~

URL to proxy http request to. The value is mapped to the settings file (.parts/.m2/settings.xml)
under proxy element.

https_proxy
~~~~~~~~~~

URL to proxy https request to. The value is mapped to the settings file (.parts/.m2/settings.xml)
under proxy element.

no_proxy
~~~~~~~~

A comma-separated list of hosts that should be not accessed via proxy.


.. _maven-details-begin:

Dependencies
------------

The plugin expects Maven to be available on the system as the ``mvn`` executable, unless
a part named ``maven-deps`` is defined. In this case, the plugin will assume that this
part will stage the ``mvn`` executable to be used in the build step.

Note that the Maven plugin does not make a Java runtime available in the target
environment. This must be handled by the developer when defining the part, according to
each application's runtime requirements.

.. _maven-details-end:
