.. _craft_parts_maven_plugin:

Maven plugin
============

The Maven plugin builds Java projects using the Maven build tool.

After a successful build, this plugin will:

* Create ``bin/`` and ``jar/`` directories in ``$CRAFT_PART_INSTALL``.
* Find the ``java`` executable provided by the part and link it as
  ``$CRAFT_PART_INSTALL/bin/java``.
* Hard link the ``.jar`` files generated in ``$CRAFT_PART_SOURCE`` to
  ``$CRAFT_PART_INSTALL/jar``.


Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

maven-parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings

Used to add additional parameters to the ``mvn package`` command line.


Environment variables
---------------------

This plugin reads the ``http_proxy`` and ``https_proxy`` variables from the environment
to configure Maven proxy access. A comma-separated list of hosts that should not be
accessed via proxy is read from the ``no_proxy`` environment variable.

Please refer to `Configuring Apache Maven <https://maven.apache.org/configure.html>`_ for
a list of environment variables used to configure Maven.


Dependencies
------------

The plugin expects Maven to be available on the system as the ``mvn`` executable, unless
a part named ``maven-deps`` is defined. In this case, the plugin will assume that this
part will stage the ``mvn`` executable to be used in the build step.

A Java Runtime must be staged if not part of the execution environment.


Example
-------

This is an example of a Snapcraft part using the Maven plugin. Note that the Maven and
Java Runtime packages are listed as build packages, and the Java Runtime is staged
to be part of the final payload::

  mkpass:
    plugin: maven
    source: .
    build-packages:
      - openjdk-11-jre-headless
      - maven
    stage-packages:
      - openjdk-11-jre-headless
