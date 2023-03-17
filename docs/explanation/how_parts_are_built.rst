How parts are built
===================

As described in :ref:`lifecycle`, parts are built in a sequence of steps:
*pull*, *overlay*, *build*, *stage* and *prime*.

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
processed in the order described in the :ref:`build order <build-order>`. The plugin for the part will use the appropriate build system
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


.. Export, packaging, formatting of final products to make a snap/charm
