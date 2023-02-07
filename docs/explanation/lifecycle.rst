*****************
Lifecycle details
*****************

Each part is built in five separate steps:

#. ``PULL`` — The components for the part are retrieved from their stated
   location and placed into a package cache area.
#. ``OVERLAY`` — Any overlay packages are incorporated into the staging area
   and the overlay script is run. Finally, any overlay filters are applied.
#. ``BUILD`` — The part is built according to the particular part plugin and
   build override.
#. ``STAGE`` — The specified outputs from the ``BUILD`` stage are copied into
   a unified staging area for all parts.
#. ``PRIME`` — The specified files are copied from the staging area to the
   priming area for use in the final project. This is distinct from ``STAGE``
   in that the ``STAGE`` step allows files that are used in the ``BUILD`` steps
   of dependent parts to be accessed, while the ``PRIME`` step occurs after all
   parts have been staged.

Step order
----------

While each part's steps are guaranteed to run in the order above, they are
not necessarily run immediately following each other, especially if multiple
parts are included in a project. While specifics are implementation-dependent,
the general rules for combining parts are:

#. ``PULL`` all parts before running further steps
#. ``OVERLAY`` parts in their processing order (defined below).
#. ``BUILD`` any unbuilt parts whose dependencies have been staged. If a part
   has no dependencies, this part is built in the first iteration.
#. ``STAGE`` any newly-built parts.
#. Repeat the ``BUILD`` and ``STAGE`` steps until all parts have been staged.
#. ``PRIME`` all parts.

Part Processing Order
=====================

The processing of various parts is ordered based on dependencies. Circular
dependencies are not permitted between parts. Parts without dependencies are
prioritised first. Next priority contains parts that have dependencies met,
repeated until all parts have an order.

Parts of the same priority should be able to be processed in any order.
However, because ``OVERLAY`` steps may overwrite the same areas of the file
system, parts with the same priority are processed alphabetically to
guarantee deterministic ordering.

Lifecycle processing diagram
----------------------------

.. image:: /images/lifecycle_logic.png

Further Information
-------------------

Further information can be found in the `Snapcraft parts lifecycle documentation
<snapcraft-parts-lifecycle_>`_.

.. _snapcraft-parts-lifecycle: https://snapcraft.io/docs/parts-lifecycle


