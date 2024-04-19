.. _craft_parts_scons_plugin:

Scons plugin
============

The Scons plugin builds projects using Scons_.

After a successful build, this plugin will installs the generated
binaries in ``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

scons-parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Parameters to pass to scons for building and installation.

Environment variables
---------------------

This plugin sets ``DESTDIR`` to ``$CRAFT_PART_INSTALL``.

Dependencies
------------

The Scons plugin needs the ``scons`` executable work.


How it works
------------

During the build step the plugin performs the following actions:

* Run ``scons`` with any ``scons-parameters`` that might have been set;
* Run ``scons install`` with any ``scons-parameters`` that might have been set,
  the ``DESTDIR`` environment variable would affect the final installation path.

Examples
--------

The following snippet declares a part using the ``scons`` plugin. It
sets the ``scons-parameters`` for a ``prefix`` to be set to ``/usr``:

.. code-block:: yaml

    parts:
      gpsd:
        source: .
        plugin: scons
        scons-parameters:
            - prefix=/usr

.. _Scons: https://scons.org/

