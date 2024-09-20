.. _how_to_document_a_plugin:

How to document a plugin
========================

This document contains a template that should be used when documenting new
plugins. Substitute values for each of the following placeholders in the
headings and main text.

<name>
    The name of the plugin; e.g. Python

Replace the instructions with suitable descriptions.


<Name> plugin
-------------

A general description of the plugin that includes as many of these items as
necessary:

* The overall purpose of the plugin.
* What tasks it performs or helps with.
* Why it might be used instead of another solution, such as a collection of
  custom actions.

It is also useful to indicate if the plugin replaces an existing plugin, or
should be used instead of another similar plugin.


Keywords
~~~~~~~~

A sequence of subsections specifying the keywords provided by the plugin and
describe how the plugin uses them using the same format for keywords used in
the :ref:`part_properties` reference.

For example:

    **python-requirements**

    **Type**: list of strings

    A list of paths to requirements files needed to run :command:`pip`.


Environment variables
~~~~~~~~~~~~~~~~~~~~~

A sequence of subsections specifying the environment variables that the plugin
defines in the build environment, their default values, and what they are
typically used for.

For example:

    **PARTS_PYTHON_INTERPRETER**

    **Default value:** python3

    The interpreter binary to search for in ``PATH``.


Dependencies
~~~~~~~~~~~~

Notes about dependencies, the components relied on in the base.


Example
~~~~~~~

Ideally, a simple example or snippet from a YAML file should be included that
shows typical use of the plugin, with a link to a repository containing a
project that can be verified to work.

Alternatively, the YAML can be quoted from a test in the repository hosting
the documentation.

Known issues
~~~~~~~~~~~~

A list of links to known issues about the plugin, or a link to a search that
can retrieve the known issues.
