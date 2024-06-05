.. _craft_parts_make_plugin:

Make plugin
===========

The Make plugin can be used with projects that use a ``Makefile`` to
build with `GNU Make`_. After a successful build, this plugin will run
the ``install`` ``Makefile`` target with ``DESTDIR`` set to
``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

make-parameters
~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Options to pass to make.


Dependencies
------------

The plugin requires ``make``, its installation is handled by the
plugin itself.

From the project, the ``Makefile`` must support the ``install`` target
and the use of ``DESTDIR``.


How it works
------------

During the build step, the plugin performs the following actions:

* Call ``make`` with any parameters defined in ``make-parameters``
* Call ``make install`` with the ``DESTDIR`` set to the installation
  directory defined for the part.

Example
-------

The following snippet declares a part using the ``make`` plugin, the
source referred to in the part contains a ``Makefile`` at the root and
and ``install`` target that respects ``DESTDIR``, an alternate compiler
is set using ``make-parameters``:

.. code-block:: yaml

    parts:
      make:
        source: .
        plugin: make
        make-parameters:
          - CC=clang
        build-packages:
          - clang

.. _GNU Make: https://www.gnu.org/software/make/
