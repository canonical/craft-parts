.. _craft_parts_nil_plugin:

Nil plugin
==========

The Nil plugin can be used to by-pass the need for a plugin when only parts primitives
are required.

Common cases include:

- Adding only :ref:`stage-packages <reference-part-properties-stage-packages>` in a
  discrete part
- Building source for when there is no suitable plugin with :ref:`override-build
  <reference-part-properties-override-build>`.


Keywords
--------

This plugin uses the common :ref:`plugin <reference-part-properties-plugin>` keywords as
well as those for :ref:`sources <reference-part-properties-source>`.

This plugin in itself has no requirement.

Dependencies
------------

This plugin has no dependencies.


How it works
------------

This plugin does nothing. It serves as a *noop* when there is a need to only use native
:ref:`part properties <reference-part-properties>`.

Examples
--------

The following snippet declares a part using the ``nil`` plugin to fetch and unpack
``hello`` defined in :ref:`stage-packages <reference-part-properties-stage-packages>`:

.. code-block:: yaml

    parts:
      nil:
        plugin: nil
        stage-packages:
          - hello
