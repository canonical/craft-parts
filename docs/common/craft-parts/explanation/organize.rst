.. |app| replace:: Craft Parts

.. _organize_explanation:

Organize
========

The ``organize`` part property rearranges a part's installed files before
they are staged.

During the *build* step, the plugin installs the part's output into the
part-specific ``install`` directory. At the end of that step, |app| applies
the part's ``organize`` mappings to that install layout. The later *stage*
step then migrates the resulting install contents into the common stage area.

This makes ``organize`` a way to shape a part's own install tree. It isn't a
direct copy from the build area into the stage area.

Mappings
--------

The ``organize`` property is a mapping of source paths to destination paths:

.. code-block:: yaml

    organize:
      source-path-or-pattern: destination-path

For ordinary mappings, the source path selects a file or directory from the
part's install layout. The destination path says where the selected content
should be placed. Source paths can also contain source patterns with ``*``.

For task-oriented examples that use the Dump plugin to include local files and
remote resources, see :ref:`how_to_include_files_and_resources`.

Build directory sources
-----------------------

A source path prefixed with ``(build)`` selects content from the part's build
directory instead of its install directory. Unlike ordinary sources, content
organized from the build directory is copied: the original content remains in
the build directory after the mapping is applied.

For example:

.. code-block:: yaml

    organize:
      (build)/generated.txt: share/generated.txt

The destination receives ``generated.txt``, while the original file remains in
the build directory. Files, directories, and source patterns can all use the
``(build)`` prefix.

The build directory can only be used as a source. ``(build)`` isn't a valid
destination.

Partitions and overlays
-----------------------

When partitions are enabled, destination paths can select a partition. Ordinary
sources come from the default partition's install layout, while ``(build)``
continues to select the part's build directory. ``(default)`` can be used to
refer explicitly to the default partition.

An ``(overlay)`` destination organizes content into the overlay layout. The
same distinction between explicit directories and directories selected by
``*`` still applies: explicit directories merge their contents into the
destination, while directories selected by a pattern keep their directory
names below the destination.

These qualified destinations change where content is organized, but not the
basic mapping model described below.

Files
-----

An explicit file source can be moved or renamed.

Given this install layout:

.. code-block:: text

    .
    └── foo

This mapping:

.. code-block:: yaml

    organize:
      foo: bar

Produces this install layout:

.. code-block:: text

    .
    └── bar

When a source pattern containing ``*`` selects multiple files, use a directory
destination if their file names should be preserved. A destination that ends
with ``/`` is treated as a directory to create if it doesn't already exist.

Given this install layout:

.. code-block:: text

    .
    ├── bar.conf
    └── foo.conf

This mapping:

.. code-block:: yaml

    organize:
      "*.conf": dir/

Produces this install layout:

.. code-block:: text

    .
    └── dir
        ├── bar.conf
        └── foo.conf

If the destination is written as ``dir`` instead of ``dir/`` and the ``*``
pattern selects more than one file, |app| reports an error because multiple
files would be organized to the same destination path.

Directories
-----------

An explicit directory source is merged directly into its destination path. The
source directory name itself isn't preserved under the destination.

Given this install layout:

.. code-block:: text

    .
    └── foodir
        └── foo

This mapping:

.. code-block:: yaml

    organize:
      foodir: bardir

Produces this install layout:

.. code-block:: text

    .
    └── bardir
        └── foo

Directories selected through a ``*`` pattern keep their source directory names
under the destination.

Given this install layout:

.. code-block:: text

    .
    ├── dir1
    │   └── foo
    └── dir2
        └── bar

This mapping:

.. code-block:: yaml

    organize:
      "dir*": dir/

Produces this install layout:

.. code-block:: text

    .
    └── dir
        ├── dir1
        │   └── foo
        └── dir2
            └── bar

Ordering
--------

Source entries without ``*`` are processed before source entries containing
``*``. This allows a specific path to be organized separately before a broader
``*`` pattern handles the remaining content.

Given this install layout:

.. code-block:: text

    .
    ├── dir1
    │   ├── bar
    │   └── foo
    └── dir2
        └── bar

This mapping:

.. code-block:: yaml

    organize:
      "dir*": dir/
      dir1/bar: .

Produces this install layout:

.. code-block:: text

    .
    ├── bar
    └── dir
        ├── dir1
        │   └── foo
        └── dir2
            └── bar

Although the ``*`` pattern appears first in the YAML, ``dir1/bar`` is organized
first because it's a source entry without ``*``. The later ``dir*`` mapping then
organizes the remaining matching directories.

Conflicts
---------

Organizing fails if a mapping would place content where another file already
exists, or if more than one selected file would be organized to the same
non-directory destination. This prevents an ``organize`` rule from silently
replacing files or making the final install layout depend on ``*`` pattern match
order.

Directory contents can be merged into the same destination when there are no
file conflicts. For example, two explicit source directories can both organize
their contents into the same destination directory, and files can also be
organized into that destination by explicit file mappings.

Source path safety
------------------

Ordinary source paths are resolved against the part's install directory.
Absolute source paths and paths that traverse outside that directory are
rejected.

For example, this source is rejected:

.. code-block:: yaml

    organize:
      ../foo: foo

A path that contains ``..`` segments is allowed only when the normalized source
path still stays within the install directory.

Summary
-------

When defined:

* ``organize`` maps source paths or patterns to destination paths.
* Explicit file sources can move or rename files.
* Source patterns containing ``*`` need a directory destination when multiple
  selected file names should be preserved.
* Explicit source directories are merged directly into their destinations.
* Source directories selected by ``*`` patterns keep their directory names
  under the destination.
* ``(build)`` sources copy content from the build directory instead of moving
  it, and the build directory can't be used as a destination.
* With partitions, destinations can select another partition or the overlay
  layout.

When used:

* ``organize`` is applied at the end of the *build* step, normally rearranging
  the part's install layout.
* Source entries without ``*`` are processed before source entries containing
  ``*``.
* The later *stage* step migrates the resulting install contents into the
  common stage area.
