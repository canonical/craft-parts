.. _craft_parts_overlay_parameters:

Overlay parameters
------------------

A part has five parameters that can be used to adjust how the overlay step
works: ``overlay-packages``, ``overlay-recommended-packages``, ``overlay-script``,
``override-overlay`` and ``overlay``. ``overlay-packages`` and ``overlay`` (the
overlay-files parameter) behave much the same way as the related parameters on the
``STAGE`` step. The ``overlay-recommended-packages`` key works like
``overlay-packages``, but also installs any `recommended packages
<https://www.debian.org/doc/manuals/debian-faq/pkg-basics.en.html#depends`__ that the
target packages might have.

The ``overlay-script`` and ``override-overlay`` keys both take as value a scriplet that
replaces the default overlay step behaviour. They are mutually incompatible.

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
contain ed as an editor, with vi, Vim, Emacs, and nano all having been
removed.
