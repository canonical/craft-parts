How parts are built
-------------------

As described in :ref:`lifecycle`, parts are built in a sequence of steps:
*pull*, *overlay*, *build*, *stage* and *prime*.

A part is built in a clean environment to ensure that only the base file
system and its dependencies are present, avoiding contamination from partial
builds and side effects from other builds. The environment is a file system in
a container where the root user's home directory is populated with a number of
subdirectories and configured to use snaps.

.. ### Verify that snap is available in general for non-Snapcraft builds.

Initially, before the *pull* step is run, the *working* directory contains a
``project`` directory containing the files for the project to be built.

The pull step
~~~~~~~~~~~~~

When the *pull* step is run the :ref:`sources <parts_source>` are obtained
using the source definitions for each part. After the step, the *working*
directory contains a ``state`` file to manage the state of the build and a
number of subdirectories:

* ``parts`` is where individual parts for the project are prepared for build.
  The directory for each part in the ``parts`` directory contains ``src``, ``build`` and ``install`` directories that will be used during the *build*
  step.
* ``prime`` will contain the finished build product later in the process.
* ``project`` contains the original, unmodified project files.
* ``stage`` will contain staged files after a build, before they are primed.

The standard actions for the *pull* step can be overridden or extended by
using the :ref:`override_pull` key to describe a series of actions.

The build step
~~~~~~~~~~~~~~

When the *build* step is run, each part in the ``parts`` subdirectory is
processed in the order described in the :ref:`build order <parts_build-order>`. The plugin for the part will use the appropriate build system
to build the part in its ``build`` subdirectory, using a copy of the files
in its ``src`` subdirectory, and install the result in the part's ``install``
subdirectory. The files in the ``install`` directory will be organised
according to the rules in the part's :ref:`organize` property.

After the *build* step is run, the directory for each part in the ``parts``
directory will contain updated ``build`` and ``install`` directories. The
``build`` directory will contain the build products, and the ``install``
directory will contain the files to be included in the payload.

Parts that depend on other parts will be built *after* their dependencies have
been built and staged.

The stage step
~~~~~~~~~~~~~~

When the *stage* step is run for a part, the contents of its ``install``
directory are copied into the common ``stage`` directory. Additionally,
dependencies specified by the :ref:`stage_packages` and :ref:`stage_snaps`
properties of the part are also unpacked into the ``stage`` directory.

The result is that ``stage`` directory can contain the files needed for the
final payload as well as resources for other parts.
If other parts need a part, such as a compiler, to be built and staged before
they can be built, their *build* steps will run after the *stage* step for the
part they depend on.

The prime step
~~~~~~~~~~~~~~

When the *prime* step is run for a part, the contents of the common ``stage``
directory are filtered using the rules in the :ref:`prime` property and
copied into the ``prime`` directory.

In a multi-part project the ``stage`` directory may contain resources that
were required to build certain parts, or the build products may include files
that are not needed at run-time. Using a separate ``prime`` directory in a
separate *prime* step makes it possible to apply a filter to the build
products.
