.. _craft_parts_mill_plugin:

Mill plugin
===========

Mill plugin is a plugin that simplifies building and packaging jars for projects that
use Mill. By default, it is equivalent to running:

.. code-block:: shell

    ./mill __.assembly

When wrapper mode is disabled, this plugin bootstraps an official Mill release from
GitHub and then runs:

.. code-block:: shell

    mill __.assembly

After a successful build, this plugin will:

#. Create ``bin/`` and ``jar/`` directories in ``$CRAFT_PART_INSTALL``.
#. Find the ``java`` executable provided by the part and link it as
   ``$CRAFT_PART_INSTALL/bin/java``.
#. Hard link the ``.jar`` files generated in ``$CRAFT_PART_BUILD`` to
   ``$CRAFT_PART_INSTALL/jar``.

Keys
----

This plugin provides the following unique keys.


mill-task
~~~~~~~~~

**Type:** string

Task to execute with Mill. Default is ``__.assembly``.


mill-parameters
~~~~~~~~~~~~~~~

**Type:** list of strings

Additional command-line arguments passed to the Mill command.


mill-use-wrapper
~~~~~~~~~~~~~~~~

**Type:** boolean

Whether to use a project-provided ``mill`` wrapper at ``<project-root>/mill``.
Default is ``True``.


mill-version
~~~~~~~~~~~~

**Type:** string

Mill release version to bootstrap from official releases when ``mill-use-wrapper`` is
``False``. Default is ``0.12.8``.


Dependencies
------------

When ``mill-use-wrapper`` is ``False``, the plugin downloads the official Mill release
binary in the part build area.

The Mill plugin does not make a Java runtime available in the target environment. This
must be handled by the developer when defining the part, according to each
application's runtime requirements.


Example
-------

This example builds a real Kotlin project from the Mill repository. It disables
wrapper mode so the plugin bootstraps Mill from an official release.

.. code-block:: yaml

    parts:
      mill-kotlin-example:
        plugin: mill
        source: https://github.com/com-lihaoyi/mill.git
        source-subdir: example/kotlinlib/script/6-packaging
        source-branch: main
        mill-use-wrapper: false
        mill-version: 0.12.8
        mill-task: Bar.kt:assembly
        build-packages:
          - openjdk-21-jdk
        stage-packages:
          - openjdk-21-jdk
