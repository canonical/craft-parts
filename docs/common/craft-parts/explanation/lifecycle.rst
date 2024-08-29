.. _lifecycle:

*****************
Lifecycle details
*****************

Each part is built in :ref:`five separate steps <craft_parts_steps>`, each with
its own input and output locations:

#. ``PULL`` — The source and external dependencies (such as package
   dependencies) for the part are retrieved from their stated location and
   placed into a package cache area.
#. ``OVERLAY`` — Any overlay packages are installed in an overlay of the
   filesystem base, and the overlay script is run. Finally, any overlay filters
   are applied.
#. ``BUILD`` — The part is built according to the particular part plugin and
   build override.
#. ``STAGE`` — The specified outputs from the ``BUILD`` step are copied into
   a unified staging area for all parts.
#. ``PRIME`` — The specified files are copied from the staging area to the
   priming area for use in the final payload. This is distinct from ``STAGE``
   in that the ``STAGE`` step allows files that are used in the ``BUILD`` steps
   of dependent parts to be accessed, while the ``PRIME`` step occurs after all
   parts have been staged.

Step order
----------

While each part's steps are guaranteed to run in the order above, they are
not necessarily run immediately following each other, especially if multiple
parts are included in a project. While specifics are implementation-dependent,
the general rules for combining parts are:

#. ``PULL`` all parts before running further steps.
#. ``OVERLAY`` parts in their processing order (defined below).
#. ``BUILD`` any unbuilt parts whose dependencies have been staged. If a part
   has no dependencies, this part is built in the first iteration.
#. ``STAGE`` any newly-built parts.
#. Repeat the ``BUILD`` and ``STAGE`` steps until all parts have been staged.
#. ``PRIME`` all parts.

.. _part_processing_order:

Part processing order
=====================

The processing of various parts is ordered based on dependencies. Circular
dependencies are not permitted between parts. The ordering rules are as follows:

#. Parts are ordered alphabetically by name
#. Any part that requires another part (using the ``after`` key) will move that
   dependency ahead of the declaring part.

NOTE: This means that renaming parts and adding, modifying or removing ``after``
keys for parts can change the order.

In the example below, the parts will run each stage, ordering the parts
alphabetically at each stage (even though C is listed before B):

.. code-block:: yaml

  parts:
    A:
      plugin: nil
    C:
      plugin: nil
    B:
      plugin: nil

.. details:: craft_parts output

  .. code-block:: text

    Execute: Pull A
    Execute: Pull B
    Execute: Pull C
    Execute: Overlay A
    Execute: Overlay B
    Execute: Overlay C
    Execute: Build A
    Execute: Build B
    Execute: Build C
    Execute: Stage A
    Execute: Stage B
    Execute: Stage C
    Execute: Prime A
    Execute: Prime B
    Execute: Prime C

However, if parts specify dependencies, both the ``build`` and ``stage`` steps
of a dependency will be moved ahead of the dependent part in addition to the
parts being reordered within a step:

.. code-block:: yaml

  parts:
    A:
      plugin: nil
      after: [C]
    C:
      plugin: nil
    B:
      plugin: nil

.. details:: craft_parts output

  .. code-block:: text
    :emphasize-lines: 7-8

    Execute: Pull C
    Execute: Pull A
    Execute: Pull B
    Execute: Overlay C
    Execute: Overlay A
    Execute: Overlay B
    Execute: Build C
    Execute: Stage C (required to build 'A')
    Execute: Build A
    Execute: Build B
    Execute: Stage A
    Execute: Stage B
    Execute: Prime C
    Execute: Prime A
    Execute: Prime B


Lifecycle processing diagram
----------------------------

.. image:: /common/craft-parts/images/lifecycle_logic.png

Further Information
-------------------

Further information can be found in the `Snapcraft parts lifecycle documentation
<snapcraft-parts-lifecycle_>`_.

.. _snapcraft-parts-lifecycle: https://snapcraft.io/docs/parts-lifecycle
