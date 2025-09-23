.. _explanation-file-migration:

File migration
==============

During the part lifecycle, files resulting from building a part
are transferred from that part's install directory to a shared stage
directory, and from there to the prime directory. The process of moving
files between steps during the lifecycle is referred to as *migration*.
Not all files from a step are necessarily migrated — crafters can apply
filters to exclude certain files, or specify which ones should proceed
to the next step.

The lifecycle also supports granular operations such as executing individual
steps, removing files tied to a specific part, or running a step for a
specific part. To allow that, the system maintains metadata to track file
ownership in shared areas, mapping each file to its originating part.


Migration tracking
------------------

Parts typically contain files pulled from sources or generated during the
build process. Up to the build step files belonging to each part are kept
in separate directories, but once they are staged they share a common
area in the filesystem. To further migrate or remove files from a shared
directory containing files from different parts, it is necessary to know
which files belong to each part. This mapping is obtained when files are
initially migrated files from part-specific directories, and is called the
*migration tracking state*.


Simple file migration
---------------------

During the execution of the lifecycle, files from the part's install directory are
migrated to the stage area and from there to prime.

When files from a specific part need to be migrated from stage to prime or removed from
stage or prime, the migration tracking state contains the list of files to migrate or
remove.

.. figure:: /common/craft-parts/images/simple_migration.svg
    :align: left
    :alt: A diagram showing the migration tracking state of files from two parts,
          described in more detail in the figure caption.

    The migration of files between lifecycle steps. Each labelled circle is a file.
    Each black rectangle is a directory.

    Files A and B originate from Part 1, while files C and D originate from part 2.
    They are staged into a common area, and then migrated to the prime directory.
    Observe that file D is filtered out when priming, and isn't in the final primed
    contents.

    The migration tracking state for parts 1 and 2 is obtained from the contents of
    each part's install directories while they're still separate, as indicated by the
    red ellipses.


File migration with partitions
------------------------------

When the partitions feature is enabled, files can be organized from a part's
install directory to a different partition. In this case, files are migrated
When the partitions feature is in use, files can be organized from a part's
to the partition's own stage and prime directories.

.. image:: /common/craft-parts/images/partition_migration.svg
    :alt: A diagram showing the migration tracking state of files when partitions are
          in use, described in more detail next.

When partitions are used, an operation to remove or migrate files from a
specific part happens across all partitions. In this example, if files from
part 1 are to be removed from prime, files A and B will be deleted.
For that, separate migration tracking states are obtained from all parts in
all partitions.


File migration using overlays
-----------------------------

When the overlay feature is enabled, files can originate from both the part's
install directory and the overlay area. In the diagram, files from the overlay
are represented as squares, and files from the build install are represented
as circles.

When the overlays are in use, files can originate from both the part's install
directory and the overlay area.

.. figure:: /common/craft-parts/images/overlay_migration.svg
    :align: left
    :alt: A diagram showing the migration tracking state of files when overlays
          are in use, described in more detail next.

    File migration involving overlays. Files from the overlay are represented as
    squares, and files from the build install are represented as circles.

If overlays are used, it's important to note that the files originating from the
overlay form a set that are moved or deleted as one. In the previous diagram, if
files from part 1 are to be deleted from prime, only files A and B are removed.
Overlay files are only removed when files from all parts containing overlay
files are removed. Conversely, when files are migrated, the entire set of
overlay files is migrated along with the first part that contains overlay files.

If a part depends on another part, cleaning the latter will also cause the
former to be cleaned.


File migration with partitions and overlays
-------------------------------------------

When both partition and overlays are in use, files from overlay can
be moved to other partitions using mount maps. This operation also generates a
migration state to keep track of the files originating part.

.. image:: /common/craft-parts/images/partition_overlay_migration.svg
    :alt: A diagram showing the migration tracking state of files when both overlays
          and partitions are in use, described in more detail next.

The same constraints for overlay file removal and migration apply, extended to
all partitions. In the example above, if files from part 1 are to be removed
from stage, files A and B are removed, but file E is only removed when part 2
files are also removed, because overlay files can only be removed at the same
time.

With partitions and overlays, migration tracking information is
obtained from the part's install directories across partitions, overlay migration,
and overlay mounts.
