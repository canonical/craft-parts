.. meta::
    :description: Reference for parts built with the fpc-use plugin. Learn how to share Free Pascal units between parts and see working examples in YAML.

.. _craft_parts_fpc_use_plugin:

fpc-use plugin
==============

The fpc-use plugin makes the units of a part available to other parts. It is a
companion plugin meant to be used with the :ref:`fpc plugin <craft_parts_fpc_plugin>`,
for libraries that are distributed as source and compiled together with the programs
that use them.


Keys
----

This plugin provides the following unique keys.


fpc-use-unit-paths
~~~~~~~~~~~~~~~~~~

**Type:** list of strings

**Default:** ``["."]``

Directories containing units, relative to the source directory. An entry ending in
``/*`` adds every subdirectory of that directory instead of the directory itself.


fpc-use-include-paths
~~~~~~~~~~~~~~~~~~~~~

**Type:** list of strings

Directories containing include files, relative to the source directory. An entry
ending in ``/*`` adds every subdirectory of that directory instead of the directory
itself.


Environment variables
---------------------

This plugin sets no environment variables.


.. _fpc-use-details-begin:

Dependencies
------------

This plugin has no dependencies.

.. _fpc-use-details-end:


How it works
------------

During the build step the plugin performs the following actions:

#. Record the entries in ``fpc-use-unit-paths`` and ``fpc-use-include-paths`` in the
   part's export directory.
#. Link the source directory into the export directory.

The export directory is migrated to the backstage area during the stage step. Parts
using the ``fpc`` plugin that list this part in their ``after`` key then add the
recorded directories to their unit and include search paths.

Nothing is compiled or installed by this plugin.


Example
-------

The following snippet declares a part named ``greetlib`` using the fpc-use plugin and
a ``hello`` part that uses the ``fpc`` plugin to build a program that depends on the
units of ``greetlib``. The ``after`` key in the ``hello`` part establishes the correct
ordering of these parts.

.. code-block:: yaml

    parts:
      greetlib:
        plugin: fpc-use
        source: https://github.com/example/greetlib.git
        fpc-use-unit-paths:
          - units
        fpc-use-include-paths:
          - include
      hello:
        plugin: fpc
        source: .
        build-packages:
          - fpc
        fpc-programs:
          - src/hello.pas
        after:
          - greetlib
