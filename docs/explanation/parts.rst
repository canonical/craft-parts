Parts
=====

In the Craft Parts framework, parts are descriptions of the components to be
build for deployment, either individually or as part of a larger build
containing many components.

Tools like `Snapcraft`_ and `Juju`_ that use the concepts of parts to
describe a build process typically accept specifications of parts in YAML format. This allows each part to be described in a convenient,
mostly-declarative format.

When the Craft Parts framework is used to process a part on behalf of a tool
or library, it performs the steps described in the
:ref:`parts lifecycle <lifecycle>` to *pull* the source code and dependencies, *overlay* them onto a base file system, *build* the part, then *organize*,
*stage* and *prime* the build products for further processing.

Describing a part
-----------------

Each part contains all the required information about a specific component,
defining pieces of information using keys and values, as in a dictionary.
It can also be thought of as an object with named properties.

Generally, each part includes information about the following:
 * Its `source <Source_>`_
 * Its `dependencies <Dependencies_>`_
 * The `build process <Build process_>`_
 * How `build products <Build products_>`_ are exported/installed

Each of these are described in the following sections.

In addition, if more than one part is specified, the order in which the parts
are built is also partially defined by its description. See `Defining the build order`_ for more information.

.. ### Link to a schema or complete overview in the reference section.

Source
~~~~~~

The source for a part is described using the ``source`` key. This
specifies a location where the source code or other information is to be
*pulled* from, and may be a repository on a remote server, a directory on
the build host, or some other location.

Additional keys are used to fine-tune the specification so that a precise
description of the source location can be given, and also to specify the type
of source to be processed.

Where the type of the source information cannot be automatically determined,
the ``source-type`` key is used to explicitly specify the source format.
This influences the way in which the source code or data is processed.
A list of supported formats can be found in the `craft_parts/sources/sources.py` file. Examples include "bzr", "git", "hg", "mercurial", "subversion", "svn", "tar", "zip", "deb", "rpm", "7z", "local".

If the source type represents a file, the ``source-checksum`` key can be used
to provide a checksum value to be compared against the checksum of the
downloaded file.

Parts with source types that describe repositories can also use additional
keys to accurately specify where source code is found. The ``source-branch``,
``source-commit`` and ``source-tag`` keys allow sources to be obtained from
a specific branch, commit or tag.

Since some repositories can contain large amounts of data, the
``source-depth`` key can be used to specify the number of commits in a
repository's history that should be fetched instead of the complete history.
For repositories that use submodules, the ``source-submodules`` key can be
used to selectively fetch only those submodules that are needed.

The ``source-subdir`` key specifies the subdirectory in the unpacked sources
where builds will occur. **Note:** This key restricts the build to the
subdirectory specified, preventing access to files in the parent directory
and elsewhere in the file system directory structure.

Dependencies
~~~~~~~~~~~~

The dependencies of a part are described using the ``build-snaps`` and
``build-packages`` definitions. These specify lists of snaps and system
packages to be installed before the part is built.

System packages are referred to by the names that they are identified by on
the host system, and they are installed using the host's native package
manager, such as :command:`apt` or :command:`dnf`.

Build process
~~~~~~~~~~~~~

Every part needs to define how it will be built. Since all parts are built
using *plugins*, each part definition will use the ``plugin`` key.

The available plugins are provided as modules in the `craft_parts/plugins`
directory -- see :py:mod:`craft_parts.plugins`. These aim to simplify the
process of building source code written in a variety of programming languages
using appropriate build systems, libraries and frameworks. If a plugin is not
available for a particular combination of these attributes, a custom plugin
can be created or a basic plugin can be used to manually specify the build
actions to be taken, using the ``override-build`` key.

When a plugin is used, it exposes additional keys that can be used to
define behaviour that is specific to the type of project that the plugin
supports. For example, the :py:mod:`cmake plugin <craft_parts.plugins.cmake_plugin>` provides the ``cmake-parameters`` and
``cmake-generator`` keys that can be used to configure how :command:`cmake`
is used in the build process.

The build process can be further customised with the ``build-environment``,
``build-attributes`` and ``override-build`` keys.

The ``build-environment`` key defines assignments to shell environment variables in the build environment, specified as a list of key-value pairs.
In YAML format, this can take either of the following forms:

.. code:: yaml

   build-environment: [MESSAGE: "Hello world", NAME: "Craft Parts"]

   build-environment:
     - MESSAGE: "Hello world"
     - NAME: "Craft Parts"

The ``build-attributes`` key allows a number of standard customisations to be
applied to the build. Some of these are used to address issues that occur in
specific situations; others, such as ``debug`` are generally useful.

By default, Craft Parts builds independent parts in parallel. This can be
disabled by setting the ``disable-parallel`` key to ``True``.

The ``override-build`` key is used to override the build process provided by
a plugin, and it can be used to replace or extend it.

Build products
~~~~~~~~~~~~~~

After a part has been built in the *build* step, the build products are
prepared in three further steps.

If the ``organize`` key is specified, it is used to move files
specify a list of mappings between files
in the part key-value pairs

   * How to manage the different steps in the build process

    override-stage string
    override-prime string



   * Filesets

 * How artifacts are exported/installed




    stage-snaps ref: #/definitions/grammar-array
    stage-packages ref: #/definitions/grammar-array
    organize
    filesets
    stage array with at least 1 unique item(s) of string
    prime array with at least 1 unique item(s) of string

..    parse-info array with at least 1 unique item(s) of string

.. _build-order:

Defining the build order
~~~~~~~~~~~~~~~~~~~~~~~~

By default, when more than one part is specified, they are built in alphabetical order unless there are dependencies between parts.

One way to define a dependency for a part is to use the ``after`` key in
a part's definition to specify a list of parts that it will be built after. The parts whose names are supplied in the list will be *built and staged*
before the part is built.

This is covered in detail in :ref:`part_processing_order`.

.. Overriding aspects of the build
.. ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How parts are built
-------------------

As described in :ref:`lifecycle`, parts are built in a sequence of steps:
*pull*, *overlay*, *build*, *organize*, *stage* and *prime*.

A part is built in a clean environment to ensure that only the base and its
dependencies are present, avoiding contamination from partial builds and
side effects from other builds. The environment is a file system in a
container where the root user's home directory is populated with a number of
subdirectories and configured to use snaps.

.. ### Verify that snap is available in general for non-Snapcraft builds.

Initially, before the *pull* step is run, the ``/root`` directory contains a
``project`` directory containing the files for the project to be built.

The pull step
~~~~~~~~~~~~~

When the *pull* step is run the :doc:`sources <Source>` are obtained using
the ``source*`` definitions in the part. After the step, the ``/root``
directory contains a ``state`` file to manage the state of the build and a
number of subdirectories:

 * ``parts`` is where individual parts for the project are prepared for build.
   The directory for each part in the ``parts`` directory contains ``src``, ``build`` and ``install`` directories that will be used during the *build*
   step.
 * ``prime`` will contain the finished build product later in the process.
 * ``project`` contains the original, unmodified project files.
 * ``stage`` will contain staged files after a build, before they are primed.

The standard actions for the *pull* step can be overridden or extended by
using the ``override-pull`` key to describe a series of actions.

The build step
~~~~~~~~~~~~~~

When the *build* step is run, each part in the ``parts`` subdirectory is
processed in the order described in the :ref:`previous section <build-order>`. The plugin for the part will use the appropriate build system
to build the part in its ``build`` subdirectory, using a copy of the files
in its ``src`` subdirectory, and install the result in the part's ``install``
subdirectory.

After the *build* step is run, the directory for each part in the ``parts``
directory will contain updated ``build`` and ``install`` directories. The
``build`` directory will contain the build products, and the ``install``
directory will contain the files to be installed in the snap.

.. Python representation of parts
.. ------------------------------
..
.. Link to reference documentation.


Summary of keys and steps
-------------------------

The following table shows the keys that are used in each build step.
The ``plugin`` and ``parse-info`` keys apply to all steps.

+-------------------+-------------------+-------------------+----------------+
| Pull              | Build             | Stage             | Prime          |
+===================+===================+===================+================+
| source            | disable-parallel  | stage             | prime          |
+-------------------+-------------------+-------------------+----------------+
| source-checksum   | after             | stage-snaps       |                |
+-------------------+-------------------+-------------------+----------------+
| source-branch     | build-snaps       | stage-packages    |                |
+-------------------+-------------------+-------------------+----------------+
| source-commit     | build-packages    | organize          |                |
+-------------------+-------------------+-------------------+----------------+
| source-depth      | build-environment | filesets          |                |
+-------------------+-------------------+-------------------+----------------+
| source-submodules | build-attributes  |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-subdir     |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-tag        |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-type       |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| override-pull     | override-build    | override-stage    | override-prime |
+-------------------+-------------------+-------------------+----------------+

.. include:: /links.txt
