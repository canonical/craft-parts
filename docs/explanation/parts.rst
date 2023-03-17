Parts
=====

In the Craft Parts framework, parts are descriptions of the components to be
built and prepared for deployment, either individually or as part of a larger
project containing many components.

When the Craft Parts framework is used to process a part on behalf of a tool
or library, it performs some or all of the steps described in the
:ref:`parts lifecycle <lifecycle>`:

 * The *pull* step pulls the source code and dependencies from locations
   defined in the part and places them into a package cache.
 * The *overlay* step unpacks them onto a base file system chosen from a
   collection of standard file system images.
 * The *build* step runs a suitable build tool for the sources to compile
   a set of build products.
 * The *stage* step copies the build products for the part into a common
   area for all parts in a project.
 * The *prime* step copies the required files for deployment.

Not all of these steps may be needed for every use case, and tools that use
the Craft Parts framework can skip those that are not appropriate for their
purposes.

Tools like `Snapcraft`_ and `Charmcraft`_ that use the concepts of parts to
describe a build process typically accept specifications of parts in YAML format. This allows each part to be described in a convenient,
mostly-declarative format.

Describing a part
-----------------

Each part contains all the required information about a specific component,
and is organised like a dictionary. Each piece of information is accessed
by name using a property.

Generally, each part includes information about the following:
 * Its `source <Source_>`_ (where it is obtained from)
 * Its `build dependencies <Build dependencies_>`_ (snaps and packages)
 * The `build process <Build process_>`_
 * How `build products <Build products_>`_ are exported/installed

Each of these are described in the following sections.

.. ### Link to a schema or complete overview in the reference section.

Source
~~~~~~

The source for a part is described using the ``source`` property. This
specifies a location where the source code or other information is to be
*pulled* from. This may be a repository on a remote server, a directory on
the build host, or some other location.

Additional properties are used to fine-tune the specification so that a
precise description of the source location can be given, and also to specify
the type of source to be processed.

Where the type of the source information cannot be automatically determined,
the ``source-type`` property is used to explicitly specify the source format.
This influences the way in which the source code or data is processed.
A list of supported formats can be found in the :mod:`craft_parts.sources`
file. These include repository types, such as ``git``, archive formats such
as ``zip``, and ``local`` for files in the local file system.

If the source type represents a file, the ``source-checksum`` property can be
used to provide a checksum value to be compared against the checksum of the
downloaded file.

Parts with source types that describe repositories can also use additional
properties to accurately specify where source code is found.
The ``source-branch``, ``source-commit`` and ``source-tag`` properties allow
sources to be obtained from a specific branch, commit or tag.

Since some repositories can contain large amounts of data, the
``source-depth`` property can be used to specify the number of commits in a
repository's history that should be fetched instead of the complete history.
For repositories that use submodules, the ``source-submodules`` property can
be used to selectively fetch only those submodules that are needed.

The ``source-subdir`` property specifies the subdirectory in the unpacked
sources where builds will occur. **Note:** This property restricts the build
to the subdirectory specified, preventing access to files in the parent
directory and elsewhere in the file system directory structure.

Build dependencies
~~~~~~~~~~~~~~~~~~

The dependencies of a part are described using the ``build-snaps`` and
``build-packages`` properties. These specify lists of snaps and system
packages to be installed before the part is built.

System packages are referred to by the names that they are identified by on
the host system, and they are installed using the host's native package
manager, such as :command:`apt` or :command:`dnf`.

For example, a part that is built against the SDL 2 libraries could include
the ``libsdl2-dev`` package in the ``build-packages`` property.

Build process
~~~~~~~~~~~~~

Each part specifies the name of a *plugin* using the ``plugin`` property to
describe how it should be built. The available plugins are provided by the modules in the :py:mod:`craft_parts.plugins` package.

Plugins simplify the process of building source code written in a variety of
programming languages using appropriate build systems, libraries and
frameworks. If a plugin is not available for a particular combination of
these attributes, a custom plugin can be created or a basic plugin can be
used to manually specify the build actions to be taken, using the
``override-build`` property.

When a plugin is used, it exposes additional properties that can be used to
define behaviour that is specific to the type of project that the plugin
supports. For example, the :py:mod:`cmake plugin <craft_parts.plugins.cmake_plugin>` provides the ``cmake-parameters`` and
``cmake-generator`` properties that can be used to configure how
:command:`cmake` is used in the build process.

The build process can be further customised with the ``build-environment``,
``build-attributes`` and ``override-build`` properties.

The ``build-environment`` property defines assignments to shell environment variables in the build environment, specified as a list of key-value pairs,
as in the following YAML format example:

.. code:: yaml

   build-environment:
     - MESSAGE: "Hello world"
     - NAME: "Craft Parts"

The ``build-attributes`` property allows a number of standard customisations
to be applied to the build. Some of these are used to address issues that
occur in specific situations; others, such as ``debug`` are generally useful.

The ``override-build`` property is used to override the build process
provided by a plugin, and it can be used to replace or extend it.

Build products
~~~~~~~~~~~~~~

At the end of the *build* step, the build products can be organized before
the *stage* step is run.

The ``organize`` property is used to customise how files are copied from the
building area to the staging area. It defines an ordered dictionary whose
properties are paths in the building area and values are paths in the staging area.

After the *build* step, the *stage* step is run to collect the build products
from all the parts into a common staging area. Additional snaps and system
packages that need to be deployed with the part are specified using the
``stage-snaps`` and ``stage-packages`` properties. Files and :doc:`Filesets`
are specified using the ``stage`` property.

In the final *prime* step, the files needed for deployment are copied from
the staging area to the priming area. During this step the ``prime`` property
is used to include files and filesets.

.. _build-order:

Defining the build order
~~~~~~~~~~~~~~~~~~~~~~~~

By default, when more than one part is specified, they are built in alphabetical order unless there are dependencies between parts.

One way to define a dependency for a part is to use the ``after`` property in
a part's definition to specify a list of parts that it will be built after. The parts whose names are supplied in the list will be *built and staged*
before the part is built.

By default, Craft Parts uses the defined build order to determine which
parts can be built in parallel. This can be disabled by setting the
``disable-parallel`` property to ``True``.

This is covered in detail in :ref:`part_processing_order`.

.. Overriding aspects of the build
.. ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
..   * How to manage the different steps in the build process
..
..    override-stage string
..    override-prime string

.. include:: /links.txt
