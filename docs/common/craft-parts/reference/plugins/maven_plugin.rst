.. _craft_parts_maven_plugin:

Maven plugin
============


Maven plugin is a plugin that simplifies building and packaging Jars for projects that use the
Maven (mvn) tooling. It is equivalent to running the following command:

.. code-block:: shell
    
    mvn package


The ``maven-parameters`` key passes arguments to the ``mvn package`` command. The
parameter can also configure any command-line arguments. All values are passed after the
initial package command, delimited by spaces.

The ``maven-use-wrapper`` key leverages Maven wrapper files provided by the project to run
the package command. It replaces the default Maven executable with the project's
``mvnw`` file, to where the package command becomes ``./mvnw package``.

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

maven-use-wrapper
~~~~~~~~~~~~~~~~~
**Type:** boolean

Used to determine whether the build should use the Maven wrapper provided by the project
at ``<project-root>/mvnw``. If turned on, the project command is replaced with ``./mvnw
package``.


Environment variables
---------------------

Environment variables can be specified to modify the behavior of the build. Three
proxy-related, case-insensitive environment variables are treated specially:

- ``http_proxy``
- ``https_proxy``
- ``no_proxy``

For a list of environment variables used to configure Maven, please refer to
`Configuring Apache Maven <https://maven.apache.org/configure.html>`_.

http_proxy
~~~~~~~~~~

URL to proxy HTTP request to. The value is mapped to the settings file
(``.parts/.m2/settings.xml``) under the proxy element.

https_proxy
~~~~~~~~~~~

URL to proxy HTTPS request to. The value is mapped to the settings file
(``.parts/.m2/settings.xml``) under the proxy element.

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
