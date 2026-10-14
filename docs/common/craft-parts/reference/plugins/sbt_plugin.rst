.. _craft_parts_sbt_plugin:

SBT plugin
==========

SBT plugin is a plugin that simplifies building and packaging jars for projects that
use the SBT tooling. By default, it is equivalent to running:

.. code-block:: shell

    ./sbt package

When wrapper mode is disabled, this plugin bootstraps an official SBT release from
GitHub and then runs:

.. code-block:: shell

    sbt package

After a successful build, this plugin will:

#. Create ``bin/`` and ``jar/`` directories in ``$CRAFT_PART_INSTALL``.
#. Find the ``java`` executable provided by the part and link it as
   ``$CRAFT_PART_INSTALL/bin/java``.
#. Hard link the ``.jar`` files generated in ``$CRAFT_PART_BUILD`` to
   ``$CRAFT_PART_INSTALL/jar``.

Keys
----

This plugin provides the following unique keys.


sbt-task
~~~~~~~~

**Type:** string

Task to execute with SBT. Default is ``package``.


sbt-parameters
~~~~~~~~~~~~~~

**Type:** list of strings

Additional command-line arguments passed to the SBT command.


sbt-use-wrapper
~~~~~~~~~~~~~~~

**Type:** boolean

Whether to use a project-provided ``sbt`` wrapper at ``<project-root>/sbt``.
Default is ``True``.


sbt-version
~~~~~~~~~~~

**Type:** string

SBT release version to bootstrap from official releases when ``sbt-use-wrapper`` is
``False``. Default is ``1.12.11``.


Dependencies
------------

When ``sbt-use-wrapper`` is ``False``, the plugin downloads the official SBT release
archive and extracts it in the part build area.

The SBT plugin does not make a Java runtime available in the target environment. This
must be handled by the developer when defining the part, according to each
application's runtime requirements.


Example
-------

This example builds the Scala 3 example project with SBT. It disables wrapper
mode so the plugin bootstraps SBT from an official release.

.. code-block:: yaml

        parts:
            sbt-scala3-example:
                plugin: sbt
                source: https://github.com/scala/scala3-example-project.git
                source-branch: main
                sbt-use-wrapper: false
                sbt-version: 1.12.11
                sbt-task: package
                build-packages:
                    - openjdk-21-jdk
                stage-packages:
                    - openjdk-21-jdk
