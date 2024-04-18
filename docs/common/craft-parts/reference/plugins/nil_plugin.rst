.. _craft_parts_nil_plugin:

Nil plugin
==========

The Nil plugin can be used to by-pass the need for a plugin when only
parts primitives are required.

Common cases include:

- Adding only :ref:`stage-packages <part-properties-plugin>` in a discrete part
- Building source for when there is no suitable plugin with
  :ref:`override-build <part-properties-plugin>`.


Keywords
--------

This plugin uses the common :ref:`plugin <part-properties-plugin>` keywords as
well as those for :ref:`sources <part-properties-sources>`.

This plugin in itself has no requirement.

Dependencies
------------

This plugin has no dependencies.


How it works
------------

During the build step, this plugin essentially does nothing.

Examples
--------

