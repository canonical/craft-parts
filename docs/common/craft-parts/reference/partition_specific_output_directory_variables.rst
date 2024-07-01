Partition-specific output directory environment variables
---------------------------------------------------------

If partitions are enabled, partition-specific environment variables will be created for use during step processing and execution of user-defined scriptlets.

These variable names will contain the (optional) namespace, partition name, and lifecycle step, formatted as ``CRAFT_[<namespace>_]<partition>_{STAGE|PRIME}``.  The values of these variables will be the directory that corresponds to that partition and step.  For instance, if the defined partitions are ``default``, ``kernel``, and ``component/bar-baz``, the following environment variables will be created::

  $CRAFT_STAGE                   -> stage
  $CRAFT_DEFAULT_STAGE           -> stage
  $CRAFT_KERNEL_STAGE            -> partitions/kernel/stage
  $CRAFT_COMPONENT_BAR_BAZ_STAGE -> partitions/component/bar-baz/stage

  $CRAFT_PRIME                   -> prime
  $CRAFT_DEFAULT_PRIME           -> prime
  $CRAFT_KERNEL_PRIME            -> partitions/kernel/prime
  $CRAFT_COMPONENT_BAR_BAZ_PRIME -> partitions/component/bar-baz/prime

(Note that the hyphen in the partition ``component/bar-baz`` is converted to an underscore in the corresponding variable names.)
