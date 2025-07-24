.. _craft_parts_maven_use_plugin:

Maven Use plugin
================

The Maven Use plugin packages a `Maven`_-based project for use by other plugins using
the Maven Use plugin or the :ref:`craft_parts_maven_plugin`. It differs from the Maven
plugin in that it deploys the artifact to an internal `Maven repository`_ instead of
placing it in the final output.

Keys
----

This plugin has no unique keys.

.. _maven_use_self-contained_start:

Attributes
----------

This plugin supports the ``self-contained`` build attribute. Using this attribute will
disable the default `Maven Central repository`_ for every dependency including plugins.
All necessary dependencies will then need to be provided either as build packages or in
earlier parts.

When using this attribute, Maven Use may rewrite the version specification
of project dependencies based on what is locally available. This can be avoided by
provisioning the specified version prior to build time — for example, by building it
with the Maven Use plugin in an earlier part.

.. _maven_use_self-contained_end:

.. _maven_use_details_begin:

Dependencies
------------

The Maven plugin needs the ``mvn`` executable to build Maven projects but does not
provision it to allow flexibility in the choice of version.

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
* Updates any of the project's :file:`pom.xml` files to deploy the final artifacts to
  the local repository.
* Calls ``maven deploy`` to build and deploy the project to the local repository.

Examples
--------

The following snippet declares a part named ``java-dep`` using the ``maven-use`` plugin
and a ``java-main`` part. The ``java-main`` part depends on the contents of
``java-dep`` to build. Correct ordering is achieved with the use of the ``after`` key in
the ``java-main`` part.

.. code-block::

    parts:
      java-dep:
        source: dep/
        plugin: maven-use
        build-packages:
          - maven
      java-main:
        source: main/
        plugin: maven
        build-packages:
          - maven
        after:
          - java-dep

The following snippet declares a part named ``java-jacoco`` using the ``maven-use``
plugin and a ``java-main`` part. This build is done using the ``self-contained``
build attribute to control what Maven downloads for the build. The ``java-main`` part
declares a dependency on the ``jacoco-maven-plugin`` in its :file:`pom.xml` file. As
with the previous example, correct ordering is achieved with the use of the ``after``
key in the ``java-main`` part.

.. code-block:: yaml

    parts:
      java-jacoco:
        source: https://github.com/jacoco/jacoco.git
        plugin: maven-use
        build-packages:
          - maven
        build-attributes:
          - self-contained
      java-main:
        source: .
        plugin: maven
        build-packages:
          - maven
        build-attributes:
          - self-contained
        after:
          - java-jacoco

.. _Maven repository: https://maven.apache.org/guides/introduction/introduction-to-repositories.html
.. _Maven: https://maven.apache.org/index.html
.. _Maven Central repository: https://central.sonatype.com/
