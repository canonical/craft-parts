.. _craft_parts_gradle_plugin:

Gradle plugin
=============

The Gradle plugin builds Java projects using the Gradle build tool.

After a successful build, this plugin will:

.. _craft_parts_gradle_plugin_post_build_begin:

* Create ``bin/`` and ``jar/`` directories in ``$CRAFT_PART_INSTALL``.
* Find the ``java`` executable provided by the part and link it as
  ``$CRAFT_PART_INSTALL/bin/java``.
* Hard link the ``.jar`` files generated in ``$CRAFT_PART_BUILD`` to 
  ``$CRAFT_PART_INSTALL/jar``.

.. _craft_parts_gradle_plugin_post_build_end:

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

gradle-init-script
~~~~~~~~~~~~~~~~~~
**Type:** string

The path to the initialization script to run with ``gradle --init-script <gradle-init-script>``
command. See `official gradle documentation <https://docs.gradle.org/current/userguide/init_scripts.html>`_
on the init script.

gradle-parameters
~~~~~~~~~~~~~~~~~
**Type:** list of strings

Used to add additional parameters to the ``gradle <task>`` command line.

gradle-task
~~~~~~~~~~~
**Type:** string

The `Gradle task <https://docs.gradle.org/current/userguide/more_about_tasks.html>`_ to build the
project.

Environment variables
---------------------

Environment variables can be specified to modify the behavior of the build. For the Gradle plugin,
three proxy environment variables are treated specially: ``http_proxy``, ``https_proxy`` and
``no_proxy``. For a list of environment variables used to configure Gradle, please refer to
`Configuring the build environment`_.

http_proxy
~~~~~~~~~~

URL to proxy HTTP requests to. The value is mapped to the settings file (.parts/.m2/settings.xml) under proxy element.

https_proxy
~~~~~~~~~~~

URL to proxy HTTPS requests to. The value is mapped to the settings file (.parts/.m2/settings.xml) under proxy element.

no_proxy
~~~~~~~~

A comma-separated list of hosts that should be not accessed via proxy.

Example
-------

Here is a consolidated example of how to use the Gradle plugin.

.. code-block:: yaml

    plugin: gradle
    source: .
    gradle-init-script: <path-to-gradle-init-script>
    gradle-parameters:
    - -D<some-parameter>=<some-value>
    gradle-task: build
    build-environment:
    - http_proxy: <http-proxy-url>
    - https_proxy: <https-proxy-url>
    - no_proxy: <comma-separated-no-proxy-urls>


For possible values of each field, refer to the Gradle documentation.

* ``gradle-parameters``: `Command line interface <https://docs.gradle.org/current/userguide/command_line_interface.html>`_
* ``gradle-task``: `Understanding tasks <https://docs.gradle.org/current/userguide/more_about_tasks.html>`_
* ``build-environment``: `Configuring the build environment`_

.. _Configuring the build environment: https://docs.gradle.org/current/userguide/build_environment.html
