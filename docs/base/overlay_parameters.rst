.. _craft_parts_overlay_parameters:

Overlay Parameters
------------------

A part has three parameters that can be used to adjust how the overlay step
works: ``overlay-packages``, ``overlay-script`` and ``overlay-filter``.
``overlay-packages`` and ``overlay`` (the filter parameter) behave much the
same way as the related parameters on the ``STAGE`` step. ``overlay-script``
likewise behaves similarly to ``override-stage``, including having access to
the ``craftctl`` command.

An example parts section with overlay parameters looks as follows:

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
