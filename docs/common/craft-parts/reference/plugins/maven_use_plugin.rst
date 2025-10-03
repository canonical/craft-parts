.. _craft_parts_maven_use_plugin:

Maven Use plugin
================

The Maven Use plugin packages `Maven`_-based projects and, unlike the
:ref:`craft_parts_maven_plugin`, deploys the artifact to an internal `Maven
repository`_. From this repository, the artifacts can be accessed by any other parts
using the Maven or Maven Use plugins.


Keys
----

This plugin has no unique keys.


.. _maven_use_self-contained_start:

Attributes
----------

This plugin supports the ``self-contained`` build attribute. Declaring this attribute
prevents access to the default `Maven Central repository`_. All dependencies, including
plugins, must then be provided as build packages or in an earlier part.

When this attribute is declared, Maven Use may rewrite the version specification of
project dependencies based on what is locally available. This can be avoided by
provisioning the specified version prior to build time — for example, by building it
with the Maven Use plugin in an earlier part. For more information on this behavior,
see :ref:`maven_use_version_rewriting`.

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


.. _maven_use_version_rewriting:

Version rewriting
-----------------

When building a :ref:`self-contained <maven_use_self-contained_start>` part, the
Maven Use plugin selects dependency versions as follows:

If the version of the dependency specified in the project's ``pom.xml`` file exists
locally, that version is selected.

If the requested version doesn't exist locally, Maven Use compares the locally
available versions that follow `semantic versioning`_ and selects the earliest
subsequent release. If no such version is found, Maven Use selects the latest release
that precedes the requested version.

If no prior conditions were satisfied, no version was requested, or the requested
version couldn't be interpreted as a semantic version, the latest locally-available
release following semantic versioning is selected.

Finally, if no releases with semantic versions exist locally, the release that comes
last alphabetically is selected.


How it works
------------

During the build step the plugin performs the following actions:

* Creates a Maven settings file that configures proxy settings, points to the local
  Maven repository created by Craft Parts, and, if the ``self-contained`` build
  attribute is declared, disables network connections.
* Updates any of the project's ``pom.xml`` files to deploy the final artifacts to
  the local repository.
* Calls ``maven deploy`` to build and deploy the project to the local repository.


Examples
--------

The following snippet declares two parts: ``java-dep``, which uses the ``maven-use``
plugin, and ``java-main``. Before ``java-main`` can build, the contents of ``java-dep``
must be staged. This dependency is handled by declaring that ``java-main`` must build
``after`` the ``java-dep`` part.

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

The following snippet declares two parts: ``java-jacoco``, which uses the ``maven-use``
plugin, and ``java-main``. To restrict access to the Maven Central repository, both
parts declare the ``self-contained`` build attribute. The ``pom.xml`` file of
``java-main`` declares ``java-jacoco`` as a dependency, which is handled by declaring
that ``java-main`` must build ``after`` the ``java-jacoco`` part.

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
.. _semantic versioning: https://semver.org/
