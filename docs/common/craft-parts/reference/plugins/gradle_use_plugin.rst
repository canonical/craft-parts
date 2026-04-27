.. _craft_parts_gradle_use_plugin:

Gradle Use plugin
=================

The Gradle Use plugin builds Java projects using the Gradle build tool and, unlike
the :ref:`craft_parts_gradle_plugin`, publishes the artifacts to a local `Maven
repository`_.


Keys
----

This plugin provides the following unique keys.


gradle-init-script
~~~~~~~~~~~~~~~~~~

**Type:** string

The path to the initialization script to run with ``gradle --init-script
<gradle-init-script>`` command. See `official gradle documentation
<https://docs.gradle.org/current/userguide/init_scripts.html>`_ on the init script.


gradle-parameters
~~~~~~~~~~~~~~~~~

**Type:** list of strings

Used to add additional parameters to the ``gradle publish`` command line.


gradle-use-daemon
~~~~~~~~~~~~~~~~~

**Type:** boolean

Whether to use the `Gradle daemon <https://docs.gradle.org/current/userguide/gradle_daemon.html>`_
during the build. The daemon is disabled by default.


Attributes
----------

This plugin supports the ``self-contained`` build attribute. Declaring this attribute
redirects all dependency resolution to a local Maven repository by overriding repository
settings. All dependencies, including plugins, must then be provided as build packages or
in an earlier part.


Environment variables
---------------------

Environment variables can be specified to modify the behavior of the build. For the
Gradle plugin, three proxy environment variables are treated specially: ``http_proxy``,
``https_proxy`` and ``no_proxy``. For a list of environment variables used to configure
Gradle, please refer to `Configuring the build environment`_.


http_proxy
~~~~~~~~~~

URL to proxy HTTP requests to. The value is mapped to the settings file
(``.parts/.m2/settings.xml``) under the proxy element.


https_proxy
~~~~~~~~~~~

URL to proxy HTTPS requests to. The value is mapped to the settings file
(``.parts/.m2/settings.xml``) under the proxy element.


no_proxy
~~~~~~~~

A comma-separated list of hosts that should be not accessed via proxy.


How it works
------------

During the build step, the plugin performs the following actions:

1. Creates a Gradle init script that configures publishing to a local Maven repository.
2. If the ``self-contained`` build attribute is declared, create an additional init
   script that redirects dependency resolution to the local Maven repository.
3. Calls ``gradle publish`` to build and deploy the project to the local repository.

Example
-------

The following snippet declares two parts: ``hello-dep``, which uses the ``gradle-use``
plugin, and ``hello-main``. Before ``hello-main`` can build, the contents of ``hello-dep``
must be staged. This dependency is handled by declaring that ``hello-main`` must build
``after`` the ``hello-dep`` part.

.. code-block:: yaml

  parts:
    hello-dep:
      source: dep/
      plugin: gradle-use
      build-snaps:
        - gradle
      build-attributes:
        - self-contained
    hello-main:
      source: main/
      plugin: gradle
      build-snaps:
        - gradle
      build-attributes:
        - self-contained
      after:
        - hello-dep


For possible values of each field, refer to the Gradle documentation.

#. ``gradle-parameters``: `Command line interface
   <https://docs.gradle.org/current/userguide/command_line_interface.html>`_
#. ``build-environment``: `Configuring the build environment`_


.. _Configuring the build environment: https://docs.gradle.org/current/userguide/build_environment.html
.. _Maven repository: https://maven.apache.org/guides/introduction/introduction-to-repositories.html
