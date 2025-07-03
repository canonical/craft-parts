.. _migration:

**************
File migration
**************

During the lifecycle execution, files resulting from building a part
are transferred from that part's install directory to a shared stage
directory, and from there to the prime directory. The process of moving
content between steps during the lifecycle is referred to as "migration".
Not all files from a step are necessarily migrated — users can apply
filters to exclude certain files, or specify which ones should proceed
to the next step.

The lifecycle also supports granular operations such as executing individual
steps, removing files tied to a specific part, or running a step for a
specific part. To allow that, the system maintains metadata to track file
ownership in shared areas, mapping each file to its originating part.


Migration state
---------------

The list of files belonging to a part is necessary when files are migrated
from a shared directory, or when files from a specific part must be removed
from an area containing files from different parts. This mapping is obtained
when migrating files from part-specific directories, and is called the
"migration state".


Simple file migration
---------------------

During the execution of a simple four-step lifecycle, files from the part's
install directory are migrated to the stage area and from there to prime.
In the following diagram, files are represented as circles with letters. The
green circles correspond to files from part 1, while blue circles represent
files originating from part 2.

.. image:: /common/craft-parts/images/simple_migration.svg

Files ``A`` and ``B`` originate from part 1, while files ``C`` and ``D``
originate from part 2. They are staged into a common area, and then migrated
to prime. Note that file ``D`` is filtered out when priming, and is not part
of the final primed contents. The migration state for parts 1 and 2 is obtained
from the contents of each of the parts' install directories while they're still
separate (marked with red ellipses in the diagram).

When files from a specific part need to be migrated from stage to prime or
removed from stage or prime, the migration state contains the list of files
to migrate or remove.


File migration using partitions
-------------------------------

When the partitions feature is enabled, files can be organized from a part's
install directory to a different partition. In this case, files are migrated
to the partition's specific stage and prime directories.

.. image:: /common/craft-parts/images/partition_migration.svg

When partitions are used, an operation to remove or migrate files from a
specific part happens across all partitions. In this example, if files from
part 1 are to be removed from prime, files ``A`` and ``B`` will be deleted.
For that, separate migration states are obtained from all parts in all
partitions.


File migration using overlays
-----------------------------

When the overlay feature is enabled, files can originate from both the part's
install directory and the overlay area. In the diagram, files from the overlay
are represented as squares, and files from the build install are represented
as circles.

.. image:: /common/craft-parts/images/overlay_migration.svg

If overlays are used, it's important to note that the files originating from
the overlay form a set that are moved or deleted as a group. In the example
above, if files from part 1 are to be deleted from prime, only files ``A``
and ``B`` are removed. Overlay files are only removed when files from all parts
containing overlay files are removed. Conversely, when files are migrated, the
entire set of overlay files is migrated along with the first part that contains
overlay files. A part with no overlay files will have all its files processed
immediately.


File migration using partitions and overlays
--------------------------------------------

When both partitions and overlays are enabled, files from overlay can be moved
to other partitions using mount maps. This operation also generates a migration
state to keep track of the files originating part.

.. image:: /common/craft-parts/images/partition_overlay_migration.svg

The same constraints for overlay file removal and migration apply, extended to
all partitions. In the example above, if files from part 1 are to be removed from
stage, files ``A`` and ``B`` are removed, but file ``E`` is only removed when
part 2 files are also removed (because overlay files can only be removed at the 
same time).

Migration states in the case with partitions and overlays are obtained from
the part's install directories across partitions, overlay migration, and overlay
mounts.


Migration states and lifecycle states
-------------------------------------

Migration states don't affect lifecycle planning and exist entirely on the
executor phase of the lifecycle run. They should never be accessed during the
planning phase.
