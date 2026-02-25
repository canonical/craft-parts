.. _craft_parts_overlay_parameters:

Overlay Parameters
------------------

A part has four parameters that can be used to adjust how the overlay step
works: ``overlay-packages``, ``overlay-script``, ``override-overlay`` and ``overlay``.
``overlay-packages`` and ``overlay`` (the overlay-files parameter) behave much the
same way as the related parameters on the ``STAGE`` step. The ``overlay-script`` and
``override-overlay`` keys both behave similarly to ``override-stage`` and are mutually
incompatible.

The ``override-overlay`` key is unique in that it runs the script in a
chroot environment. This is useful for scripts that need to execute within the target
filesystem as opposed to the host.

An example of a parts section with overlay parameters looks as follows:

.. code-block:: yaml

    parts:
      part_with_overlay:
        plugin: nil
        overlay-packages:
          - ed
        overlay-script: |
          rm -f ${CRAFT_OVERLAY}/usr/bin/vi ${CRAFT_OVERLAY}/usr/bin/vim*
          rm -f ${CRAFT_OVERLAY}/usr/bin/emacs*
          rm -f ${CRAFT_OVERLAY}/bin/nano
        overlay:
          - bin
          - usr/bin

After running this part, the overlay layer (and the final package) will only
contain ed as an editor, with vi/vim, emacs, and nano all having been
removed.
