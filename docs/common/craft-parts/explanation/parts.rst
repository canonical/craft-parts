.. _parts:

Parts
=====

A *part* is a description of the components to be built and prepared for deployment in a
payload, either individually or as part of a larger project containing many components.

When a part is processed, it performs some or all of the steps described in the parts
lifecycle: *pull*, *overlay*, *build*, *stage* and *prime*.

Not all of these steps may be needed for every use case, and some tools can skip steps
that aren't appropriate for their purposes.

Tools that use parts to describe a build process typically accept specifications of
parts in YAML format. This allows each part to be described in a convenient,
mostly-declarative format. Libraries that use parts may use the underlying data
structures to describe them.

Describing a part
-----------------

Each part contains all the required information about a specific component, and is
organised like a dictionary. Each piece of information is accessed by name using a
key.

Generally, each part includes information about the following:

* Its `source <Source_>`_ (where it is obtained from)
* Its `build dependencies <Build dependencies_>`_ (snaps and packages)
* The `build process <Build process_>`_
* How `build artefacts <Build artefacts_>`_ are handled

Each of these are described in the following sections.

.. ### Link to a schema or complete overview in the reference section.

.. _parts_source:

Source
~~~~~~

The source for a part is described using the ``source`` key. This specifies a
location where the source code or other information is to be *pulled* from. This may be
a repository on a remote server, a directory on the build host, or some other location.

Additional properties are used to fine-tune the specification so that a precise
description of the source location can be given, and also to specify the type of source
to be processed.

Where the type of the source information cannot be automatically determined, the
``source-type`` key is used to explicitly specify the source format. This
influences the way in which the source code or data is processed. A list of supported
formats can be found in the :mod:`craft_parts.sources` file. These include repository
types, such as ``git``, archive formats such as ``zip``, and ``local`` for files in the
local file system.

If the source type represents a file, the ``source-checksum`` key can be used to
provide a checksum value to be compared against the checksum of the downloaded file.

Parts with source types that describe repositories can also use additional properties to
accurately specify where source code is found. The ``source-branch``, ``source-commit``,
and ``source-tag`` keys allow sources to be obtained from a specific branch, commit or
tag.

Since some repositories can contain large amounts of data, the ``source-depth`` key can
be used to specify the number of commits in a repository's history that should be
fetched instead of the complete history. For repositories that use submodules, the
``source-submodules`` key can be used to fetch only those submodules that are needed.

The ``source-subdir`` key specifies the subdirectory in the unpacked sources where
builds will occur. It also restricts the build to the subdirectory specified, preventing
access to files in the parent directory and elsewhere in the file system directory
structure.

.. _build_dependencies:

Build dependencies
~~~~~~~~~~~~~~~~~~

The dependencies of a part are described using the ``build-snaps`` and
``build-packages`` keys. These specify lists of snaps and system packages to be
installed before the part is built. If a part relies on other parts for dependencies,
the ``after`` key asserts the hierarchy.

Snaps are referred to by the names that identify them in the Snap Store and can also
include the channel information so that specific versions of snaps are used. For
example, the ``juju`` snap could be specified as ``juju/stable``, ``juju/2.9/stable`` or
``juju/latest/stable`` to select different versions.

System packages are referred to by the names that identify them on the host system, and
they are installed using the host's native package manager, such as :command:`apt` or
:command:`dnf`.

For example, a part that is built against the SDL 2 libraries could include the
``libsdl2-dev`` package in the ``build-packages`` key.

.. _build_process:

Build process
~~~~~~~~~~~~~

Each part specifies the name of a *plugin* using the ``plugin`` key to describe how
it should be built. The available plugins are provided by the modules in the
:py:mod:`craft_parts.plugins` package.

Plugins simplify the process of building source code written in a variety of programming
languages using appropriate build systems, libraries and frameworks. If a plugin is not
available for a particular combination of these attributes, a basic plugin can be used
to manually specify the build actions to be taken, using the ``override-build`` key.
This key can also be used to replace or extend the build process provided by a plugin.

When a plugin is used, it exposes additional properties that can be used to define
behaviour that is specific to the type of project that the plugin supports. For example,
the :py:mod:`cmake plugin <craft_parts.plugins.cmake_plugin>` provides the
``cmake-parameters`` and ``cmake-generator`` properties that can be used to configure
how :command:`cmake` is used in the build process.

.. ifconfig:: project in ("Snapcraft",)

   The ``build_attributes`` key allows a number of standard customisations to be
   applied to the build. Some of these are used to address issues that occur in specific
   situations; others, such as ``debug`` are generally useful.

The ``build-environment`` key defines assignments to
shell environment variables in the build environment. This is useful in situations where
the build process of a part needs to be fine-tuned and can be configured by setting
environment variables.

The result of the *build* step is a set of build artefacts or products that are the same
as those that would be produced by manually compiling or building the software.

.. _build_artefacts:

Build artefacts
~~~~~~~~~~~~~~~

At the end of the *build* step, the build artefacts can be organised before the *stage*
step is run.

The ``organize`` key is used to customise how files are copied from the building area to
the staging area. It defines an ordered dictionary that maps paths in the building area
to paths in the staging area.

After the *build* step, the *stage* step is run to collect the artefacts from the build
into a common staging area for all parts. Additional snaps and system packages that need
to be deployed with the part are specified using the ``stage-snaps`` and
``stage-packages`` keys. Files to be deployed are specified using the ``stage`` key.

.. ifconfig:: project in ("Rockcraft", "Snapcraft")

   Chisel slices can be specified in ``stage-packages`` as well, but they can't be mixed
   with deb packages. 

In the final *prime* step, the files needed for deployment are copied from the staging
area to the priming area. During this step the ``prime`` key is typically used to
exclude files in the staging area that are not required at run-time. This is especially
useful for multi-part projects that include their own compilers or development tools.


.. _parts_build-order:

Defining the build order
~~~~~~~~~~~~~~~~~~~~~~~~

If a part depends on other parts in a project as build dependencies then it can use the
``after`` key to define this relationship. This key specifies a list containing the
names of parts that it will be built after. The parts in the list will be *built and
staged* before the part is built.


.. _include-how-parts-are-built:

.. include:: how_parts_are_built.rst
