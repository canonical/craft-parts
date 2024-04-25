.. _parts:

Parts
=====

In the Craft Parts framework, parts are descriptions of the components to be
built and prepared for deployment in a payload, either individually or as
part of a larger project containing many components.

When the Craft Parts framework is used to process a part on behalf of a tool
or library, it performs some or all of the steps described in the
:ref:`parts lifecycle <lifecycle>`:

#. The *pull* step pulls the source code and dependencies from locations
   defined in the part and places them into a package cache.
#. The *overlay* step unpacks them into a base file system chosen from a
   collection of standard file system images.
#. The *build* step runs a suitable build tool for the sources to compile
   a set of build products or artefacts.
#. The *stage* step copies the build products for the part into a common
   area for all parts in a project.
#. The *prime* step copies the files to be deployed into an area for
   further processing.

Not all of these steps may be needed for every use case, and tools that use
the Craft Parts framework can skip those that are not appropriate for their
purposes.

Tools like `Snapcraft`_ and `Charmcraft`_ that use the concepts of parts to
describe a build process typically accept specifications of parts in YAML format. This allows each part to be described in a convenient,
mostly-declarative format. Libraries that use parts may use the underlying
data structures to describe them.

Describing a part
-----------------

Each part contains all the required information about a specific component,
and is organised like a dictionary. Each piece of information is accessed
by name using a property.

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

The source for a part is described using the :ref:`source` property. This
specifies a location where the source code or other information is to be
*pulled* from. This may be a repository on a remote server, a directory on
the build host, or some other location.

Additional properties are used to fine-tune the specification so that a
precise description of the source location can be given, and also to specify
the type of source to be processed.

Where the type of the source information cannot be automatically determined,
the :ref:`source_type` property is used to explicitly specify the source
format. This influences the way in which the source code or data is processed.
A list of supported formats can be found in the :mod:`craft_parts.sources`
file. These include repository types, such as ``git``, archive formats such
as ``zip``, and ``local`` for files in the local file system.

If the source type represents a file, the :ref:`source_checksum` property can
be used to provide a checksum value to be compared against the checksum of
the downloaded file.

Parts with source types that describe repositories can also use additional
properties to accurately specify where source code is found.
The :ref:`source_branch`, :ref:`source_commit` and :ref:`source_tag`
properties allow sources to be obtained from a specific branch, commit or
tag.

Since some repositories can contain large amounts of data, the
:ref:`source_depth` property can be used to specify the number of commits in
a repository's history that should be fetched instead of the complete history.
For repositories that use submodules, the :ref:`source_submodules` property
can be used to fetch only those submodules that are needed.

The :ref:`source_subdir` property specifies the subdirectory in the unpacked
sources where builds will occur. **Note:** This property restricts the build
to the subdirectory specified, preventing access to files in the parent
directory and elsewhere in the file system directory structure.

Build dependencies
~~~~~~~~~~~~~~~~~~

The dependencies of a part are described using the :ref:`build_snaps` and
:ref:`build_packages` properties. These specify lists of snaps and system
packages to be installed before the part is built. If a part depends on
other parts, the :ref:`after` property is used to specify these -- see :ref:`parts_build-order`.

Snaps are referred to by the names that identify them in the Snap Store and
can also include the channel information so that specific versions of snaps
are used. For example, the ``juju`` snap could be specified as
``juju/stable``, ``juju/2.9/stable`` or ``juju/latest/stable`` to select
different versions.

System packages are referred to by the names that identify them on the host
system, and they are installed using the host's native package manager, such
as :command:`apt` or :command:`dnf`.

For example, a part that is built against the SDL 2 libraries could include
the ``libsdl2-dev`` package in the :ref:`build_packages` property.

.. _build_process:

Build process
~~~~~~~~~~~~~

Each part specifies the name of a *plugin* using the ``plugin`` property to
describe how it should be built. The available plugins are provided by the modules in the :py:mod:`craft_parts.plugins` package.

Plugins simplify the process of building source code written in a variety of
programming languages using appropriate build systems, libraries and
frameworks. If a plugin is not available for a particular combination of
these attributes, a basic plugin can be used to manually specify the build
actions to be taken, using the :ref:`override_build` property. This property
can also be used to replace or extend the build process provided by a plugin.

When a plugin is used, it exposes additional properties that can be used to
define behaviour that is specific to the type of project that the plugin
supports. For example, the :py:mod:`cmake plugin <craft_parts.plugins.cmake_plugin>` provides the ``cmake-parameters`` and
``cmake-generator`` properties that can be used to configure how
:command:`cmake` is used in the build process.

.. ifconfig:: project in ("Snapcraft",)

   The :ref:`build_attributes` property allows a number of standard
   customisations to be applied to the build. Some of these are used to address
   issues that occur in specific situations; others, such as ``debug`` are
   generally useful.

The :ref:`build_environment` property defines assignments to shell environment
variables in the build environment. This is useful in situations where the
build process of a part needs to be fine-tuned and can be configured by
setting environment variables.

The result of the *build* step is a set of build artefacts or products that
are the same as those that would be produced by manually compiling or
building the software.

Build artefacts
~~~~~~~~~~~~~~~

At the end of the *build* step, the build artefacts can be organised before
the *stage* step is run.

The :ref:`organize` property is used to customise how files are copied from
the building area to the staging area. It defines an ordered dictionary that
maps paths in the building area to paths in the staging area.

After the *build* step, the *stage* step is run to collect the artefacts from
the build into a common staging area for all parts. Additional snaps and
system packages that need to be deployed with the part are specified using
the :ref:`stage_snaps` and :ref:`stage_packages` properties. Files to be
deployed are specified using the :ref:`stage` property.

In the final *prime* step, the files needed for deployment are copied from
the staging area to the priming area. During this step the ``prime`` property
is typically used to exclude files in the staging area that are not required
at run-time. This is especially useful for multi-part projects that include
their own compilers or development tools.

.. _parts_build-order:

Defining the build order
~~~~~~~~~~~~~~~~~~~~~~~~

If a part depends on other parts in a project as build dependencies then it
can use the :ref:`after` property to define this relationship. This property
specifies a list containing the names of parts that it will be built after.
The parts in the list will be *built and staged* before the part is built.

This is covered in detail in :ref:`part_processing_order`.

.. include:: how_parts_are_built.rst
