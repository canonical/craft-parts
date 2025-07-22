.. _craft_parts_maven_use_plugin:

Maven Use plugin
================

The Maven Use plugin allows a `Maven repository`_ to be set up for `Maven`_-based
projects when used alongside the :ref:`craft_parts_maven_plugin`.

Keys
----

This plugin has no unique keys.

.. _maven_use_self-contained_start:

Attributes
----------

This plugin supports the ``self-contained`` build attribute. By declaring this
attribute on all parts using the Maven or Maven Use plugin, Maven will only use
locally-available projects as dependencies, creating an offline build of that artifact.

With the ``self-contained`` attribute, Maven Use may rewrite the version specification
of project dependencies based on what is locally available. This can be avoided by
provisioning the specified version prior to build time — for example, by building it
with the Maven Use plugin in an earlier part.

.. _maven_use_self-contained_end:

.. _maven_use_details_begin:

Dependencies
------------

The Maven plugin needs the ``mvn`` executable to build Maven projects but does not
provision it by itself, to allow flexibility in the choice of version.

To provide ``mvn``, one can either specify the ``maven`` Ubuntu package as a
``build-package`` or define a ``maven-deps`` part. In the latter case, all
parts using Maven should declare that they come after the ``maven-deps`` part. The
plugin will then assume that the ``maven-deps`` part staged the ``mvn`` executable to
be used in the build step. This can be useful, for example, in cases where a specific,
unreleased version of Maven is desired but unavailable as a snap or Ubuntu package.

.. _maven_use_details_end:

How it works
------------

During the build step the plugin performs the following actions:

* Creates a Maven settings file that configures proxy settings, points to the local
  Maven repository created by Craft Parts, and, if the ``self-contained`` build
  attribute is declared, disables network connections.
* Updates the :file:`pom.xml` file for project from the ``source`` key to tell Maven to
  deploy the final artifact to the local repository.
* Calls ``maven deploy`` to build and deploy the project to the local repository.

Examples
--------

The following snippet declares a part named ``java-jacoco`` using the ``maven-use``
plugin and a ``java-main`` part. The ``java-main`` part declares a dependency on the
``jacoco-maven-plugin`` in its :file:`pom.xml` file. Correct ordering is achieved with
the use of the ``after`` key in the ``java-main`` part.

.. code-block:: yaml

    parts:
      java-jacoco:
        source: https://github.com/jacoco/jacoco.git
        plugin: maven-use
        build-packages:
          - maven
      java-main:
        source: .
        plugin: maven
        build-packages:
          - maven
        after:
          - java-jacoco

.. _Maven repository: https://maven.apache.org/guides/introduction/introduction-to-repositories.html
.. _Maven: https://maven.apache.org/index.html
