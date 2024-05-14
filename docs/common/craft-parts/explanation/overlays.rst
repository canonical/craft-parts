****************
``OVERLAY`` Step
****************

Some Craft applications, such as Rockcraft_, include entire base filesystems in
addition to the usual part-generated payload. The ``OVERLAY`` step provides the
means to modify the base filesystem.

.. include:: /common/craft-parts/explanation/overlay_parameters.rst

.. _overlay_visibility:

Overlay Visibility
------------------

By default, a part does not get access to the filesystem overlay. However,
if a part provides any overlay parameters or depends on another part that
provides overlay parameters, the location of the overlay is made available
in the ``${CRAFT_OVERLAY}`` environment variable. For example:

.. code-block:: yaml

    parts:
      no-overlay-access:
        plugin: nil
        override-build: |
          echo "${CRAFT_OVERLAY}" > "${CRAFT_PART_INSTALL}/empty"
      direct-overlay-access:
        plugin: nil
        overlay-script: |
          echo "${CRAFT_OVERLAY}" > "${CRAFT_PART_INSTALL}/direct"
      indirect-overlay-access:
        plugin: nil
        after: [direct-overlay-access]
        override-build: |
          echo "${CRAFT_OVERLAY}" > "${CRAFT_PART_INSTALL}/indirect"

Because ``no-overlay-access`` has no access to the overlay directory, the
``no-overlay-access`` part will fail to build, as the ``CRAFT_OVERLAY``
environment variable is unset. Removing that attempted access will make this
file build.

.. _overlay_layers:

Layers
------

Each part has an overlay layer, which acts on a shared storage area in the
processing order of parts. If the part doesn't specify any overlay parameters,
this overlay is empty. The overlay's integrity is checked with a checksum
defined by the following diagram:

.. image:: /common/craft-parts/images/overlay_checksum.svg
   :alt: Diagram for generating the overlay checksum.

Each layer's checksum is derived from the combination of the layer's properties
and the checksum of the layer below it. As a result, a change to any layer will
require the recalculation of the overlay for all layers above it, and an
update to the base layer results in the recalculation of all overlays. The
order of layers is determined by the :ref:`part_processing_order`.

Filesystem Mutations
====================

Mutations to the filesystem may include changes caused by the installation of OS
packages (including package database updates), the execution of user scripts in
the overlay filesystem context, or file filters.

The outcome of the overlay step for each part includes solely the modifications
made by that part to underlying layers. As a consequence, if no modifications
are made, the result of the overlay step is empty and the result is the same as
the four-step lifecycle without overlays. Subtractive changes such as file
removals are allowed and handled through special whiteout files conforming to
the `OCI image layer specification`_.

Overlay Processing
------------------

Step Execution
==============

Each layer in the overlay step is generated under the following rules:

#. The overlay step for previous parts must have been executed before processing
   the overlay step for a part.
#. If the part declares no overlay parameters, its layer in the overlay step is
   empty.
#. Otherwise, enable the mechanism that handles filesystem layering, and
   assemble the layer stack up to the part being processed.
#. Install overlay packages on top of the layer stack, and execute the user
   script if defined.
#. Disable the mechanism that handles filesystem layering.
#. Generate the overlay step state.

Staging Overlay Files
=====================

When executing the stage step for a part that declares overlay content, the
consolidated content generated in the overlay step is added to the common stage
area along with artifacts resulting from the part's build step. Files from
overlay and part install may overlap as long as they don't conflict.
Conflicting files can be resolved using stage or overlay file filters.

Staging any part that declares overlay content cause the consolidated overlay
content be staged. The overlay files remain in the stage area until all parts
that specify overlay parameters are cleaned. Because multiple parts can modify
the same file, only the final version of the file is staged. This final version,
not the intermediate version, of the file is what is made available to relevant
parts during the build step.

Normalization
=============

Overlay files may be adjusted to work better on a non-root filesystem
environment (such as converting absolute paths to relative path in symbolic link
targets), but must not be changed in a way that precludes it from running
correctly on a root filesystem environment (such as setting an absolute path to
a non-root environment in a configuration file).

Overlay Package Installation
============================

Overlay packages are downloaded in the pull stage into a package cache area and
made available for installation during the overlay stage, from sources
configured in the overlay base image. The package cache layer may be placed
between the base layer and the layer for the 1st part, using the logic defined
in :ref:`overlay_layers`.

The package cache layer is not visible as part of the final overlay filesystem
as seen by other parts during the build step, nor are its files migrated from
the build to the stage step. This means that the package cache layer may be
removed from the layer stack after the overlay packages are installed without
affecting subsequent steps.

Note that the package installation process runs in the context of the overlay
filesystem (i.e. considering the base filesystem as the root filesystem) so
that package maintainer scripts are always executed correctly.

Overlay State
-------------

The overlay state for a particular part includes the overlay script and
any overlay filesets. The list of overlay packages is included in the state of
the pull step, so if the list of overlay packages is changed, the pull step
for the part will re-run. If the :ref:`overlay is visible <overlay_visibility>`
to a part, the overlay integrity code is added to future steps of the part,
ensuring proper invalidation of those steps if overlay data changes.

Step Invalidation
=================



.. _OCI image layer specification: https://github.com/opencontainers/image-spec/blob/master/layer.md
.. _Rockcraft: https://canonical-rockcraft.readthedocs-hosted.com/
